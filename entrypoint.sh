#!/bin/bash

timestamp() {
  date +"%Y-%m-%d %H:%M:%S"
}

# Function to log diagnostic information
log_diagnostics() {
    echo "Diagnostic Info:"
    echo "- User ID (UID): $(id -u)"
    echo "- Group ID (GID): $(id -g)"
    echo "- Directory Permissions: $(ls -ld "$BARCHART_OUTPUT_DIR" | awk '{print $1}')"
    echo "- Directory Owner: $(ls -ld "$BARCHART_OUTPUT_DIR" | awk '{print $3}')"
    echo "- Directory Group: $(ls -ld "$BARCHART_OUTPUT_DIR" | awk '{print $4}')"
    echo "- Disk Usage of Output Directory's Disk: $(df -h "$BARCHART_OUTPUT_DIR" | tail -1 | awk '{print "Used: " $3 " Available: " $4 " Use%: " $5}')"
    echo "- Mounted File System Details: $(df -hT "$BARCHART_OUTPUT_DIR" | tail -1)"
#    echo "- Effective Permissions (Access Control List):"
#    getfacl "$BARCHART_OUTPUT_DIR" 2>/dev/null
#    echo "- SELinux Context: $(ls -Zd "$BARCHART_OUTPUT_DOMAIN" | awk '{print $1}')"
    echo "- Filesystem Mount Options: $(mount | grep " $BARCHART_OUTPUT_DIR " | awk '{print $NF}')"
    echo "- Inode Usage: $(df -i "$BARCHART_OUTPUT_DIR" | tail -1 | awk '{print "Used: " $3 " Free: " $4 " Use%: " $5}')"
#    echo "- Recent Disk Errors (dmesg):"
#    dmesg | grep -i "error"
}

# Function to check write permissions in the output directory
check_write_permission() {
  local testfile="$BARCHART_OUTPUT_DIR/.test_write_permissions"
  if ! touch "$testfile" 2>/dev/null; then
    echo "$(timestamp) ERROR Unable to write to $BARCHART_OUTPUT_DIR."
    log_diagnostics
    exit 1
  else
    if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
      echo "$(timestamp) DEBUG Write permission test passed for $BARCHART_OUTPUT_DIR."
      log_diagnostics
    fi
  fi
  rm -f "$testfile"
}

# Check environment variable is set and directory is writable
if [ -n "$BARCHART_OUTPUT_DIR" ]; then
  check_write_permission
else
  echo "$(timestamp) ERROR The environment variable BARCHART_OUTPUT_DIR is not set or empty."
  sleep 60
  exit 1
fi

timestamp=$(date +"%Y-%m-%d %H:%M:%S")

if [ -n "$BC_UTILS_REPO_DIR" ]; then
  if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
    echo "$timestamp DEBUG The environment variable BC_UTILS_REPO_DIR is set to $BC_UTILS_REPO_DIR."
  fi
else
  echo "$timestamp ERROR The environment variable BC_UTILS_REPO_DIR is either not set or empty."
  sleep 60
  exit
fi

#if [ -n "$BARCHART_USERNAME" ]; then
#  if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
#    echo "$timestamp DEBUG The environment variable BARCHART_USERNAME is set to $BARCHART_USERNAME"
#  fi
#else
#  echo "$timestamp ERROR The environment variable BARCHART_USERNAME is either not set or empty."
#  sleep 60
#  exit
#fi
#
#if [ -n "$BARCHART_PASSWORD" ]; then
#  if [ "$BARCHART_LOGGING_LEVEL" = "DEBUG" ]; then
#    echo "$timestamp DEBUG The environment variable BARCHART_PASSWORD is set and not empty."
#  fi
#else
#  echo "$timestamp ERROR The environment variable BARCHART_PASSWORD is either not set or empty."
#  sleep 60
#  exit
#fi

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

# Function to rotate logs
rotate_log() {
  local log_file=$1
  local backup_file="${log_file}.previous"

  # Check if the log file exists and is not empty
  if [ -f "$log_file" ] && [ -s "$log_file" ]; then
    # Move the current log to a backup file
    mv "$log_file" "$backup_file"
    # Touch the new log file to ensure it exists
    touch "$log_file"
    echo "$(date +"%Y-%m-%d %H:%M:%S") INFO Log rotated for $log_file"
  fi
}

# Rotate bc_utils.log and ping.log
rotate_log "$BARCHART_OUTPUT_DIR/bc_utils.log"
rotate_log "$BARCHART_OUTPUT_DIR/ping.log"

timestamp=$(date +"%Y-%m-%d %H:%M:%S")

if [ "$RUN_ON_STARTUP" = "True" ]; then
  echo "$timestamp INFO Running script on startup - RUN_ON_STARTUP environment variable is set to 'True'."
  "$BC_UTILS_REPO_DIR/run_bc_utils.sh" 2>&1 | tee -a "$BARCHART_OUTPUT_DIR/bc_utils.log"
else
  echo "$timestamp INFO Skipping running script on startup. To run on start up, set RUN_ON_STARTUP environment variable to 'True'."
fi


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
