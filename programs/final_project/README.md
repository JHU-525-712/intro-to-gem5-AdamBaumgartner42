# This is my final project
”Investigating Processor Internals for Normalized Fuel Economy Inference in Class 8 Trucks”

## Step 1: Demonstrate gem5 SE simulation of ARM A7 microprocessor
Use ARM SE (syscall emulation) mode with an ARMv7 core:

Use a CPU model close to the Cortex-A7: MinorCPU is a good stand-in

### File structure


### Compile your code spaces as ARMv7 Linux userspace
aarch64-linux-gnu-gcc -O2 -static can_sim_1.c -o sim_workload

### Update Binary Resource in run_minor_arm64.py
binary = BinaryResource(local_path="sim_workload")

### Run the project with a cache prefetcher
../../gem5/build/ARM/gem5.opt -d m6out run_minor_arm64.py

### Run the project without a cache prefetcher
../../gem5/build/ARM/gem5.opt -d m6out run_minor_arm64_tutorial.py

### Run the sweep
programs/final_project# python3 sweep_workload.py

