#!/usr/bin/env python2

from argparse import ArgumentParser

import configuration
import network_simulator

def main():
    parser = ArgumentParser(description="Network simulator for the hadoop \
coflow simulator")
    parser.add_argument('--config', dest='config_path',
            help='path to configuration file')
    args = parser.parse_args()

    configuration.read(args.config_path)

    simulator = network_simulator.NetworkSimulator.get_instance()
    simulator.start()

if __name__ == "__main__":
    main()

