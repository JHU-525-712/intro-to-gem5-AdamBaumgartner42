#include <stdio.h>

int main(void) {
    volatile long sum = 0;
    for (long i = 0; i < 1000000; ++i)
        sum += i;
    printf("sum = %ld\n", sum);
    return 0;
}
