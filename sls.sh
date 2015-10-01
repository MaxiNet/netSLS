#!/usr/bin/env bash

function print_usage {
  echo -e "usage: sls.sh TraceFile [TopologyFile]"
  echo -e
  echo -e "Starts SLS with the given trace file."
}

if [[ -z $1 ]]; then
  print_usage
  exit 1
fi

TRACE_FILE=$(realpath $1)
TOPOLOGY_FILE=""
if [[ ! -z $2 ]]; then
  TOPOLOGY_FILE=$(realpath $2)
fi

if [[ ! -f ${TRACE_FILE} ]]; then
  echo "Job Trace File not found: ${TRACE_FILE}"
  print_usage
  exit 1
fi

if [[ ! -f ${TOPOLOGY_FILE} ]]; then
  echo "Topology File not found: ${TRACE_FILE}"
  print_usage
  exit 1
fi

cd sls

OUTPUT_DIRECTORY="/tmp/sls"
mkdir -p ${OUTPUT_DIRECTORY}

ARGS="-inputsls ${TRACE_FILE}"
if [[ ! -z ${TOPOLOGY_FILE} ]]; then
  ARGS+=" -nodes ${TOPOLOGY_FILE}"
fi
ARGS+=" -output ${OUTPUT_DIRECTORY}"
ARGS+=" -printsimulation"

mvn exec:java -Dexec.args="${ARGS}"
