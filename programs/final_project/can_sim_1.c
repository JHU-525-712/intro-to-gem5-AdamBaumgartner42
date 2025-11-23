/**
 * @file mixed_rt_infer.c
 * @brief Tiny mixed real-time + inference-like benchmark.
 *
 * The main loop:
 *   - First runs a "real-time" step over a small buffer.
 *   - Then does some inference-like dot products.
 *
 * This is meant to be simple and deterministic for gem5 MinorCPU.
 */

#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

/* ===== Parameters (you can tweak these later) ===== */

#define DEFAULT_NUM_STEPS           10000   // how many outer iterations
#define DEFAULT_INF_WORK_PER_STEP   8       // how many dot products per step

static int g_num_steps = DEFAULT_NUM_STEPS;
static int g_inf_work_per_step = DEFAULT_INF_WORK_PER_STEP;

#define RT_LEN              64      // size of real-time buffer
#define INF_LEN             128     // length of inference vector

/* ===== Parser for arguments ===== */
static void parse_args(int argc, char **argv)
{
    for (int i = 1; i < argc; ++i) {
        if (i + 1 < argc && strcmp(argv[i], "--steps") == 0) {
            g_num_steps = atoi(argv[++i]);
        } else if (i + 1 < argc && strcmp(argv[i], "--inf-work") == 0) {
            g_inf_work_per_step = atoi(argv[++i]);
        }
    }
}

/* ===== Global state for RT side ===== */

static int32_t rt_buf[RT_LEN];
static int64_t rt_sum_norm  = 0;
static int64_t rt_sum_anom  = 0;

/* ===== Global state for inference side ===== */

static int16_t inf_weights[INF_LEN];
static int16_t inf_input[INF_LEN];
static int64_t inf_accumulator = 0;

/* ===== Initialize data ===== */

static void init_data(void)
{
    for (int i = 0; i < RT_LEN; ++i) {
        rt_buf[i] = (int32_t)(i * 7 + 3);
    }

    for (int i = 0; i < INF_LEN; ++i) {
        inf_weights[i] = (int16_t)((i * 5 + 1) & 0x7FFF);
        inf_input[i]   = (int16_t)((i * 3 + 2) & 0x7FFF);
    }
}

#define CAN_MSGS  128  // simulate ~128 frames per cycle
#define CAN_MAX_DATA 64

typedef struct {
    uint32_t id;
    uint8_t  len;
    uint8_t  data[CAN_MAX_DATA];
} CanFrame;

/* Incoming CAN buffer */
extern CanFrame can_ring[CAN_MSGS];

/* State variables */
static float veh_speed = 0.0f;
static float engine_rpm = 0.0f;
static float coolant_temp = 0.0f;
static float brake_pressure = 0.0f;
static uint32_t diag_frame_cnt = 0;

/* ===== Realistic CAN decoding step ===== */
static void rt_step(void)
{
    for (int i = 0; i < CAN_MSGS; ++i) {
        const CanFrame* f = &can_ring[i];

        switch (f->id) {

        /* === Engine RPM: ID 0x100 === */
        case 0x100: {
            uint16_t raw = (f->data[0] << 8) | f->data[1];
            engine_rpm = (float)raw * 0.125f;   // scale factor
            break;
        }

        /* === Vehicle speed: ID 0x120 === */
        case 0x120: {
            uint16_t raw = (f->data[2] << 8) | f->data[3];
            veh_speed = (float)raw * 0.01f;     // 0.01 km/h per tick
            break;
        }

        /* === Brake pressure: ID 0x221 === */
        case 0x221: {
            uint16_t raw = (f->data[0] << 8) | f->data[1];
            brake_pressure = (float)(raw - 1000) * 0.05f;
            break;
        }

        /* === Coolant temperature: ID 0x330 === */
        case 0x330: {
            int8_t raw = (int8_t)f->data[0];
            coolant_temp = (float)raw;  // already °C
            break;
        }

        /* === Diagnostic frame: CAN-FD style === */
        default:
            // do a small checksum
            uint32_t crc = 0;
            for (int b = 0; b < f->len; ++b)
                crc = (crc * 31) ^ f->data[b];

            if ((crc & 0xFFFF) == 0)
                diag_frame_cnt++;

            break;
        }
    }
}

/* ===== "Inference" step =====
 *
 * Computes a dot product between weights and input.
 * Repeats it g_inf_work_per_step times per outer step.
 */
static void inference_step(void)
{
    for (int rep = 0; rep < g_inf_work_per_step; ++rep) {
        int64_t acc = 0;
        for (int i = 0; i < INF_LEN; ++i) {
            acc += (int32_t)inf_weights[i] * (int32_t)inf_input[i];
        }
        inf_accumulator += acc;
    }
}

/* ===== Main: simple mixed workload ===== */

int main(void)
{
    init_data();

    for (int step = 0; step < g_num_steps; ++step) {
        // 1) Always do the "real-time" work first.
        rt_step();

        // 2) Then burn cycles on inference-like work.
        inference_step();
    }

    // Print a few values so the compiler can't optimize everything away.
    printf("steps=%d inf_work=%d rt_sum_norm=%lld rt_sum_anom=%lld inf_acc=%lld rt_buf0=%d\n",
        g_num_steps, g_inf_work_per_step,
        (long long)rt_sum_norm,
        (long long)rt_sum_anom,
        (long long)inf_accumulator,
        rt_buf[0]);

    return 0;
}

