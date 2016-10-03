# netSLS
netSLS combines the Hadoop Scheduler Load Simulator (SLS) and the network
emulator MaxiNet to emulate Hadoop network traffic based on artificial or real
world job traces.

## Quickstart
Download and start the MaxiNet virtual machine images from
http://maxinet.github.io. The VMs subsequently will be referred to by their
hostnames, "worker1" and "worker2".

First, upgrade Pyro4 on both VMs:
```
sudo pip install --upgrade Pyro4
```

Before proceeding, follow the instructions on
http://maxinet.github.io/#quickstart to start and test your MaxiNet setup.

Now install netSLS on worker1:
```
sudo apt-get update
sudo apt-get install openjdk-7-jdk maven virtualenv libzmq-dev python-dev
git clone https://github.com/MaxiNet/netSLS.git
cd netSLS
./setup.sh
```

The netSLS network emulator requires ssh access to all MaxiNet workers. Add the
following content to ~/.ssh/config
```
Host worker2
  HostName 192.168.0.2
```
and distribute an ssh key to all workers:
```
ssh-keygen -f ~/.ssh/id_rsa -N ""
ssh-copy-id worker1
ssh-copy-id worker2
```

Start the network emulator:
```
cd ~/netSLS
./network_emulator.sh
```

You might want to check if the network emulator works properly first:
```
cd ~/netSLS/network_emulator
env/bin/python test/test_all_rpc.py
```

Now start sls with a demo trace:
```
cd ~/netSLS
./sls.sh generator/medium.json
```

## Remote Setup
The MaxiNet API allows to run the network emulator and sls on hosts different
from the MaxiNet workers. Assuming the MaxiNet setup from above and the netSLS
repository is cloned into ~/netSLS on the hosts running the network emulator and
sls.

### Network Emulator
* Enable ssh access to all workers. Add the following entries to ~/.ssh/config
  (adapt addresses accordingly)
```
Host worker1
  User maxinet
  HostName a.b.c.d
Host worker2
  User maxinet
  HostName a.b.c.e
```
and copy the ssh key to all workers.

* Copy the MaxiNet configuration:
```
scp worker1:/etc/MaxiNet.cfg ~/netSLS/network_emulator/MaxiNet.cfg
```
Make sure, that the addresses in MaxiNet.cfg match the addresses in
~/.ssh/config. Otherwise modify the workers' and the copied MaxiNet.cfg file to
match these addresses. MaxiNet needs to be restarted at this point.

* Create a python virtualenv and install dependencies (might require additional
  packages to be installed, cf. Quickstart):
```
cd ~/netSLS/network_emulator
./setup_virtualenv.sh
```

* Start the network emulator
```
cd ~/netSLS
./network_emulator.sh
```

### SLS
* Build sls:
```
cd ~/netSLS/sls
mvn compile
```

* If sls runs on a host different from the host running the network emulator the
  configuration needs to be changed. In
  ~/netSLS/sls/hadoop/etc/hadoop/sls-runner.xml change the properties
  `yarn.sls.networkemulator.zmq.url` and `yarn.sls.networkemulator.rpc.url` to
  match the network emulator's address.

* Start sls
```
cd ~/netSLS
./sls.sh generator/medium.json
```

## Development/IDE
When modifying sls using an IDE, it is recommended to use IntelliJ IDEA rather
than Eclipse (due to problems with the Eclipse Maven plugin).

Simply import the sls folder as Maven project and add the folder
hadoop/etc/hadoop to the project's classpath.

## Troubleshooting
netSLS may fail due to various reasons. Most likely there is a version mismatch
between the system's and network emulator's versions of MaxiNet or Pyro4.

* Update system's MaxiNet:
```
cd ~/MaxiNet
git pull
sudo make install
```

* Update system's Pyro4:
```
sudo pip install --upgrade Pyro4
```

* Update network emulator dependencies:
```
cd ~/netSLS/network_emulator
./setup_virtualenv.sh
```
