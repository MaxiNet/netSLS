"""
Copyright 2015 Malte Splietker

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

import inspect
import os.path
import time
import subprocess

from MaxiNet.Frontend import maxinet
from tinyrpc.dispatch import public
from mininet.node import OVSSwitch

import configuration
from publisher import Publisher
from rpc_server import RPCServer
import topology
from transmission import Transmission
from transmission_manager import TransmissionManager
import transport_api

import traceback


class NetworkSimulator(object):
    """Implementation of the network simulators public interface.

    This class implements the public interface made available through the RPC
    server.
    This class is singleton. The instance is accessable throught get_instance().

    Attributes:
        publisher: ZeroMQ publisher to publish results asynchronously.
        rpc_server: RPCServer providing this interface.
        cluster: MaxiNet cluster.
        __experiment: Currently running MaxiNet experiment.
        topology: Topology used by current MaxiNet experiment.
    """

    # Singleton instance
    _INSTANCE = None

    def __init__(self):
        self.publisher = Publisher()
        self.rpc_server = RPCServer(self)
        self.transmission_manager = TransmissionManager(
            configuration.get_transmission_manager_polling_interval())

        self.cluster = maxinet.Cluster()
        self.__experiment = None

        self.topology = None

    def start(self):
        """Start the network simulator."""
        self.cluster.start()
        self.transmission_manager.start()
        # start serving rpc calls forever
        self.rpc_server.serve_forever()

    @public
    def start_simulation(self, topo):
        """RPC: Start a new simulation.

        Starts a new MaxiNet experiment with the given topology. If there is
        an experiment running MaxiNet is reset first.

        Args:
            topo: A dict representing the topology description. A topology
                description has a type, which must correspond to a class in the
                topology module and arguments. The arguments may vary for the
                different topology classes. However, there must always be a list
                of racks. For example:

                {
                    "type" : "FatTree",
                    "arguments" : {
                        "racks" : [ ... ]
                        }
                }

        Returns:
            True on success, False otherwise.
        """
        try:
            # Copy transport api executables onto workers
            for worker in self.cluster.worker:
                dest_dir = transport_api.TransportAPI.REMOTE_TRANSPORT_BIN_PATH
                rm_cmd = "ssh %s rm -rf %s" % (worker.hn(), dest_dir)
                mkdir_cmd = "ssh %s mkdir -p %s" % (
                    worker.hn(), os.path.dirname(dest_dir))
                copy_cmd = "scp -r ./transport_bin %s:%s" % (
                    worker.hn(), dest_dir)
                subprocess.check_output(rm_cmd.split())
                subprocess.check_output(mkdir_cmd.split())
                subprocess.check_output(copy_cmd.split())

                try:
                    kill_cmd = "ssh %s sudo pkill nc" % worker.hn()
                    subprocess.check_output(kill_cmd.split())
                except Exception:
                    pass

            # Create topology object
            topology_class = None
            for key, value in inspect.getmembers(topology, inspect.isclass):
                if key == topo["type"]:
                    topology_class = value
                    break
            if not topology_class:
                print("ERROR: topology class \"%s\" not found." % topo["type"])
                return False

            self.topology = topology_class(**topo["arguments"])

            # Reset & start experiment
            if self.__experiment:
                for host in self.__experiment.hosts:
                    # tear down transmission api
                    configuration.get_transport_api().teardown(host)
                self.__experiment.stop()

            self.__experiment = maxinet.Experiment(
                self.cluster, self.topology, switch=OVSSwitch)
            self.__experiment.setup()

            # start traffGen on all emulated Hosts!

            hosts_per_rack = 20
            flow_file = "~/trafficGen/flows.csv"
            scale_factor_size = "1"
            scale_factor_time = "150"
            participatory = "0"
            participatory_sleep = "0"
            loop = "true"
            config = "/tmp/traffGen.config"
            ip_base = "10.0"

            for host in self.__experiment.hosts:
                # start traffic generator
                ip = host.IP()
                ip_ar = ip.split(".")
                host_id = hosts_per_rack * (int(ip_ar[2]) - 1) + int(ip_ar[3])

                traffgen_cmd = "/home/schwabe/trafficGen/trafficGenerator/trafficGenerator/traffGen --hosts_per_rack %d \
                --ip_base %s --host_id %s --flow_file %s --scale_factor_size %s --scale_factor_time %s \
                --participatory %s --participatory_sleep %s --loop %s --config %s &> /tmp/IP-%s-traff-Gen.log &" % (
                    hosts_per_rack, ip_base, host_id, flow_file,
                    scale_factor_size, scale_factor_time, participatory,
                    participatory_sleep, loop, config, host.IP())
                host.cmd(traffgen_cmd)

                host.cmd("/home/schwabe/trafficGen/trafficGenerator/trafficServer2/trafficServer2 &>/dev/null &")

                # setup transport api
                configuration.get_transport_api().setup(host)

            # send start command to all traffGen processes.
            time.sleep(5)

#            for host in self.__experiment.hosts:
#                print(host.cmd("ping -c 3 10.0.1.1"))

#            self.__experiment.CLI(locals(), globals())
            
            for w in self.cluster.workers():
                w.run_cmd("killall -s USR2 traffGen &")

            result = {
                "type": "SIMULATION_STARTED",
                "data": {}}
            self.publisher.publish("DEFAULT", result)

            return True
        except:
            traceback.print_exc()

    @public
    def register_coflow(self, coflow_description):
        """RPC: Register a new coflow.

        Register a new coflow using the current transport API.

        Args:
            coflow_description: Coflow description for the new coflow. This
                conforms to the Varys CoflowDescription and is a json string of
                the following form:
                
                {
                    "name" : "CoflowX",
                    "coflowType" : "DEFAULT",
                    "maxFlows" : 42,
                    "maxSizeInBytes" : 1024
                }

        Returns:
            Coflow id of type string.
        """
        return configuration.get_transport_api().register_coflow(
            coflow_description)

    @public
    def unregister_coflow(self, coflow_id):
        """RPC: Unregister a coflow.

        Unregister the coflow corresponding to coflow_id using the currente
        transort API.

        Args:
            coflow_id: Coflow id of the coflow to remove.

        Returns:
            True on success, False otherwise.
        """
        return configuration.get_transport_api().unregister_coflow(
            coflow_id)

    @public
    def transmit_n_bytes(self, coflow_id, source, destination, n_bytes,
                         subscription_key):
        """RPC: Transmit n bytes from source to destination

        Send n_bytes bytes from source to destination using the current
        transport API. The transmission belongs to the given coflow_id. The
        result will be published asynchronously under the given
        subscription_key.

        Args:
            coflow_id: Coflow id the transmission belongs to.
            source: Hostname of the source.
            destination: Hostname of the destination.
            n_bytes: Number of bytes to transmit.
            subscription_key: Key under which the result will be published.

        Returns:
            transmission id of type integer (unique).
        """
        print("NS: transmit_n_bytes")
        mn_source = self.__experiment.get_node(
            self.topology.get_mn_hostname(source))
        mn_destination = self.__experiment.get_node(
            self.topology.get_mn_hostname(destination))
        transmission = Transmission(
            coflow_id, mn_source, mn_destination, n_bytes, subscription_key)
        self.transmission_manager.start_transmission(transmission)

        return transmission.transmission_id

    @classmethod
    def get_instance(cls):
        """Returns a singleton instance of this class."""
        if not cls._INSTANCE:
            cls._INSTANCE = NetworkSimulator()
        return cls._INSTANCE
