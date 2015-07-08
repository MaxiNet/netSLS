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

logger = logging.getLogger(__name__)

class TransportAPI(object):
    """Transport API used by Transmission threads to handle coflows and send
    coflow transmissions through MaxiNet.
    """

    # The transport binaries are copied to this path on the worker nodes
    REMOTE_TRANSPORT_BIN_PATH = "/tmp/transport_bin"

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
    def transmit_n_bytes(cls, coflow_id, source, destination, n_bytes):
        """Transmit n bytes from source to destination.

        Args:
            coflow_id: Coflow id the transmission belongs to.
            source: MaxiNet node of the source.
            destination: MaxiNet node of the destination.
            n_bytes: Number of bytes to transmit.
            subscription_key: Key under which the result will be published.

        Returns:
            PID of sending process (daemonized) or None on failure
        """
        raise NotImplementedError()

    @classmethod
    def setup_host(cls, host):
        """Perform setup on host when the simulation is started.

        Args:
            host: MaxiNet host to perform setup on.
        """
        pass

    @classmethod
    def teardown(cls, host):
        """Perform teardown on host when the simulation is stopped.

        Args:
            host: MaxiNet host to perform teardown on.
        """
        pass

    @classmethod
    def _get_binary_path(cls, binary):
        """Returns path of binary on worker nodes.

        Returns:
            Path to binary on worker nodes.
        """
        return os.path.join(cls.REMOTE_TRANSPORT_BIN_PATH, binary)


class TransportTCP(TransportAPI):
    """TCP transport API.

    This transport API sends data through MaxiNet via TCP sockets. Coflows are
    ignored.
    """

    @classmethod
    def setup(cls, host):
        # start receiver
        receiver_cmd = "%s %i" % (
            cls._get_binary_path("tcp_receive"),
            configuration.get_tcp_receiver_port())
        result = host.cmd("%s %s %s" % (
            cls._get_binary_path("daemonize"),
            configuration.get_worker_log_dir(),
            receiver_cmd)).splitlines()
        if len(result) == 0 or len(result) > 1 or not result[0].isdigit():
            logger.error("Failed to start receiver")
            return False

        return True

    @classmethod
    def teardown(cls, host):
        # kill receiver
        host.cmd("killall tcp_receive")

    @classmethod
    def transmit_n_bytes(cls, coflow_id, source, destination, n_bytes):
        topology = network_simulator.NetworkSimulator.get_instance().topology
        destination_ip = topology.get_ip_address(destination.nn)

        transmit_cmd = "%s %s %i %i" % (cls._get_binary_path("tcp_send"),
                                        destination_ip,
                                        configuration.get_tcp_receiver_port(),
                                        n_bytes)

        logger.debug("Invoking %s on host %s" % (transmit_cmd, source.nn))

        # start daemonized sender
        pid = source.cmd("%s %s %s" % (
            cls._get_binary_path("daemonize"),
            configuration.get_worker_log_dir(),
            transmit_cmd)).splitlines()[0]

        if not pid.isdigit():
            return None

        return int(pid)
