#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "hasher.h"

const char *state_name(HasherState state) {
    switch (state) {
        case UNINITIALIZED:
            return "uninitialized";
        case RESET:
            return "reset";
        case WORKING:
            return "working";
        case DONE:
            return "done";
        case DESTROYED:
            return "destroyed";
        default:
            return "unknown";
    }
}

void unexpected_state(ShaHasher *hasher, const HasherState *expected_states, int num_expected) {
    HasherState actual = HASHER_STATE(hasher);
    const char *actual_name = state_name(actual);
    const char **expected_names = malloc(sizeof(char*) * num_expected);
    char* joined_expected_names;
    if (expected_names != NULL) {
        size_t total_size = (num_expected * 2); // Overhead for joining
        for (int i = 0; i < num_expected; i++) {
            HasherState expected = expected_states[i];
            const char *expected_name = state_name(expected);
            total_size += strlen(expected_name);
        }
        if (num_expected > 0 ) {
            joined_expected_names = malloc(total_size + 1);
            if (joined_expected_names != NULL) {
                joined_expected_names[0] = '\0'; // Start with zero length
                strcat(joined_expected_names, expected_names[0]);
                for (int i = 1; i < num_expected; i++) {
                    strcat(joined_expected_names, ", ");
                    strcat(joined_expected_names, expected_names[i]);
                }
                assert(strlen(joined_expected_names) <= total_size);
            } else {
                joined_expected_names = "OOME";
            }
        } else {
            joined_expected_names = "None";
        }
    } else {
        joined_expected_names = "OOME";
    }
    fprintf(stderr, "Expected ShaHasher states {%s}, but got %s\n", actual_name, joined_expected_names);
    abort();
}
