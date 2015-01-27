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
