#include <stdlib.h>

typedef enum HasherState {
    UNINITIALIZED,
    RESET,
    WORKING,
    DONE,
    DESTROYED
} HasherState;

typedef enum HashAlgorithm {
    SHA_256
} HashAlgorithm;

typedef struct ShaHasher ShaHasher;
struct PublicShaHasher {
    HasherState state;
    char internal[];
};

#define HASHER_STATE(hasher) ({\
    ShaHasher *_hasher = hasher; \
    ((struct PublicShaHasher*) _hasher)->state;\
})

const char *state_name(HasherState state);

void unexpected_state(ShaHasher *hasher, const HasherState *expected, int num_expected) __attribute__((noreturn, cold));

inline void check_state(ShaHasher *hasher, HasherState expected) {
    HasherState actual = HASHER_STATE(hasher);
    if (actual != expected) {
        unexpected_state(hasher, &expected, 1);
    }
}

extern int hasher_error_code;

/**
 * Return the error message for the specified non-zero error code
 */
const char *hasher_error_msg(int);

ShaHasher *create_hasher(HashAlgorithm alg);

int hash_size(ShaHasher *hasher);

/**
 * Reset the hasher, preparing it for more data.
 */
int reset_hasher(ShaHasher *hasher);

/**
 * Update the hasher with the specified data.
 */
int update_hasher(ShaHasher *hasher, const char *data, size_t count);

/**
 * Finish hashing the data, putting the result into the specified buffer,
 * and setting the size pointer to the size of the hash.
 */
int finish_hasher(ShaHasher *hasher, char *out, int *size);

int destroy_hasher(ShaHasher *hasher);
