from m5.objects import System, SrcClockDomain, VoltageDomain, MinorCPU

system = System(
    clk_domain = SrcClockDomain(clock="1GHz",
                                voltage_domain=VoltageDomain()),
    mem_mode = 'timing',
    mem_ranges = []
)

system.cpu = MinorCPU()

print("MinorCPU constructed successfully!")
