from gem5.components.boards.simple_board import SimpleBoard
from gem5.components.processors.simple_processor import SimpleProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.memory.single_channel import SingleChannelDDR3_1600
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy \
    import PrivateL1PrivateL2CacheHierarchy
from gem5.isas import ISA
from gem5.resources.resource import Resource
from gem5.simulate.simulator import Simulator
from gem5.resources.resource import BinaryResource

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
    l1d_size="32kB",
    l1i_size="32kB",
    l2_size="1MB",
)

memory = SingleChannelDDR3_1600(size="2GB")

# ------------------------------
# 3. System board
# ------------------------------
board = SimpleBoard(
    clk_freq="1GHz",
    processor=processor,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

# ------------------------------
# 4. Workload (AArch64 SE mode)
# ------------------------------
binary = BinaryResource(
    local_path="programs/final_project/hello_arm64"
    # or just "hello_arm64" if you run gem5 from programs/final_project
)
board.set_se_binary_workload(binary)

# ------------------------------
# 5. Run simulation
# ------------------------------
simulator = Simulator(board=board)
simulator.run()
