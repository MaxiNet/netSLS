#! /usr/bin/python
import time

from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc.transports.http import HttpPostClientTransport
from tinyrpc import RPCClient
import zmq

import topology
HOST ="fgcn-of-20.cs.upb.de"

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
    transmission_id = remote_server.transmit_n_bytes(coflow_id, "host00", \
        "host10", 1024*1024*1024, "SUB_KEY")
    print("Returned transmission_id = %i" % transmission_id)

    print("[ZMQ] %s" % subscriber.recv().splitlines()[1])
    
if __name__ == "__main__":
    main()
