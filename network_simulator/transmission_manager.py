import subprocess
import threading
import time

import configuration
import network_simulator
import transmission

class TransmissionManager(threading.Thread):
    def __init__(self, interval):
        threading.Thread.__init__(self)

        self.interval = interval
        self.open_transmissions_lock = threading.Lock()
        self.open_transmissions = dict()
        self.new_transmissions = dict()

    def run(self):
        for worker in network_simulator.NetworkSimulator.get_instance().cluster.worker:
            self.open_transmissions[worker] = dict()
            self.new_transmissions[worker] = dict()

        while True:
            for worker in network_simulator.NetworkSimulator.get_instance().cluster.worker:
                #print("TM: querying worker %s" % worker.hn())
                # find all running senders
                ps_cmd = "ssh %s pgrep -f %s" % (worker.hn(), "tcp_send")
                running_senders = []
                try:
                    running_senders = [int(x) for x in \
                            subprocess.check_output(ps_cmd.split()).split()]
                    print("TM: running senders:")
                    print(running_senders)
                except Exception:
                    # this possible, if pgrep result is empty
                    pass

                # get list of successfully completed senders
                completed_senders = ""
                try:
                    mv_cmd = "ssh %s sudo mv /tmp/completed_senders /tmp/completed_senders.0 &> /dev/null" \
                            % worker.hn()
                    subprocess.check_output(mv_cmd.split())
                    cat_cmd = "ssh %s cat /tmp/completed_senders.0" % worker.hn()
                    completed_senders = [int(x) for x in \
                            subprocess.check_output(cat_cmd.split()).split()]
                    print("TM: completed senders")
                    print(completed_senders)
                except Exception:
                    # this possible, if file does not yet exist
                    pass

                with self.open_transmissions_lock:
                    # all successful transmissions
                    for pid in completed_senders:
                        if pid in self.new_transmissions[worker]:
                            self.new_transmissions[worker][pid].stop( \
                                    transmission.Transmission.SUCCESSFUL)
                        elif pid in self.open_transmissions[worker]:
                            self.open_transmissions[worker][pid].stop( \
                                    transmission.Transmission.SUCCESSFUL)
                            del self.open_transmissions[worker][pid]
                        else:
                            print("TM: PID of completed transmission not found")

                    # all unsuccessful transmissions
                    for pid, tm in self.open_transmissions[worker].items():
                        if pid in running_senders:
                            continue
                        print("TM: transmission with pid %i failed" % pid)
                        tm.stop(transmission.Transmission.FAILED)
                        del self.open_transmissions[worker][pid]

            # move new transmissions to open transmissions
            for worker in self.new_transmissions.keys():
                for k, v in self.new_transmissions[worker].items():
                    self.open_transmissions[worker][k] = v
                self.new_transmissions[worker] = dict()

            time.sleep(self.interval)

    def start_transmission(self, transmission):
        print("TM: start_transmission %i" % transmission.transmission_id)
        pid = transmission.start()

        if not pid:
            print("TM: Error starting transmission")
            return

        # store pid
        with self.open_transmissions_lock:
            worker = transmission.source.worker
            self.new_transmissions[worker][pid] = transmission
