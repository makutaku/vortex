#!/bin/bash

timestamp=$(date +"%Y-%m-%d %H:%M:%S")

if [ -n "$BC_UTILS_REPO_DIR" ]; then
  if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
    echo "$timestamp DEBUG The environment variable BC_UTILS_REPO_DIR is set and not empty."
  fi
else
  echo "$timestamp ERROR The environment variable BC_UTILS_REPO_DIR is either not set or empty."
  sleep 60
  exit
fi

if [ -n "$BARCHART_USERNAME" ]; then
  if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
    echo "$timestamp DEBUG The environment variable BARCHART_USERNAME is set and not empty."
    echo "$timestamp DEBUG Value of BARCHART_USERNAME: $BARCHART_USERNAME"
  fi
else
  echo "$timestamp ERROR The environment variable BARCHART_USERNAME is either not set or empty."
  sleep 60
  exit
fi

if [ -n "$BARCHART_PASSWORD" ]; then
  if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
    echo "$timestamp DEBUG The environment variable BARCHART_PASSWORD is set and not empty."
  fi
else
  echo "$timestamp ERROR The environment variable BARCHART_PASSWORD is either not set or empty."
  sleep 60
  exit
fi

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
  echo "$timestamp DEBUG Saving BARCHART_* environment variables."
fi
declare -p | grep -v -E "_xspecs=" | grep -E "declare -x BARCHART_" > "$BC_UTILS_REPO_DIR/container.env"
if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
  cat "$BC_UTILS_REPO_DIR/container.env"
  echo "$timestamp DEBUG Saved BARCHART_* environment variables."
fi

cd "$BC_UTILS_REPO_DIR" || exit

mv -f "$BARCHART_OUTPUT_DIR/bc_utils.log" "$BARCHART_OUTPUT_DIR/bc_utils.previous.log"
mv -f "$BARCHART_OUTPUT_DIR/ping.log" "$BARCHART_OUTPUT_DIR/ping.previous.log"
rm "$BARCHART_OUTPUT_DIR/bc_utils.log"
rm "$BARCHART_OUTPUT_DIR/ping.log"

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
if [ "$RUN_ON_STARTUP" = "True" ]; then
  echo "$timestamp INFO Running script on startup - RUN_ON_STARTUP environment variable is set to 'True'."
  "$BC_UTILS_REPO_DIR/run_bc_utils.sh" 2>&1 | tee -a "$BARCHART_OUTPUT_DIR/bc_utils.log"
else
  echo "$timestamp INFO Skipping running script on startup. To run on start up, set RUN_ON_STARTUP environment variable to 'True'."
fi

timestamp=$(date +"%Y-%m-%d %H:%M:%S")
if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
  timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  echo "$timestamp DEBUG Scheduling cron jobs."
fi
# Start cron in the foreground and log to /dev/stdout
#cron -f -L /dev/stdout
cron -L /dev/stdout
echo "$timestamp INFO Scheduled cron jobs"

# Run forever
tail -f /dev/null
