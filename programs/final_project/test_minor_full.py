from m5.objects import (
    System, SrcClockDomain, VoltageDomain,
    MinorCPU, AddrRange
)

# -------------------------
# Build system
# -------------------------
system = System(
    clk_domain = SrcClockDomain(
        clock="1GHz",
        voltage_domain=VoltageDomain()
    ),
    mem_mode = 'timing',
    mem_ranges = [AddrRange('128MB')]
)

# Create two MinorCPUs and attach them to the system
system.cpu = [
    MinorCPU(cpu_id=0),
    MinorCPU(cpu_id=1)
]

print("\n=== MinorCPU Presence Test ===")
print(f"System has {len(system.cpu)} CPU objects\n")

for i, cpu in enumerate(system.cpu):
    print(f"CPU index {i}:")
    print("  isinstance MinorCPU:", isinstance(cpu, MinorCPU))
    print("  Python class name  :", cpu.__class__.__name__)
    print("  cpu_id param       :", cpu.cpu_id)
    print("  clk_domain         :", cpu.clk_domain)
    print()

print("MinorCPU objects constructed and attached to System successfully.")
