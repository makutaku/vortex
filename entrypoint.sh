#!/bin/bash

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
if [ -n "$BARCHART_USERNAME" ]; then
  if [ "$BARCHART_LOGGING_LEVEL" = "debug" ]; then
    echo "$timestamp DEBUG The environment variable BARCHART_USERNAME is set and not empty."
    echo "$timestamp DEBUG Value of BARCHART_USERNAME: $BARCHART_USERNAME"
  fi
else
  echo "$timestamp ERROR The environment variable BARCHART_USERNAME is either not set or empty."
  sleep 60
  exit
fi

if [ -n "$BARCHART_PASSWORD" ]; then
  if [ "$BARCHART_LOGGING_LEVEL" = "debug" ]; then
    echo "$timestamp DEBUG The environment variable BARCHART_PASSWORD is set and not empty."
  fi
else
  echo "$timestamp ERROR The environment variable BARCHART_PASSWORD is either not set or empty."
  sleep 60
  exit
fi


timestamp=$(date +"%Y-%m-%d %H:%M:%S")
if [ "$BARCHART_LOGGING_LEVEL" = "debug" ]; then
  echo "$timestamp DEBUG Saving BARCHART_* environment variables."
fi
declare -p | grep -v -E "_xspecs=" | grep -E "declare -x BARCHART_" > /bc-utils/container.env
if [ "$BARCHART_LOGGING_LEVEL" = "debug" ]; then
  cat /bc-utils/container.env
  echo "$timestamp DEBUG Saved BARCHART_* environment variables."
fi


timestamp=$(date +"%Y-%m-%d %H:%M:%S")
echo "$timestamp DEBUG Log file truncated at Docker entrypoint" > "$BARCHART_OUTPUT_DIR/bc_utils.log"
echo "$timestamp DEBUG Log file truncated at Docker entrypoint" > "$BARCHART_OUTPUT_DIR/ping.log"

cd /bc-utils || exit


if [ "$RUN_ON_STARTUP" = "True" ]; then
  echo "$timestamp INFO Running script on startup - RUN_ON_STARTUP environment variable is set to 'True'."
  ./run_bc_utils.sh 2>&1 | tee -a "$BARCHART_OUTPUT_DIR/bc_utils.log"
else
  echo "$timestamp INFO Skipping running script on startup. To run on start up, set RUN_ON_STARTUP environment variable to 'True'."
fi


timestamp=$(date +"%Y-%m-%d %H:%M:%S")
if [ "$BARCHART_LOGGING_LEVEL" = "debug" ]; then
  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "$timestamp DEBUG Scheduling cron jobs."
fi
# Start cron in the foreground and log to /dev/stdout
#cron -f -L /dev/stdout
cron -L /dev/stdout
echo "$timestamp INFO Scheduled cron jobs"


# Run forever
tail -f /dev/null

