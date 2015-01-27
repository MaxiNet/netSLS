import random
import re

from mininet.topo import Topo as MiniNetTopology

class Topology(MiniNetTopology):
    """Basis for all topologies in the network simulator.

    The network simulator gets a list of racks and hosts when start_simulation()
    is called. The constructor establishes a topology with the corresponding
    ToR-switches and hosts.
    Every ToR-switch corresponds to one rack. The switch is labeled with the
    rack-id.
    Every Host is labeled with the corresponding hostname.
    Every Host is linked to the corresponding ToR-switch.
    """

    latency = 0.1

    edge_bandwidth_limit = 10

    def make_host_ip(self, rack, host):
        """Generates an IP address from rack number and host number.

        Args:
            rack: Rack number.
            host: Host number.
        Returns:
            A string representing an IP address of the following form:

            10.0.r.h

            where r is the rack number and h is the host number.
        """
        return "10.0.%i.%i" % (rack, host)

    def __init__(self, racks):
        """
        Args:
            racks: A list of racks with their corresponding hosts. For example:

                [
                {"id":"rack0", "hosts":["host00", "host01"]},
                {"id":"rack1", "hosts":["host10", "host11"]}
                ]
        """
        MiniNetTopology.__init__(self)

        self.host_ip_map = dict()

        self.tor_switches = list()

        # Set up racks (ToRs, Hosts and links)
        rack_count = 1
        for rack in racks:
            tor_switch = self.addSwitch(str(rack["id"]))
            self.tor_switches.append(tor_switch)

            host_count = 1
            for hostname in rack["hosts"]:
                host_ip = self.make_host_ip(rack_count, host_count)
                host = self.addHost(str(hostname), \
                        ip=host_ip)
                self.host_ip_map[host] = host_ip

                self.addLink(host, tor_switch, bw=Topology.edge_bandwidth_limit,
                        delay="%ims" % Topology.latency)

                host_count += 1

            rack_count += 1

class FatTree(Topology):
    """A fat tree topology.

    A simple fat tree topology with fanout of 2. The bandwidth limit is doubled
    with every layer of the tree.
    """
    def __init__(self, racks):
        Topology.__init__(self, racks)

        switch_count = 1
        bandwidth = Topology.edge_bandwidth_limit
        todo = self.tor_switches # nodes that have to be integrated into the tree
        while len(todo) > 1:
            new_todo = []
            for i in range(0, len(todo), 2):
                switch_id = switch_count * (256 * 256)
                sw = self.addSwitch('s' + str(switch_count))
                switch_count += 1
                new_todo.append(sw)

                self.addLink(todo[i], sw, bw=bandwidth, \
                        delay="%ims" % Topology.latency)
                if len(todo) > (i + 1):
                    self.addLink(todo[i + 1], sw, bandwidth=bandwidth, \
                            delay="%ims" % Topology.latency)

            todo = new_todo
            bandwidth = 2.0 * bandwidth
