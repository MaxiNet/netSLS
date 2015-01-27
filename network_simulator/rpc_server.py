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

import gevent
import gevent.wsgi
import gevent.queue
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc.transports.wsgi import WsgiServerTransport
from tinyrpc.server.gevent import RPCServerGreenlets
from tinyrpc.dispatch import RPCDispatcher

import configuration

class RPCServer(object):
    """Provides an interface via JSON-RPC.

    This class creates an JSON-RPC server that dispatches calls to @public
    methods of the given interface.
    """
    def __init__(self, interface):
        """
        Args:
            interface: Interface to provide
        """
        self.__dispatcher = RPCDispatcher()
        transport = WsgiServerTransport(queue_class=gevent.queue.Queue)

        wsgi_server = gevent.wsgi.WSGIServer(('', \
            configuration.get_rpc_server_port()), transport.handle)
        gevent.spawn(wsgi_server.serve_forever)

        self.__server = RPCServerGreenlets(
            transport,
            JSONRPCProtocol(),
            self.__dispatcher
        )

        print("created rpc server with url", configuration.get_rpc_server_port())

        # register interface's public functions
        self.__dispatcher.register_instance(interface, "")

    def serve_forever(self):
        """Starts the rpc server and serves forever."""
        print("started rpc server")
        self.__server.serve_forever()
