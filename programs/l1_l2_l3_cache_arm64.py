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


class L2Cache(Cache):
    size = "256kB"
    assoc = 8
    tag_latency = 20
    data_latency = 20
    response_latency = 20
    mshrs = 20
    tgts_per_mshr = 12


class L3Cache(Cache):
    size = "1MB"
    assoc = 16
    tag_latency = 100
    data_latency = 100
    response_latency = 100
    mshrs = 30
    tgts_per_mshr = 12


# Create the system
system = System()

# Set up clock domain FIRST
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

# Set up memory
system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")]

# Create ARM64 CPU
system.cpu = ArmTimingSimpleCPU()

# Create L1 caches
system.cpu.icache = L1ICache()
system.cpu.dcache = L1DCache()

# Connect L1 caches to CPU
system.cpu.icache.cpu_side = system.cpu.icache_port
system.cpu.dcache.cpu_side = system.cpu.dcache_port

# Create L2 bus and cache
system.l2bus = L2XBar()
system.l2cache = L2Cache()

# Create L3 bus and cache
system.l3bus = L2XBar()
system.l3cache = L3Cache()

# Connect L1 caches to L2 bus
system.cpu.icache.mem_side = system.l2bus.cpu_side_ports
system.cpu.dcache.mem_side = system.l2bus.cpu_side_ports

# Connect L2 cache between L2 bus and L3 bus
system.l2cache.cpu_side = system.l2bus.mem_side_ports
system.l2cache.mem_side = system.l3bus.cpu_side_ports

# Connect L3 cache to L3 bus
system.l3cache.cpu_side = system.l3bus.mem_side_ports

# Create memory bus
system.membus = SystemXBar()

# Connect L3 cache to memory bus
system.l3cache.mem_side = system.membus.cpu_side_ports

# Create interrupt controller for ARM64
system.cpu.createInterruptController()

# Create memory controller
system.mem_ctrl = MemCtrl()
system.mem_ctrl.dram = DDR3_1600_8x8()
system.mem_ctrl.dram.range = system.mem_ranges[0]
system.mem_ctrl.port = system.membus.mem_side_ports

# System port for loading binaries
system.system_port = system.membus.cpu_side_ports

# Create the workload for ARM64
try:
    system.workload = SEWorkload.init_compatible(binary)
except:
    system.workload = SEWorkload()

# Create process for the ARM64 binary
process = Process()
process.cmd = [binary]
process.executable = binary

# Set up ARM64 process
system.cpu.workload = process
system.cpu.createThreads()

# Create root object
root = Root(full_system=False, system=system)

# Instantiate all objects
m5.instantiate()

print("Beginning simulation!")
print(f"Running ARM64 binary: {binary}")
print("Configuration: L1 + L2 + L3 CACHE")

# Start simulation
exit_event = m5.simulate()

print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}")

# Dump statistics to default location
m5.stats.dump()


# Enhanced function to extract cache stats for L1 + L2 + L3
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

                        # Look for cache-related statistics (L1, L2, and L3)
                        if (
                            "system.cpu.icache" in stat_name
                            or "system.cpu.dcache" in stat_name
                            or "system.l2cache" in stat_name
                            or "system.l3cache" in stat_name
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


# Robust function to calculate hit and miss ratios - handles all edge cases
def calculate_cache_ratios(cache_stats):
    ratios = {}

    # Define patterns to look for hits, misses, and accesses
    cache_types = ["icache", "dcache", "l2cache", "l3cache"]

    for cache_type in cache_types:
        hits = None
        misses = None
        accesses = None

        # Find hits, misses, and accesses for this cache type
        for stat_name, stat_value in cache_stats.items():
            if cache_type in stat_name and "total" in stat_name:
                if "Hits" in stat_name:
                    hits = stat_value
                elif "Misses" in stat_name:
                    misses = stat_value
                elif "Accesses" in stat_name:
                    accesses = stat_value

        # Calculate ratios with robust error handling
        try:
            total_accesses = None
            calculated_hits = None

            # Determine total accesses
            if accesses is not None:
                total_accesses = accesses
            elif hits is not None and misses is not None:
                total_accesses = hits + misses
            elif misses is not None and accesses is None:
                # Only misses available, assume accesses = misses (100% miss rate)
                total_accesses = misses

            # Determine hits
            if hits is not None:
                calculated_hits = hits
            elif total_accesses is not None and misses is not None:
                calculated_hits = total_accesses - misses
                # Ensure hits is not negative
                calculated_hits = max(0, calculated_hits)
            else:
                calculated_hits = 0

            # Calculate ratios if we have valid data
            if (
                total_accesses is not None
                and total_accesses > 0
                and misses is not None
            ):
                hit_ratio = (calculated_hits / total_accesses) * 100
                miss_ratio = (misses / total_accesses) * 100

                ratios[f"{cache_type}_hit_ratio"] = hit_ratio
                ratios[f"{cache_type}_miss_ratio"] = miss_ratio
                ratios[f"{cache_type}_total_accesses"] = total_accesses
                ratios[f"{cache_type}_hits"] = calculated_hits
                ratios[f"{cache_type}_misses"] = misses

        except Exception as e:
            print(f"Error calculating ratios for {cache_type}: {e}")
            continue

    return ratios


# Extract and print cache statistics with ratios
print("\n=== ARM64 L1 + L2 + L3 CACHE STATISTICS FROM stats.txt ===")
cache_stats = extract_cache_stats_with_ratios()

if cache_stats:
    print("Raw Cache Statistics:")
    print("-" * 70)
    for stat_name, stat_value in sorted(cache_stats.items()):
        print(f"{stat_name}: {stat_value}")

    # Calculate and display ratios
    try:
        ratios = calculate_cache_ratios(cache_stats)

        if ratios:
            print("\nCalculated Cache Performance Metrics:")
            print("-" * 70)

            # L1 I-Cache metrics
            if "icache_hit_ratio" in ratios:
                print(
                    f"L1 I-Cache Hit Ratio:     {ratios['icache_hit_ratio']:.2f}%"
                )
                print(
                    f"L1 I-Cache Miss Ratio:    {ratios['icache_miss_ratio']:.2f}%"
                )
                print(
                    f"L1 I-Cache Hits:          {int(ratios['icache_hits'])}"
                )
                print(
                    f"L1 I-Cache Misses:        {int(ratios['icache_misses'])}"
                )
                print(
                    f"L1 I-Cache Total Accesses: {int(ratios['icache_total_accesses'])}"
                )
                print()

            # L1 D-Cache metrics
            if "dcache_hit_ratio" in ratios:
                print(
                    f"L1 D-Cache Hit Ratio:     {ratios['dcache_hit_ratio']:.2f}%"
                )
                print(
                    f"L1 D-Cache Miss Ratio:    {ratios['dcache_miss_ratio']:.2f}%"
                )
                print(
                    f"L1 D-Cache Hits:          {int(ratios['dcache_hits'])}"
                )
                print(
                    f"L1 D-Cache Misses:        {int(ratios['dcache_misses'])}"
                )
                print(
                    f"L1 D-Cache Total Accesses: {int(ratios['dcache_total_accesses'])}"
                )
                print()

            # L2 Cache metrics
            if "l2cache_hit_ratio" in ratios:
                print(
                    f"L2 Cache Hit Ratio:       {ratios['l2cache_hit_ratio']:.2f}%"
                )
                print(
                    f"L2 Cache Miss Ratio:      {ratios['l2cache_miss_ratio']:.2f}%"
                )
                print(
                    f"L2 Cache Hits:            {int(ratios['l2cache_hits'])}"
                )
                print(
                    f"L2 Cache Misses:          {int(ratios['l2cache_misses'])}"
                )
                print(
                    f"L2 Cache Total Accesses:  {int(ratios['l2cache_total_accesses'])}"
                )
                print()

            # L3 Cache metrics
            if "l3cache_hit_ratio" in ratios:
                print(
                    f"L3 Cache Hit Ratio:       {ratios['l3cache_hit_ratio']:.2f}%"
                )
                print(
                    f"L3 Cache Miss Ratio:      {ratios['l3cache_miss_ratio']:.2f}%"
                )
                print(
                    f"L3 Cache Hits:            {int(ratios['l3cache_hits'])}"
                )
                print(
                    f"L3 Cache Misses:          {int(ratios['l3cache_misses'])}"
                )
                print(
                    f"L3 Cache Total Accesses:  {int(ratios['l3cache_total_accesses'])}"
                )
                print()
        else:
            print("\nCould not calculate hit/miss ratios - insufficient data")

    except Exception as e:
        print(f"\nError in ratio calculations: {e}")
        print(
            "Raw statistics were successfully extracted but ratio calculation failed."
        )

else:
    print("No cache statistics found.")

print(f"\nTotal simulation ticks: {m5.curTick()}")
print("Full statistics available in: m5out/stats.txt")
