#!/bin/bash

## Function to check environment variables and issue warnings
#check_env_var() {
#  local var_name="$1"
#
#  # Check if the variable is set
#  if [ -z "${!var_name}" ]; then
#    echo "Error: $var_name is not set. Please set this environment variable." >&2
#
#    # Check if running as superuser and the variable is missing
#    if [ "$(id -u)" -eq 0 ]; then
#      echo "Notice: Running as superuser. If $var_name is set in your usual environment, consider using 'sudo -E' to preserve it." >&2
#    fi
#
#    exit 1
#  fi
#}

# Define the function to process each .env file
process_env_file() {
  local input_file="$1"
  local output_dir="$2"

  # Extract filename from the full path
  local filename=$(basename "$input_file")

  # Output file path
  local output_file="$output_dir/$filename"

  echo "Processing file: $input_file" >&2
  echo "Outputting to: $output_file" >&2

  # Interpolate variables into the output file from the specified environment file
  ./scripts/interpolate_vars.sh "$input_file" "$output_file" >&2
  if [ $? -ne 0 ]; then
    echo "Error: Failed to interpolate variables in $input_file" >&2
    exit 1
  fi

  echo "$output_file"
}


echo "Building bc-utils"

## Check for command-line argument and use it to override ENV if provided
#if [ ! -z "$1" ]; then
#  ENV="$1"
#elif [ -z "$ENV" ]; then
#  echo "Error: ENV variable is not set and no command-line argument provided."
#  exit 1
#fi


## Check both VAULT_ADDR and VAULT_TOKEN
#check_env_var "VAULT_ADDR"
#check_env_var "VAULT_TOKEN"

# Output directory for processed files
DEST_DIR="./build"
if [[ -d "$DEST_DIR" ]]; then
  echo "Removing existing build directory: $DEST_DIR"
  rm -rf "$DEST_DIR"
fi
mkdir -p "$DEST_DIR"


echo "Generating env files"

# Directory containing source environment files
ENV_DIR="./env_files"

# Create output directory if it does not exist
env_output_path="$DEST_DIR"/env_files
mkdir -p "$env_output_path"

# Process all .env files in the directory
for env_file in "$ENV_DIR"/*.env; do
  output_env_file=$(process_env_file "$env_file" "$env_output_path")
done

echo "Copying bc-utils"
cp -r ./bcutils  "$DEST_DIR"/
cp ./cronfile \
  ./requirements.txt \
  ./entrypoint.sh \
  ./run_bc_utils.sh \
  ./ping.sh \
  "$DEST_DIR"/

echo "Copying configs"
CONFIG_PROJECT_NAME="pysystemtrade_config"
CONFIG_PROJECT_DIR="../$CONFIG_PROJECT_NAME"
mkdir -p "$DEST_DIR/configs"
cp -r "$CONFIG_PROJECT_DIR/build/bc-utils/." "$DEST_DIR/configs/"

echo "DONE!"