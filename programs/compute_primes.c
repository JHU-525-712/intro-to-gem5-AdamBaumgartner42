#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

void compute_primes(int limit) {
    bool *is_prime = malloc((limit + 1) * sizeof(bool));
    if (is_prime == NULL) {
        return;
    }

    for (int i = 2; i <= limit; i++) {
        is_prime[i] = true;
    }

    for (int p = 2; p * p <= limit; p++) {
        if (is_prime[p]) {
            for (int i = p * p; i <= limit; i += p) {
                is_prime[i] = false;
            }
        }
    }

    free(is_prime);
    printf("End Program\n");

}

int main() {
    int limit = 1000000;


    compute_primes(limit);


    return 0;
}
