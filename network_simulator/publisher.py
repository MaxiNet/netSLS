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

import threading
import zmq

import configuration

class Publisher(object):
    """ZeroMQ publisher to asynchronously publish results."""
    def __init__(self):
        self.__context = zmq.Context()
        self.__socket = self.__context.socket(zmq.PUB)
        self.__socket.bind("tcp://*:%i" % (configuration.get_publisher_port()))

        self.__socket_lock = threading.Lock()

    def publish(self, subscription_key, result):
        """Publish a result under the specified subscription key.

        Args:
            subscription_key: Subscription key.
            result: Result to publish.
        """
        with self.__socket_lock:
            self.__socket.send_string("%s\n%s" % (subscription_key, result))
