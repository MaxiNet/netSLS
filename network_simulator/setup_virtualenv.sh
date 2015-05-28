#!/usr/bin/env bash

virtualenv --python=python2.7 env

# Switch to env
source $(pwd)/env/bin/activate

pip install pyzmq tinyrpc gevent requests werkzeug wsgiref

# install mininet
cd /tmp
rm -rf mininet
git clone https://github.com/mininet/mininet.git
cd mininet
git checkout 2.2.0
python setup.py install
cd ../
rm -rf mininet

# install MaxiNet
cd /tmp
rm -rf MaxiNet
git clone https://github.com/MaxiNet/MaxiNet.git
cd MaxiNet
git checkout v1.0
cat setup.py | sed "s/\"sudo\",//" > setup.py.new
python setup.py.new install
cd ../
rm -rf MaxiNet
