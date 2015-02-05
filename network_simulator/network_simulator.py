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
import subprocess

from MaxiNet.Frontend import maxinet
from tinyrpc.dispatch import public

import configuration
from publisher import Publisher
from rpc_server import RPCServer
import topology
from transmission import Transmission
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
        __cluster: MaxiNet cluster.
        __experiment: Currently running MaxiNet experiment.
        topology: Topology used by current MaxiNet experiment.
    """

    # Singleton instance
    _INSTANCE = None

    def __init__(self):
        self.publisher = Publisher()
        self.rpc_server = RPCServer(self)

        self.__cluster = maxinet.Cluster()
        self.__experiment = None

        self.topology = None

    def start(self):
        """Start the network simulator."""
        self.__cluster.start()
        # start serving rpc calls forever
        self.rpc_server.serve_forever()

    @public
    def start_simulation(self, topo):
      try:
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
        # Copy transport api executables onto workers
        for worker in self.__cluster.worker:
            dest_dir = transport_api.TransportAPI.REMOTE_TRANSPORT_BIN_PATH
            rm_cmd = "ssh %s rm -rf %s" % (worker.hn(), dest_dir)
            mkdir_cmd = "ssh %s mkdir -p %s" % (worker.hn(), \
                    os.path.dirname(dest_dir))
            copy_cmd = "scp -r ./transport_bin %s:%s" % (worker.hn(), dest_dir)
            subprocess.check_output(rm_cmd.split())
            subprocess.check_output(mkdir_cmd.split())
            subprocess.check_output(copy_cmd.split())

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
            self.__experiment.stop()
        self.__experiment = maxinet.Experiment(self.__cluster, self.topology)
        self.__experiment.setup()


        #start traffGen on all emulated Hosts!

        hostsPerRack = "20"
        flowFile = "~/traffGen/flows.csv"
        scaleFactorSize = "1"
        scaleFactorTime = "150"
        participatory = "false"
        participatorySleep = "0"
        loop = "true"
        config = "/tmp/traffGen.config"
        ipBase = "10.0"

        for host in self.__experiment.hosts:
            ip = host.IP()
            ipAr = ip.split(".")
            hostId = int(hostsPerRack) * (int(ipAr[2]) - 1) + int(ipAr[3])

            host.cmd("~/traffGen/trafficGenerator/trafficGenerator/traffGen --hostsPerRack %d \
            --ipBase %s --hostId %s --flowFile %s --scaleFactorSize %s --scaleFactorTime %s \
            --participatory %s --participatorySleep %s --loop %s --config %s &" % (hostsPerRack, ipBase, hostId,flowFile,scaleFactorSize,scaleFactorTime,participatory,participatorySleep,loop,config ))

        #send start command to all traffGen processes.
        for w in self.__cluster.workers:
            w.run_cmd("killall -s USR2 traffGen &")




        result = {
                "type" : "SIMULATION_STARTED",
                "data" : {}
                }
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
        return configuration.get_transport_api().register_coflow( \
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
        return configuration.get_transport_api().unregister_coflow( \
                coflow_id)

    @public
    def transmit_n_bytes(self, coflow_id, source, destination, n_bytes, \
            subscription_key):
        """RPC: Transmit n bytes from source to destination

        Send n_bytes bytes from source to destination using the current
        transport API. The transmission belongs to the given coflow_id. The
        result will be published asynchroneously under the given
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
        mn_source = self.__experiment.get_node(
                self.topology.get_mn_hostname(source))
        mn_destination = self.__experiment.get_node(
                self.topology.get_mn_hostname(destination))
        transmission = Transmission(coflow_id, mn_source, mn_destination, \
                n_bytes, subscription_key)
        transmission.start()

        return transmission.transmission_id

    @classmethod
    def get_instance(cls):
        """Returns a singleton instance of this class."""
        if not cls._INSTANCE:
            cls._INSTANCE = NetworkSimulator()
        return cls._INSTANCE
