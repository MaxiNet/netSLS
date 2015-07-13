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
import network_simulator
import process_manager
import process

logger = logging.getLogger(__name__)


class TransportAPI(object):
    """Transport API used by Transmission threads to handle coflows and send
    coflow transmissions through MaxiNet.
    """

    _process_manager = None

    @classmethod
    def init(cls):
        """Initialize the transport API."""
        if cls._process_manager:
            cls._process_manager.stop()
        cls._process_manager = process_manager.ProcessManager(
            configuration.get_process_manager_polling_interval())
        cls._process_manager.start()

    @classmethod
    def finalize(cls):
        """Finalizes the transport API."""
        cls._process_manager.stop()
        cls._process_manager = None

    @classmethod
    def register_coflow(cls, coflow_description):
        """Register a new coflow."""
        return "COFLOW-00000"

    @classmethod
    def unregister_coflow(cls, coflow_id):
        """Un-register a coflow.

        Returns:
            True on success, False otherwise.
        """
        return True

    @classmethod
    def transmit_n_bytes(cls, coflow_id, source, destination, n_bytes, subscription_key):
        """Transmit n bytes from source to destination.

        Args:
            coflow_id: Coflow id the transmission belongs to.
            source: MaxiNet node of the source.
            destination: MaxiNet node of the destination.
            n_bytes: Number of bytes to transmit.
            subscription_key: Key under which the result will be published.

        Returns:
            transmission_id of the new transmission.
        """
        raise NotImplementedError()

    @classmethod
    def setup_node(cls, node):
        """Perform setup on MaxiNet node when the simulation is started.

        Args:
            node: MaxiNet node to perform setup on.
        """
        pass

    @classmethod
    def teardown_node(cls, node):
        """Perform teardown on MaxiNet node when the simulation is stopped.

        Args:
            node: MaxiNet node to perform teardown on.
        """
        pass

    @classmethod
    def get_remote_transport_bin_path(cls):
        """Returns path to transport binaries on worker nodes.

        Returns:
            Path to transport binaries on worker nodes.
        """
        return os.path.join(configuration.get_worker_working_directory(),
                            "transport_bin")

    @classmethod
    def _get_binary_path(cls, binary):
        """Returns path of binary on worker nodes.

        Returns:
            Path to binary on worker nodes.
        """
        return os.path.join(cls.get_remote_transport_bin_path(), binary)


class TransportTCP(TransportAPI):
    """TCP transport API.

    This transport API sends data through MaxiNet via TCP sockets. Coflows are
    ignored.
    """

    @classmethod
    def setup_node(cls, node):
        # start receiver
        receiver_cmd = "%s %i" % (
            cls._get_binary_path("tcp_receive"),
            configuration.get_tcp_receiver_port())
        receiver_process = process.ReceiverProcess(node, receiver_cmd)
        cls._process_manager.start_process(receiver_process)

    @classmethod
    def teardown_node(cls, node):
        # kill receiver
        node.cmd("killall tcp_receive")

    @classmethod
    def transmit_n_bytes(cls, coflow_id, source, destination, n_bytes,
                         subscription_key):
        topology = network_simulator.NetworkSimulator.get_instance().topology
        destination_ip = topology.get_ip_address(destination.nn)

        trans_command = "%s %s %i %i" % (
            cls._get_binary_path("tcp_send"), destination_ip,
            configuration.get_tcp_receiver_port(), n_bytes)
        trans_process = process.TransmissionProcess(source, trans_command,
                                                    subscription_key)
        cls._process_manager.start_process(trans_process)

        return trans_process.transmission_id
