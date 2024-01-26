#!/bin/bash

echo "Saving environment variables passed to the container."
declare -p | grep -E 'BARCHART_PASSWORD|BARCHART_USERNAME|BARCHART_DRY_RUN|BARCHART_END_YEAR|BARCHART_START_YEAR|BARCHART_OUTPUT_DIR' > ./container.env

#echo "Executing commands passed to the container."
#exec "$@"

cd /bc-utils || exit

./run_bc_utils.sh 2>&1 | tee -a ./run_bc_utils.log

cron -f
