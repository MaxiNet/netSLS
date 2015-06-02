#! /usr/bin/python

import requests
import json
import logging
import logging.config
logging.config.fileConfig("logging.cfg")

import threading
import unittest

from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc.transports.http import HttpPostClientTransport
from tinyrpc import RPCClient
import zmq

logger = logging.getLogger("Testing")

HOST = "localhost"

class Sender(threading.Thread):
    count = 0

    def __init__(self, zmq_context, source, destination, n_bytes):
        threading.Thread.__init__(self)

        self.key = "SENDER%i" % Sender.count
        Sender.count += 1

        self.subscriber = zmq_context.socket(zmq.SUB)
        self.subscriber.connect("tcp://%s:5500" % HOST)
        self.subscriber.setsockopt(zmq.SUBSCRIBE, self.key)

        rpc_client = RPCClient(
            JSONRPCProtocol(),
            HttpPostClientTransport("http://%s:5501" % HOST)
        )
        self.remote_server = rpc_client.get_proxy()

        self.source = source
        self.destination = destination
        self.n_bytes = n_bytes

        self.result = ""

    def run(self):
        try:
            transmission_id = self.remote_server.transmit_n_bytes(
                "", self.source, self.destination, self.n_bytes, self.key)
        except requests.exceptions.ConnectionError:
            self.result = "CONNECTION_REFUSED"
            return
        result = self.subscriber.recv().splitlines()[1]
        logger.info("%s: Returned transmission_id = %i" % (self.key, transmission_id))
        logger.debug("%s: [ZMQ] %s" % (self.key, result))

        self.result = json.loads(result)["type"]

class TestRPCFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.context = zmq.Context()
        cls.subscriber = cls.context.socket(zmq.SUB)
        cls.remote_server = None

        cls.subscriber.connect("tcp://%s:5500" % HOST)
        cls.subscriber.setsockopt(zmq.SUBSCRIBE, "DEFAULT")
        cls.subscriber.setsockopt(zmq.SUBSCRIBE, "SUB_KEY")

        rpc_client = RPCClient(
            JSONRPCProtocol(),
            HttpPostClientTransport("http://%s:5501" % HOST)
        )
        cls.remote_server = rpc_client.get_proxy()

        # Cross-test variables
        cls.coflow_id = ""

    def test_1_start_simulation(self):
        cls = self.__class__

        topology = {
            "type": "FatTree",
            "arguments": {
                "racks": [
                    {"id": "rack0", "hosts": ["host00", "host01"]},
                    {"id": "rack1", "hosts": ["host10", "host11"]},
                    {"id": "rack2", "hosts": ["host20", "host21"]},
                    {"id": "rack3", "hosts": ["host30", "host31"]},
                ]
            }
        }
        try:
            result = cls.remote_server.start_simulation(topology)
        except requests.exceptions.ConnectionError:
            self.assertTrue(False, msg="RPC connection refused")
        logger.debug("[ZMQ] %s" % cls.subscriber.recv().splitlines()[1])
        self.assertTrue(result)

    def test_2_register_coflow(self):
        #TODO: test coflow description, once specified
        cls = self.__class__

        try:
            result = cls.remote_server.register_coflow("coflow description")
        except requests.exceptions.ConnectionError:
            self.assertTrue(False, msg="RPC connection refused")
        logger.debug("Returned coflow_id = %s" % self.coflow_id)
        cls.coflow_id = result
        self.assertTrue(result.startswith("COFLOW-"))

    def test_3_unregister_coflow(self):
        #TODO: test coflow description, once specified
        cls = self.__class__

        try:
            result = cls.remote_server.unregister_coflow(cls.coflow_id)
        except requests.exceptions.ConnectionError:
            self.assertTrue(False, msg="RPC connection refused")
        self.assertTrue(result)

    def test_4_transmit_n_bytes(self):
        cls = self.__class__

        senders = list()
        for i in range(0, 2):
            senders.append(Sender(cls.context, "host00", "host01", 2 * 1024 * 1024))
            senders.append(Sender(cls.context, "host20", "host21", 2 * 1024 * 1024))

        for sender in senders:
            sender.start()

        for sender in senders:
            sender.join()
            self.assertNotEqual(sender.result, "CONNECTION_REFUSED", msg="RPC connection refused")
            self.assertEqual(sender.result, "TRANSMISSION_SUCCESSFUL")

if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestRPCFunctions)
    unittest.TextTestRunner(verbosity=2).run(suite)
