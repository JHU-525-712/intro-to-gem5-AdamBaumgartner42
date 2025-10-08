import os
import sys
import argparse
import m5
from m5.objects import *
from m5 import stats
import time

def parse_arguments():
    parser = argparse.ArgumentParser(description='gem5 Tomasulo-style O3 Processor Simulation with Statistics')
    parser.add_argument('binary', help='Path to X86 binary to execute')
    parser.add_argument('--rob-entries', type=int, default=192, help='ROB entries (default: 192)')
    parser.add_argument('--iq-entries', type=int, default=64, help='Instruction Queue entries (default: 64)')
    parser.add_argument('--lsq-entries', type=int, default=32, help='Load/Store Queue entries (default: 32)')
    parser.add_argument('--phys-int-regs', type=int, default=256, help='Physical integer registers (default: 256)')
    parser.add_argument('--phys-float-regs', type=int, default=256, help='Physical FP registers (default: 256)')
    parser.add_argument('--fetch-width', type=int, default=8, help='Fetch width (default: 8)')
    parser.add_argument('--decode-width', type=int, default=8, help='Decode width (default: 8)')
    parser.add_argument('--rename-width', type=int, default=8, help='Rename width (default: 8)')
    parser.add_argument('--issue-width', type=int, default=8, help='Issue width (default: 8)')
    parser.add_argument('--wb-width', type=int, default=8, help='Writeback width (default: 8)')
    parser.add_argument('--commit-width', type=int, default=8, help='Commit width (default: 8)')
    parser.add_argument('--cpu-clock', default='2GHz', help='CPU clock frequency (default: 2GHz)')
    parser.add_argument('--l1i-size', default='32kB', help='L1I cache size (default: 32kB)')
    parser.add_argument('--l1d-size', default='64kB', help='L1D cache size (default: 64kB)')
    parser.add_argument('--l2-size', default='2MB', help='L2 cache size (default: 2MB)')
    parser.add_argument('--memory-size', default='512MB', help='System memory size (default: 512MB)')
    parser.add_argument('--stats-file', default='m5out/stats.txt', help='Statistics file path')

    return parser.parse_args()

class L1ICache(Cache):
    def __init__(self, size="32kB"):
        super(L1ICache, self).__init__()
        self.size = size
        self.assoc = 2
        self.tag_latency = 2
        self.data_latency = 2
        self.response_latency = 2
        self.mshrs = 4
        self.tgts_per_mshr = 20

class L1DCache(Cache):
    def __init__(self, size="64kB"):
        super(L1DCache, self).__init__()
        self.size = size
        self.assoc = 2
        self.tag_latency = 2
        self.data_latency = 2
        self.response_latency = 2
        self.mshrs = 4
        self.tgts_per_mshr = 20

class L2Cache(Cache):
    def __init__(self, size="2MB"):
        super(L2Cache, self).__init__()
        self.size = size
        self.assoc = 8
        self.tag_latency = 20
        self.data_latency = 20
        self.response_latency = 20
        self.mshrs = 20
        self.tgts_per_mshr = 12

def extract_stat_value(stats_content, stat_name):
    """Extract a specific statistic value from stats.txt content"""
    for line in stats_content:
        if line.strip().startswith(stat_name):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    return float(parts[1])
                except ValueError:
                    continue
    return None

def wait_for_stats_file(stats_file, max_wait=5):
    """Wait for stats file to be written and have content"""
    wait_time = 0
    while wait_time < max_wait:
        if os.path.exists(stats_file):
            size = os.path.getsize(stats_file)
            if size > 100:  # Wait for substantial content
                return True
        time.sleep(0.5)
        wait_time += 0.5
    return False

def analyze_basic_performance(stats_content):
    """Analyze basic CPU performance metrics"""
    print("\n" + "="*60)
    print("BASIC PERFORMANCE ANALYSIS")
    print("="*60)

    # Extract basic performance metrics
    sim_seconds = extract_stat_value(stats_content, "simSeconds")
    sim_ticks = extract_stat_value(stats_content, "simTicks")
    sim_insts = extract_stat_value(stats_content, "simInsts")
    sim_ops = extract_stat_value(stats_content, "simOps")
    num_cycles = extract_stat_value(stats_content, "system.cpu.numCycles")
    cpi = extract_stat_value(stats_content, "system.cpu.cpi")
    ipc = extract_stat_value(stats_content, "system.cpu.ipc")

    if sim_seconds:
        print(f"Simulation Time: {sim_seconds:.6f} seconds")
    if sim_ticks:
        print(f"Simulation Ticks: {int(sim_ticks):,}")
    if sim_insts:
        print(f"Instructions Simulated: {int(sim_insts):,}")
    if sim_ops:
        print(f"Operations Simulated: {int(sim_ops):,}")
    if num_cycles:
        print(f"CPU Cycles: {int(num_cycles):,}")
    if cpi:
        print(f"Cycles Per Instruction (CPI): {cpi:.3f}")
    if ipc:
        print(f"Instructions Per Cycle (IPC): {ipc:.3f}")

    # Calculate additional metrics
    if sim_insts and sim_ops and sim_insts > 0:
        ops_per_inst = sim_ops / sim_insts
        print(f"Operations Per Instruction: {ops_per_inst:.2f}")

def analyze_cache_performance(stats_content):
    """Analyze cache hit/miss ratios and performance"""
    print("\n" + "="*60)
    print("CACHE PERFORMANCE ANALYSIS")
    print("="*60)

    # L1 Data Cache
    l1d_hits = extract_stat_value(stats_content, "system.cpu.dcache.overallHits::total")
    l1d_misses = extract_stat_value(stats_content, "system.cpu.dcache.overallMisses::total")
    l1d_miss_latency = extract_stat_value(stats_content, "system.cpu.dcache.demandMissLatency::cpu.data")

    if l1d_hits is not None and l1d_misses is not None:
        l1d_accesses = l1d_hits + l1d_misses
        l1d_hit_rate = (l1d_hits / l1d_accesses) * 100
        l1d_miss_rate = (l1d_misses / l1d_accesses) * 100

        print(f"L1 Data Cache:")
        print(f"  Accesses: {int(l1d_accesses):,}")
        print(f"  Hits: {int(l1d_hits):,} ({l1d_hit_rate:.2f}%)")
        print(f"  Misses: {int(l1d_misses):,} ({l1d_miss_rate:.2f}%)")

        if l1d_miss_latency and l1d_misses > 0:
            avg_miss_latency = l1d_miss_latency / l1d_misses
            print(f"  Average Miss Latency: {avg_miss_latency:.1f} cycles")

    # L1 Instruction Cache
    l1i_hits = extract_stat_value(stats_content, "system.cpu.icache.overallHits::total")
    l1i_misses = extract_stat_value(stats_content, "system.cpu.icache.overallMisses::total")

    if l1i_hits is not None and l1i_misses is not None:
        l1i_accesses = l1i_hits + l1i_misses
        l1i_hit_rate = (l1i_hits / l1i_accesses) * 100
        l1i_miss_rate = (l1i_misses / l1i_accesses) * 100

        print(f"\nL1 Instruction Cache:")
        print(f"  Accesses: {int(l1i_accesses):,}")
        print(f"  Hits: {int(l1i_hits):,} ({l1i_hit_rate:.2f}%)")
        print(f"  Misses: {int(l1i_misses):,} ({l1i_miss_rate:.2f}%)")

    # L2 Cache
    l2_hits = extract_stat_value(stats_content, "system.l2cache.overallHits::total")
    l2_misses = extract_stat_value(stats_content, "system.l2cache.overallMisses::total")

    if l2_hits is not None and l2_misses is not None:
        l2_accesses = l2_hits + l2_misses
        l2_hit_rate = (l2_hits / l2_accesses) * 100
        l2_miss_rate = (l2_misses / l2_accesses) * 100

        print(f"\nL2 Cache:")
        print(f"  Accesses: {int(l2_accesses):,}")
        print(f"  Hits: {int(l2_hits):,} ({l2_hit_rate:.2f}%)")
        print(f"  Misses: {int(l2_misses):,} ({l2_miss_rate:.2f}%)")

def analyze_tomasulo_efficiency(stats_content):
    """Analyze Tomasulo algorithm efficiency and pipeline utilization"""
    print("\n" + "="*60)
    print("TOMASULO ALGORITHM EFFICIENCY ANALYSIS")
    print("="*60)

    # Instructions added and issued (Tomasulo reservation station activity)
    insts_added = extract_stat_value(stats_content, "system.cpu.instsAdded")
    insts_issued = extract_stat_value(stats_content, "system.cpu.instsIssued")
    squashed_insts_issued = extract_stat_value(stats_content, "system.cpu.squashedInstsIssued")
    squashed_insts_examined = extract_stat_value(stats_content, "system.cpu.squashedInstsExamined")

    print("Tomasulo Reservation Station Activity:")
    if insts_added:
        print(f"  Instructions Added to IQ: {int(insts_added):,}")
    if insts_issued:
        print(f"  Instructions Issued: {int(insts_issued):,}")
    if squashed_insts_issued:
        print(f"  Squashed Instructions Issued: {int(squashed_insts_issued):,}")
    if squashed_insts_examined:
        print(f"  Squashed Instructions Examined: {int(squashed_insts_examined):,}")

    # Calculate efficiency metrics
    if insts_added and insts_issued:
        issue_efficiency = (insts_issued / insts_added) * 100
        print(f"  Issue Efficiency: {issue_efficiency:.2f}%")

    # Branch prediction analysis
    branch_corrected_lines = [line for line in stats_content if "system.cpu.branchPred.corrected_0::" in line]
    if branch_corrected_lines:
        print(f"\nBranch Prediction Analysis:")
        total_corrected = 0
        for line in branch_corrected_lines:
            parts = line.split()
            if len(parts) >= 2:
                try:
                    count = int(parts[1])
                    total_corrected += count
                    branch_type = parts[0].split("::")[-1]
                    if count > 0:
                        print(f"  {branch_type} Corrections: {count:,}")
                except ValueError:
                    continue

        if total_corrected > 0:
            print(f"  Total Branch Corrections: {total_corrected:,}")

def analyze_statistics(stats_file):
    """Main statistics analysis function"""
    try:
        # Force statistics dump first
        print(f"Forcing statistics dump...")
        stats.dump()

        # Wait for the file to be written
        print(f"Waiting for statistics file to be written...")
        if not wait_for_stats_file(stats_file):
            print(f"Warning: Statistics file {stats_file} not ready, checking anyway...")

        if not os.path.exists(stats_file):
            print(f"Statistics file not found: {stats_file}")
            print("Checking for alternative locations...")

            # Check alternative locations
            alt_locations = ["stats.txt", "m5out/stats.txt.gz", "./stats.txt"]
            for alt_file in alt_locations:
                if os.path.exists(alt_file):
                    print(f"Found alternative stats file: {alt_file}")
                    stats_file = alt_file
                    break
            else:
                print("No statistics file found in any location.")
                return

        with open(stats_file, 'r') as f:
            stats_content = f.readlines()

        print(f"\nAnalyzing statistics from: {stats_file}")
        print(f"Total lines in stats file: {len(stats_content)}")

        if len(stats_content) < 10:
            print("Warning: Statistics file appears to be empty or very small.")
            print("First few lines:")
            for i, line in enumerate(stats_content[:5]):
                print(f"  {i+1}: {line.strip()}")
            return

        # Perform different analyses
        analyze_basic_performance(stats_content)
        analyze_cache_performance(stats_content)
        analyze_tomasulo_efficiency(stats_content)

        print(f"\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        print(f"Full statistics available in: {stats_file}")

    except Exception as e:
        print(f"Error analyzing statistics: {e}")
        import traceback
        traceback.print_exc()

def print_config(args):
    print("=== Tomasulo O3 Configuration ===")
    print(f"Binary: {args.binary}")
    print(f"ROB Entries: {args.rob_entries}")
    print(f"IQ Entries: {args.iq_entries}")
    print(f"LSQ Entries: {args.lsq_entries}")
    print(f"Physical Int Registers: {args.phys_int_regs}")
    print(f"Physical FP Registers: {args.phys_float_regs}")
    print(f"Fetch Width: {args.fetch_width}")
    print(f"Decode Width: {args.decode_width}")
    print(f"Rename Width: {args.rename_width}")
    print(f"Issue Width: {args.issue_width}")
    print(f"Writeback Width: {args.wb_width}")
    print(f"Commit Width: {args.commit_width}")
    print(f"CPU Clock: {args.cpu_clock}")
    print(f"L1I Cache: {args.l1i_size}")
    print(f"L1D Cache: {args.l1d_size}")
    print(f"L2 Cache: {args.l2_size}")
    print("=" * 40)

# Parse command line arguments
args = parse_arguments()
print_config(args)

# Create the system
system = System()

# Set up clock domain
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = args.cpu_clock
system.clk_domain.voltage_domain = VoltageDomain()

# Set up memory
system.mem_mode = "timing"
system.mem_ranges = [AddrRange(args.memory_size)]

# Create O3 CPU using the correct X86O3CPU
print("Creating X86O3CPU with Tomasulo configuration...")
try:
    system.cpu = X86O3CPU()
    cpu_type = "X86O3CPU (out-of-order)"

    # Configure Tomasulo/Out-of-order parameters
    system.cpu.fetchWidth = args.fetch_width
    system.cpu.decodeWidth = args.decode_width
    system.cpu.renameWidth = args.rename_width
    system.cpu.issueWidth = args.issue_width
    system.cpu.wbWidth = args.wb_width
    system.cpu.commitWidth = args.commit_width

    system.cpu.numROBEntries = args.rob_entries
    system.cpu.numIQEntries = args.iq_entries
    system.cpu.LQEntries = args.lsq_entries
    system.cpu.SQEntries = args.lsq_entries
    system.cpu.numPhysIntRegs = args.phys_int_regs
    system.cpu.numPhysFloatRegs = args.phys_float_regs

    # Add branch predictor for better performance
    system.cpu.branchPred = TournamentBP()

    print("Successfully created and configured X86O3CPU!")
    print("Tomasulo-style parameters applied:")
    print(f"  ROB: {system.cpu.numROBEntries}")
    print(f"  IQ (Reservation Stations): {system.cpu.numIQEntries}")
    print(f"  Load Queue: {system.cpu.LQEntries}")
    print(f"  Store Queue: {system.cpu.SQEntries}")
    print(f"  Issue Width: {system.cpu.issueWidth}")
    print(f"  Physical Registers: {system.cpu.numPhysIntRegs} int, {system.cpu.numPhysFloatRegs} fp")

except Exception as e:
    print(f"X86O3CPU failed: {e}")
    print("Falling back to X86TimingSimpleCPU...")
    system.cpu = X86TimingSimpleCPU()
    cpu_type = "X86TimingSimpleCPU (simple timing - fallback)"

# Create L1 caches with configurable sizes
system.cpu.icache = L1ICache(args.l1i_size)
system.cpu.dcache = L1DCache(args.l1d_size)

# Connect L1 caches to CPU
system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port

# Create L2 bus and cache
system.l2bus = L2XBar()
system.l2cache = L2Cache(args.l2_size)

# Connect L1 caches to L2 bus
system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports

# Connect L2 cache to L2 bus
system.l2cache.cpu_side = system.l2bus.mem_side_ports

# Create memory bus
system.membus = SystemXBar()

# Connect L2 cache to memory bus
system.l2cache.mem_side = system.membus.cpu_side_ports

# Create interrupt controller for x86
system.cpu.createInterruptController()

# x86-specific: Create interrupt controllers and connect them
system.cpu.interrupts[0].pio = system.membus.mem_side_ports
system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports

# Create memory controller
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# System port for loading binaries
system.system_port = system.membus.cpu_side_ports


# Create the workload for x86
try:
    system.workload = SEWorkload.init_compatible(args.binary)
except:
    system.workload = SEWorkload()

# Create process for the x86 binary
process = Process()
process.cmd = [args.binary]
process.executable = args.binary

# Set up x86 process
system.cpu.workload = process
system.cpu.createThreads()

# Create root object
root = Root(full_system=False, system=system)

# Instantiate all objects
m5.instantiate()

print("Beginning Tomasulo O3 simulation!")
print(f"Running x86 binary: {args.binary}")
print(f"Using: {cpu_type}")

# Start simulation
exit_event = m5.simulate()

print(f"Simulation completed!")
print(f"Exit reason: {exit_event.getCause()}")
print(f"Simulated ticks: {m5.curTick()}")

# Analyze statistics
analyze_statistics(args.stats_file)
