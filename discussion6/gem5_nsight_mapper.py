#!/usr/bin/env python3
"""
gem5 to Nsight Compute Statistics Mapper
Reads gem5 stats.txt and maps to equivalent NVIDIA Nsight Compute metrics
"""

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


class Gem5StatsParser:
    def __init__(self, stats_file_path):
        self.stats_file = stats_file_path
        self.stats = {}
        self.nsight_mapping = {}

    def parse_stats_file(self):
        """Parse gem5 stats.txt file"""
        try:
            with open(self.stats_file) as f:
                content = f.read()
        except FileNotFoundError:
            print(f"Error: Stats file not found at {self.stats_file}")
            return False
        except Exception as e:
            print(f"Error reading stats file: {e}")
            return False

        # Parse stats using regex patterns
        # Pattern for: stat_name value # description
        pattern = r"^([a-zA-Z0-9_.]+)\s+([0-9.e+-]+)(?:\s+#\s*(.*))?$"

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("---") or line.startswith("Begin"):
                continue

            match = re.match(pattern, line)
            if match:
                stat_name = match.group(1)
                stat_value = match.group(2)
                description = match.group(3) if match.group(3) else ""

                # Convert to appropriate numeric type
                try:
                    if "." in stat_value or "e" in stat_value.lower():
                        stat_value = float(stat_value)
                    else:
                        stat_value = int(stat_value)
                except ValueError:
                    pass  # Keep as string if conversion fails

                self.stats[stat_name] = {
                    "value": stat_value,
                    "description": description,
                }

        print(f"Parsed {len(self.stats)} statistics from gem5")
        return True

    def map_to_nsight_metrics(self):
        """Map gem5 stats to Nsight Compute equivalent metrics"""

        # Initialize mapping structure
        self.nsight_mapping = {
            "Memory": {},
            "Compute": {},
            "Cache": {},
            "Instruction": {},
            "Timing": {},
            "Bandwidth": {},
            "Utilization": {},
        }

        # Memory-related mappings
        self._map_memory_stats()

        # Compute-related mappings
        self._map_compute_stats()

        # Cache-related mappings
        self._map_cache_stats()

        # Instruction-related mappings
        self._map_instruction_stats()

        # Timing-related mappings
        self._map_timing_stats()

        # Bandwidth calculations
        self._calculate_bandwidth_stats()

        # Utilization calculations
        self._calculate_utilization_stats()

    def _map_memory_stats(self):
        """Map memory-related statistics"""
        memory_stats = {}

        # Global memory access patterns
        for stat_name, stat_data in self.stats.items():
            if "mem" in stat_name.lower() and "read" in stat_name.lower():
                memory_stats["Global Memory Read Requests"] = stat_data[
                    "value"
                ]
            elif "mem" in stat_name.lower() and "write" in stat_name.lower():
                memory_stats["Global Memory Write Requests"] = stat_data[
                    "value"
                ]
            elif "bytes_read" in stat_name.lower():
                memory_stats["Global Memory Read Bytes"] = stat_data["value"]
            elif "bytes_written" in stat_name.lower():
                memory_stats["Global Memory Write Bytes"] = stat_data["value"]

        # Look for DRAM/memory controller stats
        for stat_name, stat_data in self.stats.items():
            if (
                "dram" in stat_name.lower()
                or "memory_ctrl" in stat_name.lower()
            ):
                if "read" in stat_name.lower():
                    memory_stats["DRAM Read Transactions"] = stat_data["value"]
                elif "write" in stat_name.lower():
                    memory_stats["DRAM Write Transactions"] = stat_data[
                        "value"
                    ]

        self.nsight_mapping["Memory"] = memory_stats

    def _map_compute_stats(self):
        """Map compute-related statistics"""
        compute_stats = {}

        # Look for GPU/compute unit related stats
        for stat_name, stat_data in self.stats.items():
            if (
                "gpu" in stat_name.lower()
                or "compute_unit" in stat_name.lower()
            ):
                if "cycles" in stat_name.lower():
                    compute_stats["SM Active Cycles"] = stat_data["value"]
                elif (
                    "insts" in stat_name.lower()
                    or "instructions" in stat_name.lower()
                ):
                    compute_stats["Instructions Executed"] = stat_data["value"]
                elif (
                    "warps" in stat_name.lower()
                    or "wavefronts" in stat_name.lower()
                ):
                    compute_stats["Warps Launched"] = stat_data["value"]

        # Look for ALU/execution unit stats
        for stat_name, stat_data in self.stats.items():
            if "alu" in stat_name.lower() or "exec" in stat_name.lower():
                compute_stats["ALU Utilization"] = stat_data["value"]

        self.nsight_mapping["Compute"] = compute_stats

    def _map_cache_stats(self):
        """Map cache-related statistics"""
        cache_stats = {}

        # L1 Cache stats
        l1_hits = 0
        l1_misses = 0
        l1_accesses = 0

        # L2 Cache stats
        l2_hits = 0
        l2_misses = 0
        l2_accesses = 0

        for stat_name, stat_data in self.stats.items():
            # L1 Cache
            if "l1" in stat_name.lower() or "dcache" in stat_name.lower():
                if "hits" in stat_name.lower():
                    l1_hits += stat_data["value"]
                elif "misses" in stat_name.lower():
                    l1_misses += stat_data["value"]
                elif "accesses" in stat_name.lower():
                    l1_accesses += stat_data["value"]

            # L2 Cache
            elif "l2" in stat_name.lower():
                if "hits" in stat_name.lower():
                    l2_hits += stat_data["value"]
                elif "misses" in stat_name.lower():
                    l2_misses += stat_data["value"]
                elif "accesses" in stat_name.lower():
                    l2_accesses += stat_data["value"]

        # Calculate hit rates
        if l1_accesses > 0:
            cache_stats["L1 Cache Hit Rate"] = l1_hits / l1_accesses
        if l2_accesses > 0:
            cache_stats["L2 Cache Hit Rate"] = l2_hits / l2_accesses

        cache_stats["L1 Cache Hits"] = l1_hits
        cache_stats["L1 Cache Misses"] = l1_misses
        cache_stats["L2 Cache Hits"] = l2_hits
        cache_stats["L2 Cache Misses"] = l2_misses

        self.nsight_mapping["Cache"] = cache_stats

    def _map_instruction_stats(self):
        """Map instruction-related statistics"""
        instruction_stats = {}

        for stat_name, stat_data in self.stats.items():
            if "inst" in stat_name.lower() or "instr" in stat_name.lower():
                if (
                    "committed" in stat_name.lower()
                    or "executed" in stat_name.lower()
                ):
                    instruction_stats["Instructions Per Clock"] = stat_data[
                        "value"
                    ]
                elif "fetch" in stat_name.lower():
                    instruction_stats["Instructions Fetched"] = stat_data[
                        "value"
                    ]

        self.nsight_mapping["Instruction"] = instruction_stats

    def _map_timing_stats(self):
        """Map timing-related statistics"""
        timing_stats = {}

        # Look for simulation time and cycles
        for stat_name, stat_data in self.stats.items():
            if "sim_seconds" in stat_name.lower():
                timing_stats["Simulation Time (seconds)"] = stat_data["value"]
            elif "sim_ticks" in stat_name.lower():
                timing_stats["Simulation Ticks"] = stat_data["value"]
            elif "final_tick" in stat_name.lower():
                timing_stats["Final Tick"] = stat_data["value"]
            elif "kernel_time" in stat_name.lower():
                timing_stats["Kernel Execution Time"] = stat_data["value"]

        self.nsight_mapping["Timing"] = timing_stats

    def _calculate_bandwidth_stats(self):
        """Calculate bandwidth-related metrics"""
        bandwidth_stats = {}

        # Get memory bytes and timing info
        total_bytes_read = 0
        total_bytes_written = 0
        sim_time = 0

        for stat_name, stat_data in self.stats.items():
            if "bytes_read" in stat_name.lower():
                total_bytes_read += stat_data["value"]
            elif "bytes_written" in stat_name.lower():
                total_bytes_written += stat_data["value"]
            elif "sim_seconds" in stat_name.lower():
                sim_time = stat_data["value"]

        # Calculate bandwidth (GB/s)
        if sim_time > 0:
            read_bandwidth = (total_bytes_read / sim_time) / (
                1024**3
            )  # GB/s
            write_bandwidth = (total_bytes_written / sim_time) / (
                1024**3
            )  # GB/s
            total_bandwidth = read_bandwidth + write_bandwidth

            bandwidth_stats["Memory Read Bandwidth (GB/s)"] = read_bandwidth
            bandwidth_stats["Memory Write Bandwidth (GB/s)"] = write_bandwidth
            bandwidth_stats["Total Memory Bandwidth (GB/s)"] = total_bandwidth

        self.nsight_mapping["Bandwidth"] = bandwidth_stats

    def _calculate_utilization_stats(self):
        """Calculate utilization metrics"""
        utilization_stats = {}

        # Look for busy/idle cycles
        for stat_name, stat_data in self.stats.items():
            if "busy_cycles" in stat_name.lower():
                utilization_stats["Compute Unit Busy Cycles"] = stat_data[
                    "value"
                ]
            elif "idle_cycles" in stat_name.lower():
                utilization_stats["Compute Unit Idle Cycles"] = stat_data[
                    "value"
                ]

        self.nsight_mapping["Utilization"] = utilization_stats

    def print_comparison_report(self):
        """Print a formatted comparison report"""
        print("\n" + "=" * 80)
        print("GEM5 TO NSIGHT COMPUTE STATISTICS MAPPING")
        print("=" * 80)

        for category, metrics in self.nsight_mapping.items():
            if metrics:  # Only print categories with data
                print(f"\n📊 {category.upper()} METRICS:")
                print("-" * 40)

                for metric_name, value in metrics.items():
                    if isinstance(value, float):
                        if value < 1:
                            print(f"  {metric_name:<35}: {value:.6f}")
                        else:
                            print(f"  {metric_name:<35}: {value:.2f}")
                    else:
                        print(f"  {metric_name:<35}: {value:,}")

        print("\n" + "=" * 80)
        print("SUMMARY STATISTICS")
        print("=" * 80)

        # Print key performance indicators
        memory_metrics = self.nsight_mapping.get("Memory", {})
        cache_metrics = self.nsight_mapping.get("Cache", {})
        bandwidth_metrics = self.nsight_mapping.get("Bandwidth", {})

        if "L1 Cache Hit Rate" in cache_metrics:
            print(
                f"L1 Cache Hit Rate: {cache_metrics['L1 Cache Hit Rate']:.2%}"
            )
        if "L2 Cache Hit Rate" in cache_metrics:
            print(
                f"L2 Cache Hit Rate: {cache_metrics['L2 Cache Hit Rate']:.2%}"
            )
        if "Total Memory Bandwidth (GB/s)" in bandwidth_metrics:
            print(
                f"Memory Bandwidth: {bandwidth_metrics['Total Memory Bandwidth (GB/s)']:.2f} GB/s"
            )

    def save_to_json(self, output_file):
        """Save the mapping to a JSON file"""
        try:
            with open(output_file, "w") as f:
                json.dump(self.nsight_mapping, f, indent=2, default=str)
            print(f"\n💾 Results saved to: {output_file}")
        except Exception as e:
            print(f"Error saving to JSON: {e}")

    def save_to_csv(self, output_file):
        """Save the mapping to a CSV file"""
        try:
            import csv

            with open(output_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Category", "Metric", "Value"])

                for category, metrics in self.nsight_mapping.items():
                    for metric_name, value in metrics.items():
                        writer.writerow([category, metric_name, value])

            print(f"💾 Results saved to: {output_file}")
        except Exception as e:
            print(f"Error saving to CSV: {e}")


def main():
    # Default path
    default_stats_path = "/workspaces/gem5bootcamp2024/m5out/stats.txt"

    # Check if custom path provided
    if len(sys.argv) > 1:
        stats_path = sys.argv[1]
    else:
        stats_path = default_stats_path

    print(f"🔍 Looking for gem5 stats at: {stats_path}")

    # Check if file exists
    if not os.path.exists(stats_path):
        print(f"❌ Stats file not found at: {stats_path}")
        print(
            "Please ensure the gem5 simulation has completed and stats.txt exists."
        )
        sys.exit(1)

    # Create parser and process stats
    parser = Gem5StatsParser(stats_path)

    print("📖 Parsing gem5 statistics...")
    if not parser.parse_stats_file():
        sys.exit(1)

    print("🔄 Mapping to Nsight Compute equivalent metrics...")
    parser.map_to_nsight_metrics()

    # Print report
    parser.print_comparison_report()

    # Save outputs
    output_dir = os.path.dirname(stats_path)
    json_output = os.path.join(output_dir, "nsight_comparison.json")
    csv_output = os.path.join(output_dir, "nsight_comparison.csv")

    parser.save_to_json(json_output)
    parser.save_to_csv(csv_output)

    print(f"\n✅ Analysis complete!")
    print(f"📁 Output files created in: {output_dir}")


if __name__ == "__main__":
    main()
