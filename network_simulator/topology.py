"""
Copyright 2015 Malte Splietker, Philip Wette

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
import math

from mininet.topo import Topo as MiniNetTopology

logger = logging.getLogger(__name__)

class Topology(MiniNetTopology):
    """Basis for all topologies in the network simulator.

    The network simulator gets a list of racks and hosts when start_simulation()
    is called. The constructor establishes a topology with the corresponding
    ToR-switches and hosts.
    Every ToR-switch corresponds to one rack. The switch is labeled with the
    rack-id.
    Every Host is labeled with the corresponding hostname.
    Every Host is linked to the corresponding ToR-switch.

    Attributes:
        __mn_hostname_to_ip_map: Map MaxiNet hostname to its IP address
        __hostname_to_mn_hostname_map: Map hostname to MaxiNet hostname
    """

    latency = 0.05

    edge_bandwidth_limit = 10

    qsize = 75

    dpid = 0

    @classmethod
    def make_dpid(cls):
        Topology.dpid += 1
        return "%x" % Topology.dpid

    @classmethod
    def make_host_ip(cls, rack, host):
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

        self.__mn_hostname_to_ip_map = dict()
        self.__hostname_to_mn_hostname_map = dict()

        self.tor_switches = list()

        # Set up racks (ToRs, Hosts and links)
        rack_count = 1
        for rack in racks:
            tor_switch = self.addSwitch(
                "tor%i" % rack_count,
                dpid=Topology.make_dpid())
            self.tor_switches.append(tor_switch)

            host_count = 1
            for hostname in rack["hosts"]:
                host_ip = self.make_host_ip(rack_count, host_count)
                mn_hostname = self.addHost(
                    "h%02i%02i" % (rack_count, host_count),
                    ip=host_ip)
                self.__mn_hostname_to_ip_map[mn_hostname] = host_ip
                self.__hostname_to_mn_hostname_map[hostname] = mn_hostname

                self.addLink(
                    mn_hostname,
                    tor_switch,
                    bw=Topology.edge_bandwidth_limit,
                    delay=str(Topology.latency) + "ms",
                    use_tbf=False,
                    enable_red=False,
                    max_queue_size=Topology.qsize)

                host_count += 1

            rack_count += 1

    def get_mn_hostname(self, hostname):
        """Returns MaxiNet hostname corresponding to hostname."""
        if not hostname in self.__hostname_to_mn_hostname_map:
            logger.error("Unkown hostname {}".format(hostname))
        return self.__hostname_to_mn_hostname_map[hostname]

    def get_ip_address(self, mn_hostname):
        """Get IP address corresponding to MaxiNet hostname"""
        if not mn_hostname in self.__mn_hostname_to_ip_map:
            logger.error("Unkown MaxiNet hostname {}".format(mn_hostname))
        return self.__mn_hostname_to_ip_map[mn_hostname]


class FatTree(Topology):
    """A fat tree topology.

    A simple fat tree topology with fanout of 2. The bandwidth limit is doubled
    with every layer of the tree.
    """
    def __init__(self, racks):
        Topology.__init__(self, racks)

        switch_count = 1
        bandwidth = Topology.edge_bandwidth_limit
        todo = self.tor_switches  # nodes that have to be integrated into the tree
        while len(todo) > 1:
            new_todo = []
            for i in range(0, len(todo), 2):
                sw = self.addSwitch(
                    's' + str(switch_count),
                    dpid=Topology.make_dpid())
                switch_count += 1
                new_todo.append(sw)

                self.addLink(
                    todo[i],
                    sw,
                    bw=bandwidth,
                    delay="%ims" % Topology.latency)
                if len(todo) > (i + 1):
                    self.addLink(
                        todo[i + 1],
                        sw,
                        bandwidth=bandwidth,
                        delay="%ims" % Topology.latency)

            todo = new_todo
            bandwidth *= 2.0


class Clos(Topology):
    """A Clos topology.
    """

    def __init__(self, racks):
        Topology.__init__(self, racks)

        num_core = 2
        pod_size = 2
        num_pods = int(math.ceil(len(racks) / pod_size))

        bw = 50
        lat = 0.05
        qsize = 75

        pod = []
        core = []

        s = 1

        # build core:
        for c in range(num_core):
            cs = self.addSwitch('s' + str(s), dpid=Topology.make_dpid())
            s += 1
            core.append(cs)

        # build Pods
        for p in range(num_pods):
            p1 = self.addSwitch('s' + str(s), dpid=Topology.make_dpid())
            s += 1
            p2 = self.addSwitch('s' + str(s), dpid=Topology.make_dpid())
            s += 1

            pod.append(p1)
            pod.append(p2)

            # wire tors to this pod:
            start = p * pod_size
            end = (p+1) * pod_size
            if end > len(racks):
                end = len(racks)+1

            for i in range(start, end):
                sw = self.tor_switches[i]
                self.addLink(
                    p1,
                    sw,
                    bw=bw,
                    delay=str(lat) + "ms",
                    use_tbf=False,
                    enable_red=False,
                    max_queue_size=qsize)
                self.addLink(
                    p2,
                    sw,
                    bw=bw,
                    delay=str(lat) + "ms",
                    use_tbf=False,
                    enable_red=False,
                    max_queue_size=qsize)

        # wire core and pods:
        if num_core > 0:
            for k, v in enumerate(pod):
                # calculate the indices of the core switches:
                i1 = (k * 2) % num_core
                i2 = (k * 2 + 1) % num_core
                self.addLink(
                    core[i1],
                    v,
                    bw=bw,
                    delay=str(lat) + "ms",
                    use_tbf=False,
                    enable_red=False,
                    max_queue_size=qsize)
                self.addLink(
                    core[i2],
                    v,
                    bw=bw,
                    delay=str(lat) + "ms",
                    use_tbf=False,
                    enable_red=False,
                    max_queue_size=qsize)
