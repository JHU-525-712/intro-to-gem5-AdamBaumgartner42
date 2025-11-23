#!/usr/bin/env python3
import os
import subprocess
import itertools

GEM5   = "../../gem5/build/ARM/gem5.opt"
CONFIG = "run_minor_arm64.py"
OUT_ROOT = "arch_workload"

BENCH = ("sim_workload", "can_sim_1")

CPU_CLOCKS = ["600MHz", "1GHz"]
L1_SIZES   = ["32kB"]
L2_SIZES   = ["256kB", "1MB"]

STEPS_VALUES     = [10000]
INF_WORK_VALUES  = [16]

def main():
    os.makedirs(OUT_ROOT, exist_ok=True)

    bin_path, bench_name = BENCH

    for cpu, l1, l2, steps, inf_work in itertools.product(
        CPU_CLOCKS, L1_SIZES, L2_SIZES, STEPS_VALUES, INF_WORK_VALUES
    ):
        outdir = os.path.join(
            OUT_ROOT,
            f"{bench_name}_cpu{cpu}_l1{l1}_l2{l2}_steps{steps}_work{inf_work}"
            .replace(" ", "").replace("/", "")
        )
        os.makedirs(outdir, exist_ok=True)

        print(f"Running {bench_name}: cpu={cpu}, L1={l1}, L2={l2}, "
              f"steps={steps}, inf_work={inf_work} -> {outdir}")

        cmd = [
            GEM5,
            "-d", outdir,
            CONFIG,
            "--cpu-clock", cpu,
            "--l1d-size", l1,
            "--l1i-size", l1,
            "--l2-size", l2,
        ]

        env = os.environ.copy()
        env["BENCH_BINARY"] = bin_path
        env["BENCH_ARGS"] = f"--steps {steps} --inf-work {inf_work}"

        subprocess.run(cmd, check=True, env=env)

if __name__ == "__main__":
    main()
