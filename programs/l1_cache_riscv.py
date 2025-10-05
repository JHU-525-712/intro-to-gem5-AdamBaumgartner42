import os
import sys

import m5
from m5.objects import *

# Get binary from command line
if len(sys.argv) != 2:
    print("Usage: gem5 script.py <binary>")
    sys.exit(1)

binary = sys.argv[1]


class L1ICache(Cache):
    size = "16kB"
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20


class L1DCache(Cache):
    size = "64kB"
    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 20


# Create the system
system = System()

# Set up clock domain
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

# Set up memory
system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")]

# Create CPU
system.cpu = RiscvTimingSimpleCPU()

# Create L1 caches
system.cpu.icache = L1ICache()
system.cpu.dcache = L1DCache()

# Connect L1 caches to CPU
system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port

# Create memory bus
system.membus = SystemXBar()

# Connect L1 caches to memory bus
system.cpu.icache.mem_side = system.membus.cpu_side_ports
system.cpu.dcache.mem_side = system.membus.cpu_side_ports

# Create interrupt controller
system.cpu.createInterruptController()

# Create memory controller
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# System port for loading binaries
system.system_port = system.membus.cpu_side_ports

# Create the workload
try:
    system.workload = SEWorkload.init_compatible(binary)
except:
    system.workload = SEWorkload()

# Create process for the binary
process = Process()
process.cmd = [binary]
system.cpu.workload = process
system.cpu.createThreads()

# Create root object
root = Root(full_system=False, system=system)

# Instantiate all objects
m5.instantiate()

print("Beginning simulation!")
print(f"Running: {binary}")
print("Configuration: L1 CACHE")

# Start simulation
exit_event = m5.simulate()

print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")

# Dump statistics to default location
m5.stats.dump()


# Enhanced function to extract cache stats and calculate ratios
def extract_cache_stats_with_ratios(stats_file="m5out/stats.txt"):
    cache_stats = {}
    try:
        with open(stats_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "::" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        stat_name = parts[0]
                        try:
                            stat_value = int(parts[1])
                        except ValueError:
                            try:
                                stat_value = float(parts[1])
                            except ValueError:
                                continue

                        # Look for cache-related statistics
                        if (
                            "system.cpu.icache" in stat_name
                            or "system.cpu.dcache" in stat_name
                        ):
                            if any(
                                keyword in stat_name
                                for keyword in [
                                    "overallHits",
                                    "overallMisses",
                                    "overallAccesses",
                                    "demandHits",
                                    "demandMisses",
                                    "demandAccesses",
                                ]
                            ):
                                cache_stats[stat_name] = stat_value
    except FileNotFoundError:
        print("Stats file not found")

    return cache_stats


# Function to calculate hit and miss ratios
def calculate_cache_ratios(cache_stats):
    ratios = {}

    # Define patterns to look for hits, misses, and accesses
    cache_types = ["icache", "dcache"]

    for cache_type in cache_types:
        hits = None
        misses = None
        accesses = None

        # Find hits, misses, and accesses for this cache type
        for stat_name, stat_value in cache_stats.items():
            if cache_type in stat_name:
                if "Hits" in stat_name and "total" in stat_name:
                    hits = stat_value
                elif "Misses" in stat_name and "total" in stat_name:
                    misses = stat_value
                elif "Accesses" in stat_name and "total" in stat_name:
                    accesses = stat_value

        # Calculate ratios if we have the necessary data
        if hits is not None and misses is not None:
            total_accesses = hits + misses
            if total_accesses > 0:
                hit_ratio = (hits / total_accesses) * 100
                miss_ratio = (misses / total_accesses) * 100
                ratios[f"{cache_type}_hit_ratio"] = hit_ratio
                ratios[f"{cache_type}_miss_ratio"] = miss_ratio
                ratios[f"{cache_type}_total_accesses"] = total_accesses
        elif accesses is not None and (hits is not None or misses is not None):
            if hits is not None:
                hit_ratio = (hits / accesses) * 100
                miss_ratio = 100 - hit_ratio
                ratios[f"{cache_type}_hit_ratio"] = hit_ratio
                ratios[f"{cache_type}_miss_ratio"] = miss_ratio
                ratios[f"{cache_type}_total_accesses"] = accesses

    return ratios


# Extract and print cache statistics with ratios
print("\n=== CACHE STATISTICS FROM stats.txt ===")
cache_stats = extract_cache_stats_with_ratios()

if cache_stats:
    print("Raw Cache Statistics:")
    print("-" * 50)
    for stat_name, stat_value in sorted(cache_stats.items()):
        print(f"{stat_name}: {stat_value}")

    # Calculate and display ratios
    ratios = calculate_cache_ratios(cache_stats)

    if ratios:
        print("\nCalculated Cache Performance Metrics:")
        print("-" * 50)

        # I-Cache metrics
        if "icache_hit_ratio" in ratios:
            print(f"L1 I-Cache Hit Ratio:   {ratios['icache_hit_ratio']:.2f}%")
            print(
                f"L1 I-Cache Miss Ratio:  {ratios['icache_miss_ratio']:.2f}%"
            )
            print(
                f"L1 I-Cache Total Accesses: {int(ratios['icache_total_accesses'])}"
            )

        # D-Cache metrics
        if "dcache_hit_ratio" in ratios:
            print(f"L1 D-Cache Hit Ratio:   {ratios['dcache_hit_ratio']:.2f}%")
            print(
                f"L1 D-Cache Miss Ratio:  {ratios['dcache_miss_ratio']:.2f}%"
            )
            print(
                f"L1 D-Cache Total Accesses: {int(ratios['dcache_total_accesses'])}"
            )

        # Overall L1 metrics (if both caches have data)
        if "icache_hit_ratio" in ratios and "dcache_hit_ratio" in ratios:
            total_hits = 0
            total_accesses = 0

            for stat_name, stat_value in cache_stats.items():
                if "Hits" in stat_name and "total" in stat_name:
                    total_hits += stat_value
                elif ("Accesses" in stat_name and "total" in stat_name) or (
                    ("Hits" in stat_name or "Misses" in stat_name)
                    and "total" in stat_name
                ):
                    if "Accesses" in stat_name:
                        total_accesses += stat_value

            # If we don't have direct access counts, calculate from hits + misses
            if total_accesses == 0:
                total_misses = 0
                for stat_name, stat_value in cache_stats.items():
                    if "Hits" in stat_name and "total" in stat_name:
                        total_hits += stat_value
                    elif "Misses" in stat_name and "total" in stat_name:
                        total_misses += stat_value
                total_accesses = total_hits + total_misses

            if total_accesses > 0:
                overall_hit_ratio = (total_hits / total_accesses) * 100
                overall_miss_ratio = 100 - overall_hit_ratio
                print(f"\nOverall L1 Cache Performance:")
                print(f"Overall Hit Ratio:      {overall_hit_ratio:.2f}%")
                print(f"Overall Miss Ratio:     {overall_miss_ratio:.2f}%")
                print(f"Total Cache Accesses:   {int(total_accesses)}")
    else:
        print("\nCould not calculate hit/miss ratios - insufficient data")

else:
    print("No cache statistics found. Available stats:")
    if os.path.exists("m5out/stats.txt"):
        with open("m5out/stats.txt") as f:
            lines = f.readlines()[:50]  # Show first 50 lines
            for line in lines:
                if "cache" in line.lower():
                    print(line.strip())

print(f"\nTotal simulation ticks: {m5.curTick()}")
print("Full statistics available in: m5out/stats.txt")
