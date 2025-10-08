# Adam's notes

## Version Control Notes

git commit -m "commit msg" --no-verify
git push origin "branch name"

## Step 0

1. Navigate to /workspaces/intro-to-gem5-AdamBaumgartner42/programs

## Simulating ARM

1. Compile pi_arm
aarch64-linux-gnu-gcc -O2 -static -o pi_arm64 compute_pi.c

2. Run gem5 simulation, time: < 10 seconds
gem5 l1_l2_l3_cache_arm64.py pi_arm64

## Simulating x86

1. Compile pi_x86
gcc -O2 -static -o pi_x86 compute_pi.c

2. Run gem5 simulation, time: < 10 seconds
gem5 l1_l2_l3_cache_x86.py pi_x86

Tomosulo Simulation x86
intro-to-gem5-AdamBaumgartner42/programs# gem5 tomasulo_working_stats.py pi_x86


## --- Reference ---

## Simulating RISCV

1. Compile pi_riscv
riscv64-linux-gnu-gcc -O2 -static -o pi_riscv compute_pi.c

2. Run gem5 simulation, time: < 10 seconds
gem5 l1_cache_riscv.py pi_riscv
