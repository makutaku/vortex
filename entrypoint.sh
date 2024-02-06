#!/bin/bash

echo "Saving environment variables passed to the container."
#declare -p | grep -E 'LOGGING_LEVEL|BARCHART_PASSWORD|BARCHART_USERNAME|BARCHART_DRY_RUN|BARCHART_END_YEAR|BARCHART_START_YEAR|BARCHART_INPUT_DIR|BARCHART_OUTPUT_DIR|DAILY_DOWNLOAD_LIMIT|RANDOM_SLEEP_IN_SEC' > ./container.env

declare -p \
    | grep -E 'LOGGING_LEVEL' \
    | grep -E 'BARCHART_PASSWORD' \
    | grep -E 'BARCHART_USERNAME' \
    | grep -E 'BARCHART_DRY_RUN' \
    | grep -E 'BARCHART_END_YEAR' \
    | grep -E 'BARCHART_START_YEAR' \
    | grep -E 'BARCHART_INPUT_DIR' \
    | grep -E 'BARCHART_OUTPUT_DIR' \
    | grep -E 'DAILY_DOWNLOAD_LIMIT' \
    | grep -E 'RANDOM_SLEEP_IN_SEC' \
    > ./container.env

#echo "Executing commands passed to the container."
#exec "$@"

cd /bc-utils || exit

./run_bc_utils.sh 2>&1 | tee -a "$BARCHART_OUTPUT_DIR/bc_utils.log"

echo "Starting cron ..."
# Start cron in the foreground and log to /dev/stdout
cron -f -L /dev/stdout


echo "Sleeping for a minute after cron has exited..."
sleep 60
