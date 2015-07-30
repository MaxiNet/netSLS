#!/usr/bin/env python2

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
import logging.config
logging.config.fileConfig("logging.cfg")

from argparse import ArgumentParser
import os.path

import configuration
import network_simulator
import signal

logger = logging.getLogger(__name__)

def sigint_handler(signum, frame):
    """Signal handler for SIGINT."""
    logger.debug("caught SIGINT")
    simulator = network_simulator.NetworkSimulator.get_instance()
    simulator.stop()


def sigterm_handler(signum, frame):
    """Signal handler for SIGTERM."""
    logger.debug("caught SIGTERM")
    simulator = network_simulator.NetworkSimulator.get_instance()
    simulator.stop()


def main():
    parser = ArgumentParser(
        description="Network simulator for the hadoop coflow simulator")
    parser.add_argument(
        '--config', dest='config_path', help='path to configuration file')
    args = parser.parse_args()

    config_path = args.config_path
    if not config_path:
        if os.path.isfile("network_simulator.cfg"):
            config_path = "network_simulator.cfg"
        elif os.path.isfile(os.path.expanduser("~/.network_simulator.cfg")):
            config_path = os.path.expanduser("~/.network_simulator.cfg")
    configuration.read(config_path)

    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigint_handler)

    simulator = network_simulator.NetworkSimulator.get_instance()
    simulator.start()

if __name__ == "__main__":
    main()
