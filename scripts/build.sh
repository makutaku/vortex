#!/bin/bash
# Modern Python build script

set -e  # Exit on error

echo "Building bc-utils..."

# Output directory for build artifacts
DEST_DIR="./build"

# Clean previous build
if [[ -d "$DEST_DIR" ]]; then
  echo "Removing existing build directory: $DEST_DIR"
  rm -rf "$DEST_DIR"
fi

# Create build structure
mkdir -p "$DEST_DIR/app"

echo "Copying application code..."
cp -r src/bcutils "$DEST_DIR/app/"
cp requirements.txt "$DEST_DIR/app/"

echo "Copying deployment files..."
cp -r docker/* "$DEST_DIR/app/"

echo "Copying configuration..."
mkdir -p "$DEST_DIR/config"
cp config.json "$DEST_DIR/config/"

echo "Build completed successfully!"
echo "Build artifacts in: $DEST_DIR"