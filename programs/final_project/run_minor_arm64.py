import os
import argparse
from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.memory.single_channel import SingleChannelDDR3_1600
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy \
    import PrivateL1PrivateL2CacheHierarchy
from gem5.isas import ISA
from gem5.resources.resource import BinaryResource
from gem5.simulate.simulator import Simulator

# ------------------------------
# Parse arguments passed from sweep script
# ------------------------------

parser = argparse.ArgumentParser()
parser.add_argument("--cpu-clock", default="1GHz")
parser.add_argument("--l1d-size", default="32kB")
parser.add_argument("--l1i-size", default="32kB")
parser.add_argument("--l2-size",  default="1MB")
args = parser.parse_args()

# ------------------------------
# 1. CPU: MinorCPU
# ------------------------------
processor = SimpleProcessor(
    cpu_type=CPUTypes.MINOR,
    isa=ISA.ARM,
    num_cores=1,
)

# ------------------------------
# 2. Memory & caches
# ------------------------------
cache_hierarchy = PrivateL1PrivateL2CacheHierarchy(
    l1d_size=args.l1d_size,
    l1i_size=args.l1i_size,
    l2_size=args.l2_size,
)

memory = SingleChannelDDR3_1600(size="2GB")

# ------------------------------
# 3. System board
# ------------------------------
board = SimpleBoard(
    clk_freq=args.cpu_clock,
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

# ------------------------------
# 4. Workload (AArch64 SE mode)
# ------------------------------

# Which binary to run
bin_path = os.getenv(
    "BENCH_BINARY",
    "sim_workload",
)

# Arguments for that binary (space-separated string)
bench_args_str = os.getenv("BENCH_ARGS", "")
bench_args = bench_args_str.split() if bench_args_str else []

binary = BinaryResource(local_path=bin_path)
board.set_se_binary_workload(binary, arguments=bench_args)

# ------------------------------
# 5. Run simulation
# ------------------------------
simulator = Simulator(board=board)
simulator.run()
