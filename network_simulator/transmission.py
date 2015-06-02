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

import json
import threading
import time

import configuration
import network_simulator


class Transmission(object):
    """Performs a transmission in MaxiNet.

    An instance of this class is a thread that performs a transmission in
    MaxiNet using the currently specified transmission API. After the
    transmission is completed the result is published via the Publisher class.

    Attributes:
        coflow_id: Coflow id the transmission belongs to.
        source: MaxiNet node of the source.
        destination: MaxiNet node of the destination.
        n_bytes: Number of bytes to transmit.
        subscription_key: Key under which the result will be published.
        transmission_id: Unique integer identifying this transmission.
        start_time: Start time of transmission
    """

    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"

    # Counts the number of transmission objects created.
    _COUNT = 0

    # Lock for _COUNT variable.
    _COUNT_LOCK = threading.Lock()

    def __init__(self, coflow_id, source, destination, n_bytes,
                 subscription_key):
        self.coflow_id = coflow_id
        self.source = source
        self.destination = destination
        self.n_bytes = n_bytes
        self.subscription_key = subscription_key

        self.start_time = -1

        with self.__class__._COUNT_LOCK:
            self.transmission_id = self.__class__._COUNT
            self.__class__._COUNT += 1

    def start(self):
        """Starts the transmission.

        Invokes a start of the transmission according to the specified
        transport API.

        Returns:
            PID of the sending  process.
        """
        self.start_time = time.time()
        return configuration.get_transport_api().transmit_n_bytes(
            self.coflow_id, self.source, self.destination, self.n_bytes)

    def stop(self, result):
        """Stops the transmission.

        After the sending process has terminated, send the result to the RPC
        subscriber.

        Args:
            result: Result from the terminated sending process.
        """
        duration = time.time() - self.start_time
        if result == Transmission.SUCCESSFUL:
            result_string = {
                "type": "TRANSMISSION_SUCCESSFUL",
                "data": {
                    "transmission_id": self.transmission_id,
                    "duration": duration
                    }
                }
        else:
            result_string = {
                "type": "TRANSMISSION_FAILED",
                "data": {
                    "transmission_id": self.transmission_id
                    }
                }
        network_simulator.NetworkSimulator.get_instance().publisher.publish(
            self.subscription_key, json.dumps(result_string))
