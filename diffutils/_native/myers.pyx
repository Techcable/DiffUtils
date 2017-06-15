from ..engine import DiffEngine
from ..core import Delta, Patch, Chunk
from libc.stdlib cimport malloc, free, calloc, realloc, abort
from libc.string cimport memcpy, memcmp
from cpython cimport array
import hashlib

# Hopefully 6KB is enough to start off with
DEF CHUNK_SIZE = 256

cpdef native_diff(original, revised):
    cdef DiffNode *path
    if type(original) is not list:
        raise TypeError(f"Original must be a list, not a {type(original)}")
    if type(revised) is not list:
        raise TypeError(f"Revised must be a list, not a {type(revised)}")
    cdef NodeAllocator allocator = NodeAllocator() # NOTE: Python frees this automatically
    cdef int i
    cdef size_t original_size = len(original)
    cdef size_t revised_size = len(revised)
    # Take the sha256sum of the lines to speed up diffing, since string comparison is one of the main costs
    cdef char[32] *original_hashes = <char[32]*> malloc(original_size * sizeof(char[32]))
    if not original_hashes:
        raise MemoryError()
    cdef char[32] *revised_hashes =  <char[32]*> malloc(revised_size * sizeof(char[32]))
    if not revised_hashes:
        raise MemoryError()
    try:
        for (index, element) in enumerate(original):
            assert index < original_size
            if type(element) is not str:
                raise TypeError(f"Element at original index {index} must be a str, not a {type(element)}")
            element_bytes = element.encode('utf-8')
            sha256sum(element_bytes, original_hashes[index])
        for (index, element) in enumerate(revised):
            assert index < revised_size
            if type(element) is not str:
                raise TypeError(f"Element at revised index {index} must be a str, not a {type(element)}")
            element_bytes = element.encode('utf-8')
            sha256sum(element_bytes, revised_hashes[index])
        path = build_path(allocator, original_hashes, original_size, revised_hashes, revised_size)
        if not path:
            raise MemoryError()
        return build_revision(path, original, revised)
    finally:
        free(original_hashes)
        free(revised_hashes)

cdef DiffNode* build_path(NodeAllocator allocator, char[32] *original_hashes, size_t original_size, char[32] *revised_hashes, size_t revised_size):
    cdef size_t max_size = original_size + revised_size + 1
    cdef size_t size = 1 + 2 * max_size
    cdef size_t middle = size // 2
    # NOTE: Must use calloc to initialize to null
    # Also, we need to make sure this is an array of POINTERS, since that's what the allocator hands out
    cdef DiffNode **diagonal = <DiffNode**> calloc(size, sizeof(DiffNode*))
    if not diagonal:
        return NULL
    cdef int k, d, kmiddle, kplus, kminus, i, j
    cdef DiffNode *prev
    cdef DiffNode *node
    try:
        with nogil:
            node = allocator.create_snake(0, -1, NULL)
            if node == NULL:
                return NULL
            diagonal[middle + 1] = node
        
            for d in range(max_size):
                for k in range(-d, d + 1, 2):
                    kmiddle = middle + k
                    kplus = kmiddle + 1
                    kminus = kmiddle - 1
                    prev = NULL

                    # For some reason this works, but not the other ways
                    if (k == -d) or (k != d and diagonal[kminus].i < diagonal[kplus].i):
                        i = diagonal[kplus].i
                        prev = diagonal[kplus]
                    else:
                        i = diagonal[kminus].i + 1
                        prev = diagonal[kminus]

                    diagonal[kminus] = NULL

                    j = i - k

                    node = allocator.create_node(i, j, prev)
                    if node == NULL:
                        return NULL

                    # orig and rev are zero-based
                    # but the algorithm is one-based
                    # that's why there's no +1 when indexing the sequences
                    while i < original_size and j < revised_size and (memcmp(original_hashes[i], revised_hashes[j], 32) == 0):
                        i += 1
                        j += 1
                    if i > node.i:
                        node = allocator.create_snake(i, j, node)
                        if node == NULL:
                            return NULL

                    diagonal[kmiddle] = node

                    if i >= original_size and j >= revised_size:
                        return diagonal[kmiddle]

                    k += 2

                diagonal[middle + d - 1] = NULL

        # According to Myers, this cannot happen
        raise RuntimeError("couldn't find a diff path")
    finally:
        free(diagonal)


cdef build_revision(DiffNode *path, list original, list revised):
    patch = Patch()
    if path.snake:
        path = path.prev
    cdef int i, j, ianchor, janchor
    while path != NULL and path.prev != NULL and path.prev.j >= 0:
        if path.snake:
            raise ValueError("Found snake when looking for diff")
        i = path.i
        j = path.j

        path = path.prev
        ianchor = path.i
        janchor = path.j

        original_chunk = Chunk(ianchor, original[ianchor:i])
        revised_chunk = Chunk(janchor, revised[janchor:j])
        delta = Delta.create(original_chunk, revised_chunk)

        patch.add_delta(delta)
        if path.snake:
            path = path.prev
    return patch

cdef struct MemoryChunk:
    size_t current_size
    MemoryChunk *prev
    DiffNode *data

cdef class NodeAllocator:
    cdef MemoryChunk *current_chunk
    def __cinit__(self):
        self.current_chunk = NULL
        self.allocate_chunk()
        assert self.current_chunk != NULL

    cdef inline DiffNode *create_node(self, int i, int j, DiffNode *prev) nogil:
        cdef DiffNode *node = self.blank_node()
        if node == NULL:
            return NULL
        node.i = i
        node.j = j
        node.snake = False
        prev = prev.lastSnake
        node.prev = prev
        if i < 0 or j < 0:
            node.lastSnake = NULL
        else:
            node.lastSnake = prev.lastSnake
        return node
    
    cdef inline DiffNode *create_snake(self, int i, int j, DiffNode *prev) nogil:
        cdef DiffNode *snake = self.blank_node()
        if snake == NULL:
            return NULL
        snake.i = i
        snake.j = j
        snake.prev = prev
        snake.lastSnake = snake
        snake.snake = True
        return snake

    cdef inline DiffNode *blank_node(self) nogil:
        """Allocate a new, uninitialized DiffNode"""
        cdef MemoryChunk *current_chunk = self.current_chunk
        cdef DiffNode *result
        cdef size_t oldSize = current_chunk.current_size
        cdef size_t newSize = oldSize + 1
        if newSize <= CHUNK_SIZE:
            result = &current_chunk.data[oldSize]
            current_chunk.current_size = newSize
            return result
        else:
            return self.fallback_blank_node()

    cdef DiffNode *fallback_blank_node(self) nogil:
        if self.current_chunk == NULL:
            abort()
        cdef MemoryChunk *new_chunk = self.allocate_chunk()
        if new_chunk.current_size != 0:
            abort()
        new_chunk.current_size = 1
        return &new_chunk.data[0]

    cdef MemoryChunk *allocate_chunk(self) nogil:
        cdef MemoryChunk *result = <MemoryChunk*> malloc(sizeof(MemoryChunk))
        if not result:
            return NULL
        cdef DiffNode *data = <DiffNode*> malloc(sizeof(DiffNode) * CHUNK_SIZE)
        if not data:
            return NULL
        result.current_size = 0
        result.prev = self.current_chunk
        result.data = data
        self.current_chunk = result
        return result

    def __dealloc__(self):
        cdef MemoryChunk *chunk = self.current_chunk
        cdef MemoryChunk *prev
        self.current_chunk = NULL
        assert chunk != NULL
        while chunk != NULL:
            free(chunk.data)
            prev = chunk.prev
            chunk.data = NULL
            free(chunk)
            chunk = prev


cdef struct DiffNode:
    int i
    int j
    DiffNode *lastSnake
    DiffNode *prev
    bint snake

cdef void sha256sum(const char *data, char* out):
    m = hashlib.sha256()
    m.update(data)
    resultobj = m.digest()
    cdef char *result = resultobj
    memcpy(out, result, 32)
