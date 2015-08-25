#!/usr/bin/env bash

cd sls
mvn compile

if [[ $? != "0" ]]; then
  echo "ERROR: Failed to compile sls"
  exit 1
fi

cd ../network_emulator
./setup_virtualenv.sh
