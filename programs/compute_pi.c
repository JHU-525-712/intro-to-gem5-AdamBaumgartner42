#include <stdio.h>

int main() {
    long long int n = 1000000;
    long long int i;

    double pi = 0.0;
    int sign = 1;

    // Number of iterations
    printf("Enter the number of iterations: ");

    for (i = 0; i < n; i++) {
        pi += sign * 4.0 / (2 * i + 1);
        sign = -sign;  // Alternate the sign
    }

    printf("Computed value of Pi: %.15f\n", pi);
    return 0;
}
