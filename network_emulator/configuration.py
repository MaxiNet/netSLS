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
import logging
from os.path import isfile, abspath

import transport_api

logger = logging.getLogger(__name__)

_CONFIG_PARSER = ConfigParser()


def read(path):
    """Read and parse configuration file.

    Args:
        path: Path to the configuration file.
    """
    if not path:
        logger.info("No configuration file found. Using defaults.")
        return
    if not isfile(path):
        raise Exception("Configuration file '%s' does not exist." % path)

    logger.info("Reading configuration from {}".format(abspath(path)))
    global _CONFIG_PARSER
    _CONFIG_PARSER.read(path)


def get_publisher_port():
    """Port for the ZeroMQ publisher."""
    publisher_port = 5500
    if _CONFIG_PARSER.has_option("DEFAULT", "PublisherPort"):
        publisher_port = _CONFIG_PARSER.getint("DEFAULT", "PublisherPort")
    return publisher_port


def get_rpc_server_port():
    """Port for JSON-RPC server."""
    rpc_server_port = 5501
    if _CONFIG_PARSER.has_option("DEFAULT", "RPCServerPort"):
        rpc_server_port = _CONFIG_PARSER.getint("DEFAULT", "RPCServerPort")
    return rpc_server_port


def get_process_manager_polling_interval():
    """Polling interval for ProcessManager."""
    polling_interval = 1.0
    if _CONFIG_PARSER.has_option("DEFAULT", "ProcessManagerPollingInterval"):
        polling_interval = _CONFIG_PARSER.getfloat("DEFAULT", "ProcessManagerPollingInterval")
    return polling_interval


def get_worker_working_directory():
    """Working directory on MaxiNet workers."""
    working_directory = "tmp/netSLS"
    if _CONFIG_PARSER.has_option("DEFAULT", "WorkerWorkingDirectory"):
        working_directory = _CONFIG_PARSER.get("DEFAULT", "WorkerWorkingDirectory")

    # MaxiNet executes commands with root permission. We don't want to mess up our workers.
    if abspath(working_directory) == "/":
        working_directory = "/tmp/netSLS"

    return working_directory


def get_transport_api():
    """Transport API class."""
    api_name = "TransportTCP"
    if _CONFIG_PARSER.has_option("DEFAULT", "TransportAPI"):
        api_name = _CONFIG_PARSER.get("DEFAULT", "TransportAPI")
    for key, value in inspect.getmembers(transport_api, inspect.isclass):
        if key == api_name:
            return value
    return None


def get_tcp_receiver_port():
    """Port for TCP receivers."""
    tcp_receiver_port = 5502
    if _CONFIG_PARSER.has_option("TransportTCP", "TCPReceiverPort"):
        tcp_receiver_port = _CONFIG_PARSER.getint("TransportTCP", "TCPReceiverPort")
    return tcp_receiver_port
