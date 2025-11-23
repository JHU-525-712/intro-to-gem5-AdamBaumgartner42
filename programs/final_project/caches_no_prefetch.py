from m5.objects import Cache

class L1ICache(Cache):
    def __init__(self, size="32kB", assoc=2):
        super().__init__()
        self.size = size
        self.assoc = assoc
        self.tag_latency = 1
        self.data_latency = 1
        self.response_latency = 1
        self.mshrs = 4
        self.tgts_per_mshr = 20

    def connectCPU(self, cpu):
        self.cpu_side = cpu.icache_port

    def connectBus(self, bus):
        self.mem_side = bus.cpu_side_ports


class L1DCache(Cache):
    def __init__(self, size="32kB", assoc=2):
        super().__init__()
        self.size = size
        self.assoc = assoc
        self.tag_latency = 1
        self.data_latency = 1
        self.response_latency = 1
        self.mshrs = 4
        self.tgts_per_mshr = 20
        self.writeback_clean = True

    def connectCPU(self, cpu):
        self.cpu_side = cpu.dcache_port

    def connectBus(self, bus):
        self.mem_side = bus.cpu_side_ports


class L2Cache(Cache):
    def __init__(self, size="256kB", assoc=8):
        super().__init__()
        self.size = size
        self.assoc = assoc
        self.tag_latency = 10
        self.data_latency = 10
        self.response_latency = 10
        self.mshrs = 8
        self.tgts_per_mshr = 12

    def connectCPUSideBus(self, bus):
        self.cpu_side = bus.mem_side_ports

    def connectMemSideBus(self, bus):
        self.mem_side = bus.cpu_side_ports
