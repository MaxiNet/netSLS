#!/usr/bin/env bash

cd sls
mvn compile

cd ../network_simulator
./setup_virtualenv.sh
