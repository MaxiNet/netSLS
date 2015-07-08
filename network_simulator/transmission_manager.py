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
import os.path
import subprocess
import threading
import time

import configuration
import network_simulator
import transmission

logger = logging.getLogger(__name__)

class TransmissionManager(threading.Thread):
    """Thread for keeping track of open and completed transmissions.

    Each transmission is a separate process on one of the workers. This thread
    polls these workers for completed and failed transmissions.

    Attributes:
        interval: Polling interval in ms.
    """

    def __init__(self, interval):
        threading.Thread.__init__(self)

        self._stop = threading.Event()

        self.interval = interval
        self.open_transmissions_lock = threading.Lock()
        self.open_transmissions = dict()

    def stop(self):
        self._stop.set()

    def run(self):
        for worker in network_simulator.NetworkSimulator.get_instance().cluster.worker:
            self.open_transmissions[worker] = dict()

        while not self._stop.isSet():
            for worker in network_simulator.NetworkSimulator.get_instance().cluster.worker:
                successful_senders = []
                try:
                    successful_senders = self.__worker_get_pids_from_file(
                        worker,
                        os.path.join(configuration.get_worker_working_directory(), "pids_successful"))
                    logger.debug("Successful senders {!s}".format(successful_senders))
                except subprocess.CalledProcessError:
                    # This possible, if file pids_successful does not yet exist
                    pass

                failed_senders = []
                try:
                    failed_senders = self.__worker_get_pids_from_file(
                        worker,
                        os.path.join(configuration.get_worker_working_directory(), "pids_failed"))
                    logger.debug("Failed senders {!s}".format(successful_senders))
                except subprocess.CalledProcessError:
                    # This possible, if file pids_failed does not yet exist
                    pass

                # For every failed sender retrieve and print sender's output from worker
                for pid in failed_senders:
                    try:
                        logfile_content = self.__worker_get_file_content(
                            worker,
                            os.path.join(configuration.get_worker_working_directory(), "processes", str(pid)))
                        logfile_formatted = ""
                        for line in logfile_content.splitlines():
                            logfile_formatted += "\t\t%s\n" % line

                        logger.error("Transmission with PID {0} failed:\n{1}".format(
                            pid, logfile_formatted))
                    except subprocess.CalledProcessError, err:
                        logger.error("Failed to retrieve logfile for process with PID %i" % pid)
                        # Not allowed, as every daemonized process writes to a logfile
                        raise err

                # post-process successful and failed senders
                with self.open_transmissions_lock:
                    # all successful transmissions
                    for pid in successful_senders:
                        if pid in self.open_transmissions[worker]:
                            logger.info("Transmission {} completed".format(
                                self.open_transmissions[worker][pid].transmission_id))
                            self.open_transmissions[worker][pid].stop(
                                transmission.Transmission.SUCCESSFUL)
                            del self.open_transmissions[worker][pid]
                        else:
                            logger.error("PID of successful transmission not found")

                    # all unsuccessful transmissions
                    for pid in failed_senders:
                        if pid in self.open_transmissions[worker]:
                            self.open_transmissions[worker][pid].stop(
                                transmission.Transmission.FAILED)
                        del self.open_transmissions[worker][pid]

            time.sleep(self.interval)

    def start_transmission(self, trans):
        """Start a transmission.

        Start the given Transmission and add it to the list of open transmissions.

        Args:
            trans: Transmission to start.
        """
        logger.info("Transmission {} started".format(trans.transmission_id))
        pid = trans.start()

        if not pid:
            logger.error("Failed to start transmission with id {}".format(trans.transmission_id))
            return

        # store pid
        with self.open_transmissions_lock:
            worker = trans.source.worker
            self.open_transmissions[worker][pid] = trans

    def __worker_get_pids_from_file(self, worker, path):
        """Returns a list of PIDs listed in a file on the specified worker node.

        Args:
            worker: worker node to read the file on.
            path: file containing PIDs.

        Returns:
            A list of PIDs specified in the file.
        """
        self.__worker_rotate_file(worker, path)
        content = self.__worker_get_file_content(worker, "%s.0" % path)

        return [int(x) for x in content.split()]

    @staticmethod
    def __worker_get_file_content(worker, path):
        """Returns the content of a file on the specified worker node.

        Args:
            worker: worker node to read file on.
            path: file to read.

        Returns:
            Content of the specified file.
        """
        cat_cmd = "ssh {0} cat {1}".format( worker.hn(), path)

        return subprocess.check_output(cat_cmd.split())

    @staticmethod
    def __worker_rotate_file(worker, path):
        """Rotates a file on the specified worker node.

        The "path" will be moved to "path.0".
        Args:
            worker: worker node rotate file on.
            path: file to rotate.
        """
        mv_cmd = "ssh {0} sudo mv {1} {1}.0 &> /dev/null".format(worker.hn(), path)
        subprocess.check_output(mv_cmd.split())
