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

#define DEFAULT_NUM_STEPS           1000    // how many outer iterations
#define DEFAULT_INF_WORK_PER_STEP   8       // how many dot products per step

static int g_num_steps = DEFAULT_NUM_STEPS;
static int g_inf_work_per_step = DEFAULT_INF_WORK_PER_STEP;

#define RT_LEN              64      // size of real-time buffer
#define INF_LEN             1024    // length of inference vector

#define INF_IN   INF_LEN      // reuse existing length as input dimension
#define INF_HID  32           // tune this: 16, 32, 64, ...
#define INF_OUT  8            // tune this too

// Quantized weights and biases
int16_t inf_w1[INF_HID][INF_IN];   // hidden layer weights
int16_t inf_b1[INF_HID];           // hidden layer biases

int16_t inf_w2[INF_OUT][INF_HID];  // output layer weights
int16_t inf_b2[INF_OUT];           // output layer biases

// For accumulating some global result so the compiler can’t dead-code it
int64_t inf_out_accumulator = 0;

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
CanFrame can_ring[CAN_MSGS];

/* State variables */
// Driver / dynamics
static float engine_rpm;
static float veh_speed;
static float engine_torque_req;
static float engine_torque_act;
static float accel_pedal;
static float brake_pedal;
static int   gear_index;
static int   cruise_on;
static int   retarder_level;
static int   wheel_slip_flag;

// Powertrain / fuel
static float fuel_rate;
static float fuel_rail_pressure;
static float boost_pressure;
static float intake_air_temp;
static float exhaust_gas_temp;
static float engine_load_pct;
static int   aftertreat_regen_on;
static float alternator_load_pct;
static float hybrid_power_kw;
static float coolant_temp;

// Environment / road
static float road_grade;
static float ambient_temp;
static float wind_speed;
static float wind_dir_rel;
static float speed_limit;
static float road_curvature;
static int   road_surface_code;
static float traffic_density;

// Load / config
static float gv_weight_est;
static int   trailer_type_code;
static int   aero_package_on;
static float tire_pressure_deviation;

// Diagnostics
static uint32_t diag_frame_cnt;

/* ===== Realistic CAN decoding step ===== */
static void rt_step(void)
{
    for (int i = 0; i < CAN_MSGS; ++i) {
        const CanFrame* f = &can_ring[i];

        switch (f->id) {

        /* === Engine + torque + load: ID 0x100 ===
         * Byte 0-1 : engine RPM   (0.125 rpm/bit)
         * Byte 2-3 : torque_req   (0.1 Nm/bit, signed)
         * Byte 4-5 : torque_act   (0.1 Nm/bit, signed)
         * Byte 6   : engine load  (0.4 %/bit -> 0..100%)
         * Byte 7   : aftertreat regen flag (bit0)
         */
        case 0x100: {
            uint16_t raw_rpm  = (uint16_t)((f->data[0] << 8) | f->data[1]);
            int16_t  raw_treq = (int16_t)((f->data[2] << 8) | f->data[3]);
            int16_t  raw_tact = (int16_t)((f->data[4] << 8) | f->data[5]);

            engine_rpm         = (float)raw_rpm * 0.125f;
            engine_torque_req  = (float)raw_treq * 0.1f;
            engine_torque_act  = (float)raw_tact * 0.1f;
            engine_load_pct    = (float)f->data[6] * 0.4f;     // 0..100 %
            aftertreat_regen_on = (f->data[7] & 0x01) ? 1 : 0;
            break;
        }

        /* === Vehicle / driver controls: ID 0x120 ===
         * Byte 0-1 : vehicle speed   (0.01 km/h per bit)
         * Byte 2   : accel pedal     (0.4 %/bit)
         * Byte 3   : brake pedal     (0.4 %/bit)
         * Byte 4   : gear index      (signed, -8..+31)
         * Byte 5   : bit0=cruise_on, bits1-3=retarder_level
         * Byte 6   : wheel slip flag (bit0)
         */
        case 0x120: {
            uint16_t raw_speed = (uint16_t)((f->data[0] << 8) | f->data[1]);
            veh_speed          = (float)raw_speed * 0.01f;

            accel_pedal        = (float)f->data[2] * 0.4f;
            brake_pedal        = (float)f->data[3] * 0.4f;
            gear_index         = (int8_t)f->data[4];

            cruise_on          = (f->data[5] & 0x01) ? 1 : 0;
            retarder_level     = (f->data[5] >> 1) & 0x07;   // 0..7
            wheel_slip_flag    = (f->data[6] & 0x01) ? 1 : 0;
            break;
        }

        /* === Brake system: ID 0x221 ===
         * Byte 0-1 : brake pressure   (raw-1000)*0.05 bar
         * Byte 2   : road surface code (0=dry,1=wet,2=snow,...)
         * Byte 3   : tire pressure deviation (0.1 psi/bit, signed)
         */
        case 0x221: {
            uint16_t raw = (uint16_t)((f->data[0] << 8) | f->data[1]);
            // You had this previously:
            brake_pedal = (float)(raw - 1000) * 0.05f;

            road_surface_code      = (int)f->data[2];
            int8_t raw_tp_dev      = (int8_t)f->data[3];
            tire_pressure_deviation = (float)raw_tp_dev * 0.1f;
            break;
        }

        /* === Powertrain / fuel: ID 0x230 ===
         * Byte 0-1 : fuel rate        (0.01 L/h per bit)
         * Byte 2-3 : fuel rail press  (1 bar per bit)
         * Byte 4-5 : boost pressure   (0.1 bar per bit)
         * Byte 6   : alternator load  (0.4 %/bit)
         * Byte 7   : hybrid power kW  (0.5 kW/bit, signed)
         */
        case 0x230: {
            uint16_t raw_fuel_rate = (uint16_t)((f->data[0] << 8) | f->data[1]);
            uint16_t raw_rail      = (uint16_t)((f->data[2] << 8) | f->data[3]);
            uint16_t raw_boost     = (uint16_t)((f->data[4] << 8) | f->data[5]);
            int8_t   raw_hybrid    = (int8_t)f->data[7];

            fuel_rate           = (float)raw_fuel_rate * 0.01f;
            fuel_rail_pressure  = (float)raw_rail;
            boost_pressure      = (float)raw_boost * 0.1f;
            alternator_load_pct = (float)f->data[6] * 0.4f;
            hybrid_power_kw     = (float)raw_hybrid * 0.5f;
            break;
        }

        /* === Temps / engine environment: ID 0x330 ===
         * Byte 0 : coolant temp (°C, signed)
         * Byte 1 : intake air temp (°C, signed)
         * Byte 2-3 : exhaust gas temp (0.1 °C/bit)
         * Byte 4 : ambient temp (°C, signed)
         */
        case 0x330: {
            int8_t raw_coolant = (int8_t)f->data[0];
            int8_t raw_iat     = (int8_t)f->data[1];
            uint16_t raw_egt   = (uint16_t)((f->data[2] << 8) | f->data[3]);
            int8_t raw_amb     = (int8_t)f->data[4];

            coolant_temp      = (float)raw_coolant;
            intake_air_temp   = (float)raw_iat;
            exhaust_gas_temp  = (float)raw_egt * 0.1f;
            ambient_temp      = (float)raw_amb;
            break;
        }

        /* === Road & environment: ID 0x340 ===
         * Byte 0-1 : road grade       (-20.0..+20.0 %, 0.01 %/bit signed)
         * Byte 2-3 : wind speed       (0.1 m/s per bit)
         * Byte 4   : wind dir rel     (-128..127 -> -180..+180 deg approx)
         * Byte 5-6 : road curvature   (1e-6 1/m per bit, signed)
         * Byte 7   : traffic density  (0.5 %/bit)
         */
        case 0x340: {
            int16_t raw_grade = (int16_t)((f->data[0] << 8) | f->data[1]);
            uint16_t raw_wspd = (uint16_t)((f->data[2] << 8) | f->data[3]);
            int8_t raw_wdir   = (int8_t)f->data[4];
            int16_t raw_curv  = (int16_t)((f->data[5] << 8) | f->data[6]);

            road_grade       = (float)raw_grade * 0.01f;
            wind_speed       = (float)raw_wspd * 0.1f;
            wind_dir_rel     = (float)raw_wdir * (180.0f / 128.0f);
            road_curvature   = (float)raw_curv * 1e-6f;
            traffic_density  = (float)f->data[7] * 0.5f;
            break;
        }

        /* === Speed limit + map data: ID 0x350 ===
         * Byte 0-1 : speed limit (0.1 km/h per bit)
         * Byte 2-5 : reserved for map/segment ID (ignored here)
         */
        case 0x350: {
            uint16_t raw_sl = (uint16_t)((f->data[0] << 8) | f->data[1]);
            speed_limit     = (float)raw_sl * 0.1f;
            break;
        }

        /* === Load & configuration: ID 0x360 ===
         * Byte 0-1 : GVW estimate      (100 kg/bit)
         * Byte 2   : trailer type code
         * Byte 3   : aero package flag (bit0)
         */
        case 0x360: {
            uint16_t raw_gvw = (uint16_t)((f->data[0] << 8) | f->data[1]);

            gv_weight_est     = (float)raw_gvw * 100.0f;
            trailer_type_code = (int)f->data[2];
            aero_package_on   = (f->data[3] & 0x01) ? 1 : 0;
            break;
        }

        /* === Fallback / diagnostic frames (CAN-FD style) === */
        default: {
            // small checksum on any unhandled frame
            uint32_t crc = 0;
            for (int b = 0; b < f->len; ++b)
                crc = (crc * 31u) ^ (uint32_t)f->data[b];

            if ((crc & 0xFFFFu) == 0u)
                diag_frame_cnt++;
            break;
        }
        } // end switch
    } // end for
}

/* ===== "Inference" step =====
 *
 * Computes a dot product between weights and input.
 * Repeats it g_inf_work_per_step times per outer step.
 */
static void inference_step1(void)
{
    for (int rep = 0; rep < g_inf_work_per_step; ++rep) {
        int64_t acc = 0;
        for (int i = 0; i < INF_LEN; ++i) {
            acc += (int32_t)inf_weights[i] * (int32_t)inf_input[i];
        }
        inf_accumulator += acc;
    }
}


/* ===== "Inference" step (heavier, 2-layer MLP-ish) =====
 *
 * For each repetition:
 *   1) Hidden layer: h = ReLU( W1 * x + b1 )
 *   2) Output layer: y = ReLU( W2 * h + b2 )
 *   3) Accumulate outputs into a global sum so work is "observable"
 *
 * All integer/fixed-point.
 */
static void inference_step2(void)
{
    // Local buffer for hidden activations
    int32_t hidden[INF_HID];

    for (int rep = 0; rep < g_inf_work_per_step; ++rep) {

        /* --- Hidden layer: h_j = ReLU( sum_i w1[j][i] * x[i] + b1[j] ) --- */
        for (int j = 0; j < INF_HID; ++j) {
            int64_t acc = (int64_t)inf_b1[j];

            // dot product for hidden unit j
            for (int i = 0; i < INF_IN; ++i) {
                acc += (int64_t)inf_w1[j][i] * (int64_t)inf_input[i];
            }

            // Simple fixed-point scaling (optional; can be a right shift)
            // For now just clamp to int32_t range:
            if (acc > INT32_MAX) acc = INT32_MAX;
            if (acc < INT32_MIN) acc = INT32_MIN;

            int32_t v = (int32_t)acc;

            // ReLU activation
            if (v < 0) v = 0;

            hidden[j] = v;
        }

        /* --- Output layer: y_k = ReLU( sum_j w2[k][j] * h[j] + b2[k] ) --- */
        for (int k = 0; k < INF_OUT; ++k) {
            int64_t acc = (int64_t)inf_b2[k];

            for (int j = 0; j < INF_HID; ++j) {
                acc += (int64_t)inf_w2[k][j] * (int64_t)hidden[j];
            }

            // Clamp to 32-bit, ReLU
            if (acc > INT32_MAX) acc = INT32_MAX;
            if (acc < INT32_MIN) acc = INT32_MIN;

            int32_t y = (int32_t)acc;
            if (y < 0) y = 0;

            // Fold into a global accumulator so the work "matters"
            inf_out_accumulator += (int64_t)y;
        }
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
        inference_step1();
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

