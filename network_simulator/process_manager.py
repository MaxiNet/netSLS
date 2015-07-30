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
import ssh_tools
import utils

logger = logging.getLogger(__name__)


class ProcessManager(object):
    """Watches the execution of processes on MaxiNet nodes.

    The ProcessManager polls all MaxiNet workers for the state of invoked
    background processes. When a remote process terminates, a callback on the
    corresponding Process object is performed. Additionally, if the process
    terminated with an exit code other than 0, the process's stdout and stderr
    are logged.

    Attributes:
        __interval: Polling interval in ms.
        __running_processes: Mapping of MaxiNet workers to running processes.
    """

    def __init__(self, interval):
        self.__thread = threading.Thread(target=self.run)

        self.__interval = interval

        self.__running_processes = dict()
        self.__running_processes_lock = threading.Lock()
        self.__stop = threading.Event()

    def start(self):
        self.__thread.start()

    def stop(self):
        """Stops the thread and waits for termination."""
        self.__stop.set()
        if self.__thread.isAlive():
            self.__thread.join()

    def run(self):
        self.__stop.clear()

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
                    logger.debug("Failed processes {!s}".format(failed_processes))
                except subprocess.CalledProcessError:
                    # This possible, if file pids_failed does not yet exist
                    pass

                # For every failed process retrieve and print processes's output from worker
                for pid in failed_processes:
                    try:
                        cat_cmd = "cat {1}".format(
                            worker.hn(),
                            os.path.join(configuration.get_worker_working_directory(),
                                         "processes", str(pid)))
                        logfile_content = ssh_tools.worker_ssh(worker, cat_cmd)
                        logfile_formatted = utils.indent(logfile_content, 2)

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

            time.sleep(self.__interval)

    def start_process(self, proc):
        """Starts the given process and adds it to the list of running processes.

        Args:
            proc: Process to start.

        Returns:
            True if the process started successfully, False otherwise.
        """
        if not proc.start():
            return False

        with self.__running_processes_lock:
            if proc.get_worker() not in self.__running_processes:
                self.__running_processes[proc.get_worker()] = dict()
            self.__running_processes[proc.get_worker()][proc.pid] = proc

        return True

    def reset(self):
        """Reset the process manager.

        Kill all processes still running and clear the list.
        """
        self.__kill_all_processes()
        self.__running_processes = dict()
        self.__thread = threading.Thread(target=self.run)

    def kill(self, pid):
        """Kill running process with the given PID.

        Args:
            pid: PID of the process to kill.
        """
        with self.__running_processes_lock:
            if not pid in self.__running_processes:
                return
            self.__running_processes[pid].kill()
            del self.__running_processes[pid]

    def __kill_all_processes(self):
        """Kill all processes that are stil listed as running."""
        with self.__running_processes_lock:
            if len(self.__running_processes) == 0:
                return
            for worker, processes in self.__running_processes.items():
                kill_cmd = "kill -9"
                for pid in processes.keys():
                    kill_cmd += " {}".format(pid)
                ssh_tools.worker_ssh(worker, kill_cmd)

    @staticmethod
    def __worker_get_pids_from_file(worker, path):
        """Returns a list of PIDs listed in a file on the specified worker node.

        Args:
            worker: Worker node to read the file on.
            path: File containing PIDs.

        Returns:
            A list of PIDs specified in the file.
        """
        # Rotate the pid file, if exists
        mv_cmd = "mv {1} {1}.0 &> /dev/null".format(worker.hn(), path)
        ssh_tools.worker_ssh(worker, mv_cmd)

        # get rotated file's content
        cat_cmd = "cat {1}".format(worker.hn(), "%s.0" % path)
        content = ssh_tools.worker_ssh(worker, cat_cmd)

        return [int(x) for x in content.split()]
