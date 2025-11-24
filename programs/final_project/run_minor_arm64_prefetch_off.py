#!/usr/bin/env python3
import os, sys, argparse
import m5
from m5.objects import (
    System, SrcClockDomain, VoltageDomain, SystemXBar, AddrRange,
    MemCtrl, DDR3_1600_8x8, Root,
    MinorCPU, Process, SEWorkload
)

# Ensure we can import caches_no_prefetch.py
this_dir = os.path.dirname(os.path.abspath(__file__))
if this_dir not in sys.path:
    sys.path.append(this_dir)

from caches_no_prefetch import L1ICache, L1DCache, L2Cache

# ------------------------------
# 1. Parse args
# ------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--cpu-clock", default="1GHz")
parser.add_argument("--l1d-size", default="32kB")
parser.add_argument("--l1i-size", default="32kB")
parser.add_argument("--l2-size",  default="1MB")
args = parser.parse_args()

# ------------------------------
# 2. System definition
# ------------------------------
system = System()
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.cpu_clock
system.clk_domain.voltage_domain = VoltageDomain()

system.mem_mode = "timing"
system.mem_ranges = [AddrRange("2GB")]

# Top-level memory bus
system.membus = SystemXBar()

# Required for SE mode
system.system_port = system.membus.cpu_side_ports


# ------------------------------
# 3. CPU
# ------------------------------
system.cpu = MinorCPU()
system.cpu.createThreads()

# ARM SE: just create the interrupt controller, no extra wiring
system.cpu.createInterruptController()


from caches_no_prefetch import L1ICache, L1DCache, L2Cache
# ------------------------------
# 4. Caches
# ------------------------------
system.l2bus = SystemXBar()

system.icache = L1ICache(size=args.l1i_size)
system.icache.connectCPU(system.cpu)
system.icache.connectBus(system.l2bus)

system.dcache = L1DCache(size=args.l1d_size)
system.dcache.connectCPU(system.cpu)
system.dcache.connectBus(system.l2bus)

system.l2cache = L2Cache(size=args.l2_size)
system.l2cache.connectCPUSideBus(system.l2bus)
system.l2cache.connectMemSideBus(system.membus)


# ------------------------------
# 5. DRAM controller
# ------------------------------
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8(range=system.mem_ranges[0])
system.mem_ctrl.port = system.membus.mem_side_ports


# ------------------------------
# 6. Workload
# ------------------------------
bin_path = os.getenv("BENCH_BINARY", "sim_workload")
bench_args = os.getenv("BENCH_ARGS", "").split()

system.workload = SEWorkload.init_compatible(bin_path)

process = Process()
process.cmd = [bin_path] + bench_args
system.cpu.workload = process


# ------------------------------
# 7. Run
# ------------------------------
root = Root(full_system=False, system=system)
m5.instantiate()
print("Beginning simulation!")
exit_event = m5.simulate()
print(f"Exited @ {m5.curTick()} because {exit_event.getCause()}")
