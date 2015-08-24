#!/usr/bin/env bash

function print_usage {
  echo -e "usage: sls.sh TraceFile"
  echo -e
  echo -e "Starts SLS with the given trace file."
}

if [[ -z $1 ]]; then
  print_usage
  exit 1
fi

TRACE_FILE=$(realpath $1)

if [[ ! -f ${TRACE_FILE} ]]; then
  echo "File not found: ${TRACE_FILE}"
  print_usage
  exit 1
fi

cd sls

OUTPUT_DIRECTORY="/tmp/sls"
mkdir -p ${OUTPUT_DIRECTORY}

ARGS="-inputsls ${TRACE_FILE}"
ARGS+=" -output ${OUTPUT_DIRECTORY}"
ARGS+=" -printsimulation"

mvn exec:java -Dexec.args="${ARGS}"
