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

import os.path
import time

import configuration
import network_simulator

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
        """Unregister a coflow.

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
            True on success, False otherwise.
        """
        raise NotImplementedError()

    @classmethod
    def setup_host(cls, host):
        pass

    @classmethod
    def teardown(cls, host):
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
        return
        # start receiver
        ret = host.cmd("%s %i" % (cls._get_binary_path("tcp_receive"), \
                configuration.get_tcp_receiver_port()))
#        if len(ret) != 0:
#            return False

        return True

    @classmethod
    def teardown(cls, host):
        return
        # kill receiver
        host.cmd("pkill nc")

    @classmethod
    def transmit_n_bytes(cls, coflow_id, source, destination, n_bytes):
        topology = network_simulator.NetworkSimulator.get_instance().topology
        destination_ip = topology.get_ip_address(destination.nn)

        # start sender
        ret = source.cmd("%s %s %i %i" % ( \
                cls._get_binary_path("tcp_send"), \
                destination_ip, configuration.get_tcp_receiver_port(), n_bytes))
        if len(ret) != 0:
            return False

        return True
