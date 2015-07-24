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

from ConfigParser import ConfigParser
import inspect
from os.path import isfile, abspath

import transport_api

_CONFIG = dict()


def read(path):
    """Read and parse configuration file.

    Args:
        path: Path to the configuration file.
    """
    if not path:
        return
    if not isfile(path):
        raise Exception("Configuration file '%s' does not exist." % path)

    config_parser = ConfigParser.ConfigParser()
    config_parser.read(path)
    global _CONFIG
    _CONFIG = config_parser.defaults()


def get_publisher_port():
    """Port for the ZeroMQ publisher."""
    return _CONFIG.get("PublisherPort", 5500)


def get_rpc_server_port():
    """Port for JSON-RPC server."""
    return _CONFIG.get("RPCServerPort", 5501)


def get_tcp_receiver_port():
    """Port used in transportTCP."""
    return _CONFIG.get("TCPReceiverPort", 5502)


def get_process_manager_polling_interval():
    """Polling interval for TransmissionManager."""
    return _CONFIG.get("TransmissionManagerPollingInterval", 1)


def get_transport_api():
    """Transport API class."""
    api_name = _CONFIG.get("TransportAPI", "TransportTCP")
    for key, value in inspect.getmembers(transport_api, inspect.isclass):
        if key == api_name:
            return value
    return None


def get_worker_working_directory():
    """Working directory on MaxiNet workers."""
    working_directory = _CONFIG.get("WorkerLogDir", "/tmp/netSLS")

    # MaxiNet executes commands with root permission. We don't want to mess up our workers.
    if abspath(working_directory) == "/":
        working_directory = "/tmp/netSLS"

    return working_directory
