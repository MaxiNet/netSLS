from ConfigParser import ConfigParser
import inspect
from os.path import isfile

import network_simulator
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
    """Port used by netcat in transportTCP."""
    return _CONFIG.get("TCPReceiverPort", 5502)

def get_transport_api():
    """Transport API class."""
    api_name = _CONFIG.get("TransportAPI", "TransportTCP")
    for key, value in inspect.getmembers(transport_api, inspect.isclass):
        if key == api_name:
            return value
    return None
