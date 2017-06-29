cdef extern from "hashing/hasher.h":
    ctypedef enum HashAlgorithm:
        SHA_256
    ctypedef struct ShaHasher:
        pass
    
    int hasher_error_code;

    const char *hasher_error_msg(int) nogil;

    ShaHasher* create_hasher(HashAlgorithm alg) nogil;

    int hash_size(ShaHasher *hasher) nogil;

    int reset_hasher(ShaHasher *hasher) nogil;

    int update_hasher(ShaHasher *hasher, const char *data, size_t count) nogil;

    int finish_hasher(ShaHasher *hasher, char *out, int *size) nogil;

    int destroy_hasher(ShaHasher *hasher) nogil;

