#!/bin/bash

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
mkdir -p "$DEST_DIR"/app
cp -r ./bcutils  "$DEST_DIR"/app
cp ./cronfile \
  ./requirements.txt \
  ./entrypoint.sh \
  ./run_bc_utils.sh \
  ./ping.sh \
  "$DEST_DIR"/app

echo "Copying configs"
CONFIG_PROJECT_NAME="pysystemtrade_config"
CONFIG_PROJECT_DIR="../$CONFIG_PROJECT_NAME"
mkdir -p "$DEST_DIR/configs"
cp -r "$CONFIG_PROJECT_DIR/build/bc-utils/." "$DEST_DIR/configs/"

echo "DONE!"