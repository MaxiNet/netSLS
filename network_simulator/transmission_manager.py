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
import subprocess
import threading
import time

import network_simulator
import transmission

logger = logging.getLogger(__name__)

class TransmissionManager(threading.Thread):
    def __init__(self, interval):
        threading.Thread.__init__(self)

        self._stop = threading.Event()

        self.interval = interval
        self.open_transmissions_lock = threading.Lock()
        self.open_transmissions = dict()
        self.new_transmissions = dict()

    def stop(self):
        self._stop.set()

    def run(self):
        for worker in network_simulator.NetworkSimulator.get_instance().cluster.worker:
            self.open_transmissions[worker] = dict()
            self.new_transmissions[worker] = dict()

        while not self._stop.isSet():
            for worker in network_simulator.NetworkSimulator.get_instance().cluster.worker:
                # find all running senders
                ps_cmd = "ssh %s pgrep -f %s" % (worker.hn(), "[t]cp_send")
                running_senders = []
                try:
                    result = subprocess.check_output(ps_cmd.split())
                    running_senders = [int(x) for x in result.split()]
                    logger.debug("Running senders {}".format(str(running_senders)))
                except subprocess.CalledProcessError:
                    # this is possible, if pgrep result is empty
                    pass

                # get list of successfully completed senders
                completed_senders = ""
                try:
                    mv_cmd = "ssh %s sudo mv /tmp/completed_senders /tmp/completed_senders.0 &> /dev/null"\
                             % worker.hn()
                    subprocess.check_output(mv_cmd.split())
                    cat_cmd = "ssh %s cat /tmp/completed_senders.0" % worker.hn()
                    completed_senders = [int(x) for x in
                                         subprocess.check_output(cat_cmd.split()).split()]
                    logger.debug("Completed senders {}".format(str(completed_senders)))
                except subprocess.CalledProcessError:
                    # this possible, if file does not yet exist
                    pass

                with self.open_transmissions_lock:
                    # all successful transmissions
                    for pid in completed_senders:
                        if pid in self.new_transmissions[worker]:
                            logger.info("Transmission {} completed".format(
                                        self.new_transmissions[worker][pid].transmission_id))
                            self.new_transmissions[worker][pid].stop(
                                transmission.Transmission.SUCCESSFUL)
                            del self.new_transmissions[worker][pid]
                        elif pid in self.open_transmissions[worker]:
                            logger.info("Transmission {} completed".format(
                                self.open_transmissions[worker][pid].transmission_id))
                            self.open_transmissions[worker][pid].stop(
                                transmission.Transmission.SUCCESSFUL)
                            del self.open_transmissions[worker][pid]
                        else:
                            logger.error("PID of completed transmission not found")

                    # all unsuccessful transmissions
                    for pid, tm in self.open_transmissions[worker].items():
                        if pid in running_senders:
                            continue
                        logger.error("Transmission with PID {} failed".format(pid))
                        tm.stop(transmission.Transmission.FAILED)
                        del self.open_transmissions[worker][pid]

            # move new transmissions to open transmissions
            for worker in self.new_transmissions.keys():
                for k, v in self.new_transmissions[worker].items():
                    self.open_transmissions[worker][k] = v
                self.new_transmissions[worker] = dict()

            time.sleep(self.interval)

    def start_transmission(self, trans):
        logger.info("Transmission {} started".format(trans.transmission_id))
        pid = trans.start()

        if not pid:
            logger.error("Failed to start transmission with id {}".format(trans.transmission_id))
            return

        # store pid
        with self.open_transmissions_lock:
            worker = trans.source.worker
            self.new_transmissions[worker][pid] = trans
