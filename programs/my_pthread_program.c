#include <pthread.h>
#include <stdio.h>

#define NUM_THREADS 4
volatile int shared_var = 0;

void* simple_worker(void* arg) {
    int id = *(int*)arg;

    for (int i = 0; i < 100; i++) {
        // Read (I->S or stays S)
        int val = shared_var;

        // Write (S->M, causes invalidations)
        shared_var = id * 100 + i;

        printf("Thread %d: read %d, wrote %d\n", id, val, shared_var);
        fflush(stdout);
    }
    return NULL;
}

int main() {
    pthread_t threads[NUM_THREADS];
    int ids[NUM_THREADS] = {0, 1};

    for (int i = 0; i < NUM_THREADS; i++) {
        pthread_create(&threads[i], NULL, simple_worker, &ids[i]);
    }

    for (int i = 0; i < NUM_THREADS; i++) {
        pthread_join(threads[i], NULL);
    }

    return 0;
}
