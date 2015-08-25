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

import logging
import os.path

import configuration
import network_emulator
import process_manager
import process
import ssh_tools

logger = logging.getLogger(__name__)


class TransportAPI(object):
    """Transport API used by Transmission threads to handle coflows and send
    coflow transmissions through MaxiNet.

    Attributes:
        _process_manager: Process manager watching transport API related processes.
        _nodes: List of nodes the transport API is used on.
    """

    def __init__(self):
        self._process_manager = process_manager.ProcessManager(
            configuration.get_process_manager_polling_interval())
        self._nodes = list()

    def init(self, nodes):
        """Initialize the transport API.

        Instantiate the process manager and all specified MaxiNet nodes.

        Args:
            nodes: List of MaxiNet nodes the transport API is used on.
        """
        logger.debug("Initializing transport API")

        # Copy binaries to workers
        for worker in {node.worker for node in nodes}:
            ssh_tools.copy_to_worker(
                worker, os.path.abspath("./transport_bin"),
                configuration.get_worker_working_directory())

        self._process_manager.start()

        self._nodes = nodes
        for node in self._nodes:
            self._init_node(node)

    def reset(self):
        """Reset the transport API.

        Reset all transport API specific effects on the MaxiNet nodes and stop the process manager.
        """
        for node in self._nodes:
            self._reset_node(node)
        self._nodes = list()

        if not self._process_manager:
            return
        self._process_manager.stop()
        self._process_manager.reset()

    def register_coflow(self, coflow_description):
        """Register a new coflow."""
        return "COFLOW-00000"

    def unregister_coflow(self, coflow_id):
        """Un-register a coflow.

        Returns:
            True on success, False otherwise.
        """
        return True

    def transmit_n_bytes(self, coflow_id, source, destination, n_bytes, subscription_key):
        """Transmit n bytes from source to destination.

        Args:
            coflow_id: Coflow id the transmission belongs to.
            source: MaxiNet node of the source.
            destination: MaxiNet node of the destination.
            n_bytes: Number of bytes to transmit.
            subscription_key: Key under which the result will be published.

        Returns:
            transmission_id of the new transmission or -1 if failed.
        """
        raise NotImplementedError()

    def _init_node(self, node):
        """Initialize a MaxiNet node according to the transport API.

        Args:
            node: MaxiNet node to initialize.
        """
        pass

    def _reset_node(self, node):
        """Reset a MaxiNet node when the emulation is stopped.

        Args:
            node: MaxiNet node to reset.
        """
        pass

    @classmethod
    def _get_remote_transport_bin_path(cls):
        """Returns path to transport binaries on worker nodes.

        Returns:
            Path to transport binaries on worker nodes.
        """
        return os.path.join(configuration.get_worker_working_directory(),
                            "transport_bin")

    @classmethod
    def get_binary_path(cls, binary):
        """Returns path of binary on worker nodes.

        Returns:
            Path to binary on worker nodes.
        """
        return os.path.join(cls._get_remote_transport_bin_path(), binary)


class TransportTCP(TransportAPI):
    """TCP transport API.

    This transport API sends data through MaxiNet via TCP sockets. Coflows are
    ignored.
    """

    def __init__(self):
        super(self.__class__, self).__init__()
        self.__node_to_receiver_pid_map = dict()

    def _init_node(self, node):
        # start receiver
        receiver_cmd = "%s %i" % (
            self.get_binary_path("tcp_receive"),
            configuration.get_tcp_receiver_port())
        receiver_process = process.ReceiverProcess(node, receiver_cmd)
        receiver_pid = self._process_manager.start_process(receiver_process)
        self.__node_to_receiver_pid_map[node] = receiver_pid

    def _reset_node(self, node):
        # kill receiver
        if node in self.__node_to_receiver_pid_map:
            self._process_manager.kill(self.__node_to_receiver_pid_map[node])

    def transmit_n_bytes(self, coflow_id, source, destination, n_bytes,
                         subscription_key):
        topology = network_emulator.NetworkEmulator.get_instance().topology
        destination_ip = topology.get_ip_address(destination.nn)

        trans_command = "%s %s %i %i" % (
            self.get_binary_path("tcp_send"), destination_ip,
            configuration.get_tcp_receiver_port(), n_bytes)
        trans_process = process.TransmissionProcess(source, trans_command,
                                                    subscription_key)
        if not self._process_manager.start_process(trans_process):
            return -1

        return trans_process.transmission_id
