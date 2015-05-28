#! /usr/bin/python
import threading

from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc.transports.http import HttpPostClientTransport
from tinyrpc import RPCClient
import zmq

HOST ="fgcn-of-20.cs.upb.de"
HOST ="localhost"

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

    def run(self):
        transmission_id = self.remote_server.transmit_n_bytes(
            "", self.source, self.destination, self.n_bytes, self.key)
        print("%s: Returned transmission_id = %i" % (self.key, transmission_id))
        print("%s: [ZMQ] %s" % (self.key, self.subscriber.recv().splitlines()[1]))

def main():
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://%s:5500" % HOST)
    subscriber.setsockopt(zmq.SUBSCRIBE, "DEFAULT")
    subscriber.setsockopt(zmq.SUBSCRIBE, "SUB_KEY")

    rpc_client = RPCClient(
        JSONRPCProtocol(),
        HttpPostClientTransport("http://%s:5501" % HOST)
    )
    remote_server = rpc_client.get_proxy()

    racks = [ \
        {"id":"rack0", "hosts":["host00", "host01"]}, \
        {"id":"rack1", "hosts":["host10", "host11"]}, \
        {"id":"rack2", "hosts":["host20", "host21"]}, \
        {"id":"rack3", "hosts":["host30", "host31"]}, \
        ]

    topology = {
            "type" : "FatTree",
            "arguments" : {
                "racks" : racks
                }
            }
    
    print("== 1. Testing start_simulation ==")
    print(remote_server.start_simulation(topology))
    print("[ZMQ] %s" % subscriber.recv().splitlines()[1])

    print

    print("== 2. Testing register_coflow ==")
    #TODO: test coflow description, once specified
    coflow_id = remote_server.register_coflow("coflow description")
    print("Returned coflow_id = %s" % coflow_id)

    print

    print("== 3. Testing unregister_coflow ==")
    #TODO: test coflow description, once specified
    print(remote_server.unregister_coflow(coflow_id))

    print

    print("== 4. Testing transmit_n_bytes ==")
    senders = list()
    for i in range(0, 1):
        senders.append(Sender(context, "host00", "host01", 2))# * 1024 * 1024))
        senders.append(Sender(context, "host20", "host21", 2))# * 1024 * 1024))

    for sender in senders:
        sender.start()

    for sender in senders:
        sender.join()

if __name__ == "__main__":
    main()
