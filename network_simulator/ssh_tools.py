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

logger = logging.getLogger(__name__)


def worker_ssh(worker, command):
    """Executes the given command on the given MaxiNet worker via ssh.

    All commands are executed with root permissions by default to prevent
    problems with MaxiNet.

    Args:
        worker: MaxiNet Worker to ssh to.
        command: Command to execute.

    Returns:
        Output of the executed command.
    """
    logger.debug("Executing \"{0}\" on worker {1}".format(command, worker.hn()))
    ssh_command = "ssh {0} sudo {1}".format(worker.hn(), command)

    return subprocess.check_output(ssh_command.split())


def copy_to_worker(worker, source, destination):
    """Copies data from local source to destination directory on the given
    worker via scp.

    Args:
        worker: MaxiNet worker to copy data to.
        source: Local source.
        destination: Destination directory on MaxiNet worker.
    """
    logger.debug("Copying {0} to {1}:{2}".format(source, worker.hn(), destination))
    # Copy to worker:/tmp/, then move to destination (prevents permission issues)
    scp_command = "scp -r {0} {1}:/tmp/".format(source, worker.hn())
    result = subprocess.check_output(scp_command.split())
    if len(result) > 0:
        logger.error("Failed to execute {0}:\n{1}".format(scp_command, result))

    mkdir_command = "mkdir -p {0}".format(destination)
    worker_ssh(worker, mkdir_command)
    mv_command = "mv /tmp/{0} {1}/".format(os.path.basename(source), destination)
    result = worker_ssh(worker, mv_command)
    if len(result) > 0:
        logger.error("Failed to execute {0}:\n{1}".format(mv_command, result))
