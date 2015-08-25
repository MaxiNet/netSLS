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
import logging
import time

import configuration
import network_emulator
import threading
import transport_api
import utils

logger = logging.getLogger(__name__)


class Process(object):
    """Perform execution of background processes on MaxiNet nodes and handle results.

    Attributes:
        _node: MaxiNet node the command is executed on.
        _command: Command executed by the process.

        pid: PID of the remote process on the worker.
        start_time: Start time of transmission.
        end_time: End time of transmission.
    """

    SUCCESSFUL = "SUCCESSFUL"
    FAILED = "FAILED"

    def __init__(self, node, command):
        self._node = node
        self._command = command

        self.pid = None
        self.start_time = -1
        self.end_time = -1

    def start(self):
        """Starts the process on the MaxiNet node and returns the remote PID.

        Returns:
            True if the process started successfully, False otherwise.
        """
        self.start_time = time.time()

        # start command as daemonized process
        logger.debug("Daemonizing \"%s\" on MaxiNet node %s" % (self._command,
                                                                self._node.nn))
        result = self._node.cmd("%s %s %s" % (
            transport_api.TransportAPI.get_binary_path("daemonize"),
            configuration.get_worker_working_directory(),
            self._command))
        pid = result.splitlines()[0]

        # daemonize is supposed to print ONLY the PID of the started process
        if not pid.isdigit():
            logger.error("Failed to start process:\n{}".format(
                utils.indent(result, 2)))
            return False

        self.pid = int(pid)

        return True

    def kill(self):
        """Kills the process running on the MaxiNet node."""
        self._node.cmd("kill %i" % self.pid)

    def call_terminated(self, result):
        """Callback to be invoked, when the process terminated.

        Args:
            result: termination result (SUCCESSFUL or FAILED).
        """
        self.end_time = time.time()

        if result == self.__class__.SUCCESSFUL:
            self._terminated_successfully()
        else:
            self._terminated_failingly()

    def _terminated_failingly(self):
        """This method is executed, when the process failed.

        Overwrite in subclasses.
        """
        pass

    def _terminated_successfully(self):
        """This method is executed, when the process terminated successfully.

        Overwrite in subclasses.
        """
        pass

    def get_worker(self):
        """Returns the worker the process is executed on.

        Returns:
            MaxiNet worker the process is executed on.
        """
        return self._node.worker


class TransmissionProcess(Process):
    """Performs a transmission in MaxiNet and reports results to subscribers.

    Attributes:
        subscription_key: Key under which the result will be published.
    """

    # Counts the number of transmission objects created.
    _COUNT = 0

    # Lock for _COUNT variable.
    _COUNT_LOCK = threading.Lock()

    def __init__(self, node, command, subscription_key):
        super(self.__class__, self).__init__(node, command)

        self.__subscription_key = subscription_key

        with self.__class__._COUNT_LOCK:
            self.transmission_id = self.__class__._COUNT
            self.__class__._COUNT += 1

    def _terminated_successfully(self):
        """Report transmission success to subscriber via the Publisher class."""
        logger.info("TransmissionProcess with id %i terminated successfully. Duration: %f s" %
                    (self.transmission_id, (self.end_time - self.start_time)))
        result_string = {
            "type": "TRANSMISSION_SUCCESSFUL",
            "data": {
                "transmission_id": self.transmission_id,
                "duration": (self.end_time - self.start_time)
            }
        }
        network_emulator.NetworkEmulator.get_instance().publisher.publish(
            self.__subscription_key, json.dumps(result_string))

    def _terminated_failingly(self):
        """Report transmission failure to subscriber via the Publisher class."""
        logger.error("TransmissionProcess with id %i failed" % self.transmission_id)
        result_string = {
            "type": "TRANSMISSION_FAILED",
            "data": {
                "transmission_id": self.transmission_id
            }
        }
        network_emulator.NetworkEmulator.get_instance().publisher.publish(
            self.__subscription_key, json.dumps(result_string))


class ReceiverProcess(Process):
    """Starts a receiver process on a MaxiNet node."""

    def _terminated_successfully(self):
        logger.info("Receiver process on MaxiNet node %s terminated successfully" % self._node.nn)

    def _terminated_failingly(self):
        # TODO: Implement appropriate error handling, as this must not occur.
        logger.error("Receiver process on MaxiNet node %s terminated unexpectedly" % self._node.nn)
