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
import traceback

import gevent
import gevent.wsgi
import gevent.queue
from tinyrpc import MethodNotFoundError, ServerError
from tinyrpc.protocols.jsonrpc import JSONRPCProtocol
from tinyrpc.transports.wsgi import WsgiServerTransport
from tinyrpc.server.gevent import RPCServerGreenlets
from tinyrpc.dispatch import RPCDispatcher

import configuration
import utils

logger = logging.getLogger(__name__)


class RPCServer(object):
    """Provides an interface via JSON-RPC.

    This class creates an JSON-RPC server that dispatches calls to @public
    methods of the given interface.
    """
    def __init__(self, interface):
        """
        Args:
            interface: Interface to provide.
        """
        self.__dispatcher = RPCLoggingDispatcher()
        transport = WsgiServerTransport(queue_class=gevent.queue.Queue)

        self._wsgi_server = gevent.wsgi.WSGIServer(
            ('', configuration.get_rpc_server_port()),
            transport.handle,
            log=None)
        gevent.spawn(self._wsgi_server.serve_forever)

        self.__server = RPCServerGreenlets(
            transport,
            JSONRPCProtocol(),
            self.__dispatcher
        )

        # register interface's public functions
        self.__dispatcher.register_instance(interface, "")

    def serve_forever(self):
        """Starts the RPC server and serves forever."""
        logger.info("RPC server started listening on 0.0.0.0:{}".format(
            configuration.get_rpc_server_port()))
        try:
            self.__server.serve_forever()
        except gevent.hub.LoopExit:
            # FIXME: Right now this exception seems to be expected in this situation. Maybe have another look...
            pass

    def stop(self):
        """Stops the RPC server."""
        self._wsgi_server.stop()


class RPCLoggingDispatcher(RPCDispatcher):
    """A modified version of RPCDispatcher which logs errors on the server side."""

    def _dispatch(self, request):
        try:
            try:
                method = self.get_method(request.method)
            except KeyError as e:
                logger.error("RPC method not found: {}".format(request.method))
                return request.error_respond(MethodNotFoundError(e))

            # we found the method
            try:
                result = method(*request.args, **request.kwargs)
            except Exception as e:
                # an error occured within the method, return it
                logger.error("RPC method {} failed:\n{}".format(
                    request.method, utils.indent(traceback.format_exc(), 2)))
                return request.error_respond(e)

            # respond with result
            return request.respond(result)
        except Exception as e:
            logger.error("RPC method {} failed unexpectedly:\n{}".format(
                request.method, utils.indent(traceback.format_exc(), 2)))
            # unexpected error, do not let client know what happened
            return request.error_respond(ServerError())
