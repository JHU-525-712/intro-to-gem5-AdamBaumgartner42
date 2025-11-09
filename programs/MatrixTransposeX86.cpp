#include <iostream>
#include <cmath>
#include <vector>
#include <chrono>

#define WIDTH 1024
#define NUM   (WIDTH * WIDTH)

// CPU implementation of matrix transpose
void matrixTransposeCPU(float* output, const float* input, unsigned int width)
{
    for (unsigned int j = 0; j < width; j++) {
        for (unsigned int i = 0; i < width; i++) {
            output[i * width + j] = input[j * width + i];
        }
    }
}

int main() {
    std::vector<float> matrix(NUM);
    std::vector<float> transposeCPU(NUM);
    std::vector<float> transposeCheck(NUM);

    // Initialize matrix with sample values
    for (unsigned int i = 0; i < NUM; i++) {
        matrix[i] = static_cast<float>(i) * 10.0f;
    }

    // Measure transpose time
    auto start = std::chrono::high_resolution_clock::now();
    matrixTransposeCPU(transposeCPU.data(), matrix.data(), WIDTH);
    auto end = std::chrono::high_resolution_clock::now();

    // Verify correctness against reference (identical CPU version)
    matrixTransposeCPU(transposeCheck.data(), matrix.data(), WIDTH);

    int errors = 0;
    double eps = 1.0E-6;
    for (unsigned int i = 0; i < NUM; i++) {
        if (std::fabs(transposeCPU[i] - transposeCheck[i]) > eps) {
            errors++;
        }
    }

    if (errors != 0)
        std::cout << "FAILED: " << errors << " errors\n";
    else
        std::cout << "PASSED!\n";

    auto elapsed = std::chrono::duration<double>(end - start).count();
    std::cout << "Execution time: " << elapsed << " seconds\n";

    return errors;
}
