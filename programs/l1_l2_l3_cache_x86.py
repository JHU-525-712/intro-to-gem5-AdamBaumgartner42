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

# Set up clock domain
system.clk_domain = SrcClockDomain()
system.clk_domain.clock = "1GHz"
system.clk_domain.voltage_domain = VoltageDomain()

# Set up memory - x86 typically uses larger memory ranges
system.mem_mode = "timing"
system.mem_ranges = [AddrRange("512MB")]

# Create x86 CPU
system.cpu = X86TimingSimpleCPU()

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
    system.workload = SEWorkload.init_compatible(binary)
except:
    system.workload = SEWorkload()

# Create process for the x86 binary
process = Process()
process.cmd = [binary]

# x86-specific process configuration
process.executable = binary

# Set up x86 process
system.cpu.workload = process
system.cpu.createThreads()

# Create root object
root = Root(full_system=False, system=system)

# Instantiate all objects
m5.instantiate()

print("Beginning simulation!")
print(f"Running x86 binary: {binary}")
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
print("\n=== x86 L1 + L2 + L3 CACHE STATISTICS FROM stats.txt ===")
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

            # Enhanced Overall Cache System Performance Analysis
            print("Comprehensive x86 Cache System Performance Analysis:")
            print("=" * 60)

            # Calculate performance metrics for each level
            l1_total_hits = 0
            l1_total_accesses = 0
            l2_total_hits = 0
            l2_total_accesses = 0
            l3_total_hits = 0
            l3_total_accesses = 0

            # Gather L1 totals
            if "icache_hits" in ratios and "dcache_hits" in ratios:
                l1_total_hits = ratios["icache_hits"] + ratios["dcache_hits"]
                l1_total_accesses = (
                    ratios["icache_total_accesses"]
                    + ratios["dcache_total_accesses"]
                )

            # Gather L2 totals
            if "l2cache_hits" in ratios:
                l2_total_hits = ratios["l2cache_hits"]
                l2_total_accesses = ratios["l2cache_total_accesses"]

            # Gather L3 totals
            if "l3cache_hits" in ratios:
                l3_total_hits = ratios["l3cache_hits"]
                l3_total_accesses = ratios["l3cache_total_accesses"]

            # Overall system metrics
            if l1_total_accesses > 0:
                l1_overall_hit_ratio = (
                    l1_total_hits / l1_total_accesses
                ) * 100
                l1_overall_miss_ratio = 100 - l1_overall_hit_ratio

                print(f"L1 Cache Level Performance:")
                print(
                    f"  Overall L1 Hit Ratio:     {l1_overall_hit_ratio:.2f}%"
                )
                print(
                    f"  Overall L1 Miss Ratio:    {l1_overall_miss_ratio:.2f}%"
                )
                print(f"  Total L1 Accesses:       {int(l1_total_accesses)}")
                print(f"  Total L1 Hits:           {int(l1_total_hits)}")
                print(
                    f"  Total L1 Misses:         {int(l1_total_accesses - l1_total_hits)}"
                )
                print()

            if l2_total_accesses > 0:
                l2_hit_ratio = (l2_total_hits / l2_total_accesses) * 100
                l2_miss_ratio = 100 - l2_hit_ratio

                print(f"L2 Cache Level Performance:")
                print(f"  L2 Hit Ratio:             {l2_hit_ratio:.2f}%")
                print(f"  L2 Miss Ratio:            {l2_miss_ratio:.2f}%")
                print(f"  Total L2 Accesses:       {int(l2_total_accesses)}")
                print(f"  Total L2 Hits:           {int(l2_total_hits)}")
                print(
                    f"  Total L2 Misses:         {int(l2_total_accesses - l2_total_hits)}"
                )
                print()

            if l3_total_accesses > 0:
                l3_hit_ratio = (l3_total_hits / l3_total_accesses) * 100
                l3_miss_ratio = 100 - l3_hit_ratio

                print(f"L3 Cache Level Performance:")
                print(f"  L3 Hit Ratio:             {l3_hit_ratio:.2f}%")
                print(f"  L3 Miss Ratio:            {l3_miss_ratio:.2f}%")
                print(f"  Total L3 Accesses:       {int(l3_total_accesses)}")
                print(f"  Total L3 Hits:           {int(l3_total_hits)}")
                print(
                    f"  Total L3 Misses:         {int(l3_total_accesses - l3_total_hits)}"
                )
                print()

            # Multi-Level Cache Efficiency Analysis
            print("Multi-Level Cache Efficiency Analysis:")
            print("-" * 50)

            if l1_total_accesses > 0:
                # L1 efficiency (how much L1 reduces traffic to L2)
                if l2_total_accesses > 0:
                    l1_efficiency = (
                        (l1_total_accesses - l2_total_accesses)
                        / l1_total_accesses
                    ) * 100
                    l1_traffic_reduction = (
                        l1_total_accesses - l2_total_accesses
                    )
                    print(f"L1 Cache Efficiency:      {l1_efficiency:.2f}%")
                    print(
                        f"L1 Traffic Reduction:     {int(l1_traffic_reduction)} requests"
                    )
                    print(
                        f"L1 → L2 Traffic:          {int(l2_total_accesses)} requests"
                    )
                    print()

                # L2 efficiency (how much L2 reduces traffic to L3)
                if l2_total_accesses > 0 and l3_total_accesses > 0:
                    l2_efficiency = (
                        (l2_total_accesses - l3_total_accesses)
                        / l2_total_accesses
                    ) * 100
                    l2_traffic_reduction = (
                        l2_total_accesses - l3_total_accesses
                    )
                    print(f"L2 Cache Efficiency:      {l2_efficiency:.2f}%")
                    print(
                        f"L2 Traffic Reduction:     {int(l2_traffic_reduction)} requests"
                    )
                    print(
                        f"L2 → L3 Traffic:          {int(l3_total_accesses)} requests"
                    )
                    print()
                elif l2_total_accesses > 0:
                    print(f"L2 Cache Efficiency:      100.00% (no L3 traffic)")
                    print(
                        f"L2 Traffic Reduction:     {int(l2_total_accesses)} requests"
                    )
                    print(
                        f"L2 → Memory Traffic:      {int(l2_total_accesses - l2_total_hits)} requests"
                    )
                    print()

                # L3 efficiency (how much L3 reduces traffic to memory)
                if l3_total_accesses > 0:
                    memory_accesses = l3_total_accesses - l3_total_hits
                    l3_efficiency = (
                        (l3_total_hits / l3_total_accesses) * 100
                        if l3_total_accesses > 0
                        else 0
                    )
                    print(f"L3 Cache Efficiency:      {l3_efficiency:.2f}%")
                    print(
                        f"L3 Traffic Reduction:     {int(l3_total_hits)} requests"
                    )
                    print(
                        f"L3 → Memory Traffic:      {int(memory_accesses)} requests"
                    )
                    print()

                # Overall system efficiency
                if l3_total_accesses > 0:
                    memory_requests = l3_total_accesses - l3_total_hits
                    overall_efficiency = (
                        (l1_total_accesses - memory_requests)
                        / l1_total_accesses
                    ) * 100
                elif l2_total_accesses > 0:
                    memory_requests = l2_total_accesses - l2_total_hits
                    overall_efficiency = (
                        (l1_total_accesses - memory_requests)
                        / l1_total_accesses
                    ) * 100
                else:
                    memory_requests = l1_total_accesses - l1_total_hits
                    overall_efficiency = (
                        l1_total_hits / l1_total_accesses
                    ) * 100

                print(f"Overall x86 System Performance:")
                print(f"  Total CPU Requests:       {int(l1_total_accesses)}")
                print(f"  Final Memory Requests:    {int(memory_requests)}")
                print(f"  Overall Cache Efficiency: {overall_efficiency:.2f}%")
                print(f"  Memory Traffic Reduction: {overall_efficiency:.1f}x")
                print()

            # Cache Hierarchy Flow Analysis
            print("x86 Cache Hierarchy Request Flow:")
            print("-" * 40)

            if l1_total_accesses > 0:
                print(
                    f"CPU → L1:     {int(l1_total_accesses):>8} requests (100.0%)"
                )

                if l2_total_accesses > 0:
                    l1_miss_percent = (
                        l2_total_accesses / l1_total_accesses
                    ) * 100
                    print(
                        f"L1 → L2:      {int(l2_total_accesses):>8} requests ({l1_miss_percent:.1f}%)"
                    )

                    if l3_total_accesses > 0:
                        l2_miss_percent = (
                            l3_total_accesses / l1_total_accesses
                        ) * 100
                        print(
                            f"L2 → L3:      {int(l3_total_accesses):>8} requests ({l2_miss_percent:.1f}%)"
                        )

                        memory_requests = l3_total_accesses - l3_total_hits
                        memory_percent = (
                            memory_requests / l1_total_accesses
                        ) * 100
                        print(
                            f"L3 → Memory:  {int(memory_requests):>8} requests ({memory_percent:.1f}%)"
                        )
                    else:
                        memory_requests = l2_total_accesses - l2_total_hits
                        memory_percent = (
                            memory_requests / l1_total_accesses
                        ) * 100
                        print(
                            f"L2 → Memory:  {int(memory_requests):>8} requests ({memory_percent:.1f}%)"
                        )
                else:
                    memory_requests = l1_total_accesses - l1_total_hits
                    memory_percent = (
                        memory_requests / l1_total_accesses
                    ) * 100
                    print(
                        f"L1 → Memory:  {int(memory_requests):>8} requests ({memory_percent:.1f}%)"
                    )
                print()

            # Performance Impact Analysis
            print("x86 Performance Impact Analysis:")
            print("-" * 35)

            # Calculate average memory access time (assuming typical x86 latencies)
            l1_latency = 1  # cycles
            l2_latency = 12  # cycles (x86 L2 typically higher latency)
            l3_latency = 35  # cycles (x86 L3 typically higher latency)
            memory_latency = 120  # cycles (x86 memory access typically higher)

            if l1_total_accesses > 0:
                # Calculate weighted average access time
                avg_access_time = 0

                # L1 hits
                l1_hit_contribution = (
                    l1_total_hits / l1_total_accesses
                ) * l1_latency
                avg_access_time += l1_hit_contribution

                if l2_total_accesses > 0:
                    # L2 hits (L1 miss + L2 hit)
                    l2_hit_contribution = (
                        l2_total_hits / l1_total_accesses
                    ) * (l1_latency + l2_latency)
                    avg_access_time += l2_hit_contribution

                    if l3_total_accesses > 0:
                        # L3 hits (L1 miss + L2 miss + L3 hit)
                        l3_hit_contribution = (
                            l3_total_hits / l1_total_accesses
                        ) * (l1_latency + l2_latency + l3_latency)
                        avg_access_time += l3_hit_contribution

                        # Memory accesses (L1 + L2 + L3 miss)
                        memory_requests = l3_total_accesses - l3_total_hits
                        memory_contribution = (
                            memory_requests / l1_total_accesses
                        ) * (
                            l1_latency
                            + l2_latency
                            + l3_latency
                            + memory_latency
                        )
                        avg_access_time += memory_contribution
                    else:
                        # Memory accesses (L1 + L2 miss)
                        memory_requests = l2_total_accesses - l2_total_hits
                        memory_contribution = (
                            memory_requests / l1_total_accesses
                        ) * (l1_latency + l2_latency + memory_latency)
                        avg_access_time += memory_contribution
                else:
                    # Memory accesses (L1 miss only)
                    memory_requests = l1_total_accesses - l1_total_hits
                    memory_contribution = (
                        memory_requests / l1_total_accesses
                    ) * (l1_latency + memory_latency)
                    avg_access_time += memory_contribution

                # Compare with no-cache scenario
                no_cache_time = memory_latency
                speedup = (
                    no_cache_time / avg_access_time
                    if avg_access_time > 0
                    else 1
                )

                print(
                    f"Average Memory Access Time: {avg_access_time:.2f} cycles"
                )
                print(f"No-Cache Access Time:       {no_cache_time} cycles")
                print(f"x86 Cache System Speedup:   {speedup:.2f}x")

                # Break down contributions
                print(f"\nAccess Time Breakdown:")
                print(
                    f"  L1 Hit Contribution:      {l1_hit_contribution:.2f} cycles ({(l1_hit_contribution/avg_access_time)*100:.1f}%)"
                )
                if l2_total_accesses > 0:
                    print(
                        f"  L2 Hit Contribution:      {l2_hit_contribution:.2f} cycles ({(l2_hit_contribution/avg_access_time)*100:.1f}%)"
                    )
                if l3_total_accesses > 0:
                    print(
                        f"  L3 Hit Contribution:      {l3_hit_contribution:.2f} cycles ({(l3_hit_contribution/avg_access_time)*100:.1f}%)"
                    )
                print(
                    f"  Memory Access Contribution: {memory_contribution:.2f} cycles ({(memory_contribution/avg_access_time)*100:.1f}%)"
                )

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
