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

from argparse import ArgumentParser

import configuration
import network_simulator


def main():
    parser = ArgumentParser(
        description="Network simulator for the hadoop coflow simulator")
    parser.add_argument(
        '--config', dest='config_path', help='path to configuration file')
    args = parser.parse_args()

    configuration.read(args.config_path)

    simulator = network_simulator.NetworkSimulator.get_instance()
    simulator.start()

if __name__ == "__main__":
    main()

