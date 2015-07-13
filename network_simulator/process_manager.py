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
import process

logger = logging.getLogger(__name__)


class ProcessManager(threading.Thread):
    """Watches the execution of processes on MaxiNet nodes.

    The ProcessManager polls all MaxiNet workers for the state of invoked
    background processes. When a remote process terminates, a callback on the
    corresponding Process object is performed. Additionally, if the process
    terminated with an exit code other than 0, the process's stdout and stderr
    are logged.

    Attributes:
        _interval: Polling interval in ms.
        __running_processes: Mapping of MaxiNet workers to running processes.
    """

    def __init__(self, interval):
        threading.Thread.__init__(self)

        self._interval = interval

        self.__running_processes = dict()
        self.__running_processes_lock = threading.Lock()
        self.__stop = threading.Event()

    def stop(self):
        self.__stop.set()

    def run(self):
        for worker in network_simulator.NetworkSimulator.get_instance().cluster.worker:
            self.__running_processes[worker] = dict()

        while not self.__stop.isSet():
            for worker in network_simulator.NetworkSimulator.get_instance().cluster.worker:
                successful_processes = []
                try:
                    successful_processes = self.__worker_get_pids_from_file(
                        worker,
                        os.path.join(configuration.get_worker_working_directory(), "pids_successful"))
                    logger.debug("Successful processes {!s}".format(successful_processes))
                except subprocess.CalledProcessError:
                    # This possible, if file pids_successful does not yet exist
                    pass

                failed_processes = []
                try:
                    failed_processes = self.__worker_get_pids_from_file(
                        worker,
                        os.path.join(configuration.get_worker_working_directory(), "pids_failed"))
                    logger.debug("Failed processes {!s}".format(successful_processes))
                except subprocess.CalledProcessError:
                    # This possible, if file pids_failed does not yet exist
                    pass

                # For every failed process retrieve and print processes's output from worker
                for pid in failed_processes:
                    try:
                        logfile_content = self.__worker_get_file_content(
                            worker,
                            os.path.join(configuration.get_worker_working_directory(), "processes", str(pid)))
                        logfile_formatted = ""
                        for line in logfile_content.splitlines():
                            logfile_formatted += "\t\t%s\n" % line

                        logger.error("Process with PID {0} failed:\n{1}".format(
                            pid, logfile_formatted))
                    except subprocess.CalledProcessError, err:
                        logger.error("Failed to retrieve logfile for process with PID %i" % pid)
                        # Not allowed, as every daemonized process writes to a logfile
                        raise err

                # post-process successful and failed processes
                with self.__running_processes_lock:
                    # all successful transmissions
                    for pid in successful_processes:
                        if pid in self.__running_processes[worker]:
                            self.__running_processes[worker][pid].call_terminated(
                                process.Process.SUCCESSFUL)
                            del self.__running_processes[worker][pid]
                        else:
                            logger.error("PID of successful transmission not found")

                    # all unsuccessful transmissions
                    for pid in failed_processes:
                        if pid in self.__running_processes[worker]:
                            self.__running_processes[worker][pid].call_terminated(
                                process.Process.FAILED)
                            del self.__running_processes[worker][pid]

            time.sleep(self._interval)

    def start_process(self, proc):
        """Starts the given process and adds it to the list of running processes.

        Args:
            proc: Process to start.
        """
        pid = proc.start()
        with self.__running_processes_lock:
            if proc.get_worker() not in self.__running_processes:
                self.__running_processes[proc.get_worker()] = dict()
            self.__running_processes[proc.get_worker()][pid] = proc

    def __worker_get_pids_from_file(self, worker, path):
        """Returns a list of PIDs listed in a file on the specified worker node.

        Args:
            worker: Worker node to read the file on.
            path: File containing PIDs.

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
            worker: Worker node to read file on.
            path: File to read.

        Returns:
            Content of the specified file.
        """
        cat_cmd = "ssh {0} cat {1}".format(worker.hn(), path)

        return subprocess.check_output(cat_cmd.split())

    @staticmethod
    def __worker_rotate_file(worker, path):
        """Rotates a file on the specified worker node.

        The "path" will be moved to "path.0".
        Args:
            worker: Worker node rotate file on.
            path: File to rotate.
        """
        mv_cmd = "ssh {0} sudo mv {1} {1}.0 &> /dev/null".format(worker.hn(), path)
        subprocess.check_output(mv_cmd.split())
