#include <stdio.h>
#include <assert.h>
#include <openssl/evp.h>
#include "hasher.h"

typedef enum ErrorCode {
    OPENSSL_ERROR = 1,
    OUT_OF_MEMORY,
    UNKNOWN_ALGORITHM
} ErrorCode;

const char *hasher_error_msg(int code) {
    if (code == 0) return "NO ERROR";
    switch ((ErrorCode) code) {
        case OPENSSL_ERROR:
            return "Unknown OpenSSL Error";
        case OUT_OF_MEMORY:
            return "Out of memory";
        case UNKNOWN_ALGORITHM:
            return "Unknown algorithm";
        default:
            return "Unknown error";
    }
}

struct ShaHasher {
    HasherState state;
    // void internal[] -- Begin internal
    EVP_MD_CTX *evp;
    const EVP_MD *hash_type;
};

int hasher_error_code = 0;


int reset0(ShaHasher *hasher) {
    if (!EVP_DigestInit_ex(hasher->evp, hasher->hash_type, NULL)) {
        hasher_error_code = OPENSSL_ERROR;
        return 0;
    }
    hasher->state = RESET;
    return 1;
}

ShaHasher *create_hasher(HashAlgorithm alg) {
    assert(sizeof(ShaHasher) >= sizeof(struct PublicShaHasher));
    const EVP_MD *hash_type;
    switch (alg) {
        case SHA_256:
            hash_type = EVP_sha256();
            break;
        default:
            hasher_error_code = UNKNOWN_ALGORITHM;
            return NULL;
    }
    assert(hash_type != NULL);
    EVP_MD_CTX *evp = EVP_MD_CTX_create();
    if (evp == NULL) {
        hasher_error_code = OPENSSL_ERROR;
        return NULL;
    }
    ShaHasher *result = malloc(sizeof(ShaHasher));
    if (result == NULL) {
        hasher_error_code = OUT_OF_MEMORY;
        return NULL;
    }
    *result = (ShaHasher) {
        .state = UNINITIALIZED,
        .evp = evp,
        .hash_type = hash_type,
    };
    if (!reset0(result)) return NULL;
    return result;
}

int hash_size(ShaHasher *hasher) {
    int result = EVP_MD_size(hasher->hash_type);
    assert(result > 0);
    return result;
}

int reset_hasher(ShaHasher *hasher) {
    check_state(hasher, DONE);
    return reset0(hasher);
}

int update_hasher(ShaHasher *hasher, const char *data, size_t count) {
    static HasherState EXPECTED_STATES[2] = {WORKING, RESET};
    HasherState state = hasher->state;
    switch (state) {
        case RESET:
            hasher->state = WORKING;
        case WORKING:
            break;
        default:
            unexpected_state(hasher, EXPECTED_STATES, 2);
            abort();
    }
    if (!EVP_DigestUpdate(hasher->evp, data, count)) {
        hasher_error_code = OPENSSL_ERROR;
        return 0;
    }
    return 1;
}

int finish_hasher(ShaHasher *hasher, char *out, int *size) {
    check_state(hasher, WORKING);
    unsigned int expected_size = EVP_MD_size(hasher->hash_type);
    assert(expected_size <= EVP_MAX_MD_SIZE);
    unsigned int actual_size = -1;
    if (!EVP_DigestFinal_ex(hasher->evp, (unsigned char*) out, &actual_size)) {
        hasher_error_code = OPENSSL_ERROR;
        return 0;
    }
    hasher->state = DONE;
    assert(actual_size >= 0 && actual_size == expected_size);
    if (size != NULL) {
        *size = expected_size;
    }
    return 1;
}

int destroy_hasher(ShaHasher *hasher) {
    EVP_MD_CTX_destroy(hasher->evp);
    hasher->evp = NULL;
    hasher->hash_type = NULL;
    hasher->state = DESTROYED;
    free(hasher);
    return 1;
}
