#!/bin/bash
# Debug script for container issues

echo "Building test container..."
docker build -t bcutils-debug .

echo -e "\n=== Testing container interactively ==="
echo "Running container with bash..."
docker run -it --rm bcutils-debug bash -c "
echo 'PATH: $PATH'
echo 'Python location:' \$(which python)
echo 'Pip list:'
pip list | grep bcutils
echo 'Testing bcutils import:'
python -c 'import bcutils; print(\"bcutils imported successfully\")'
echo 'Testing bcutils command:'
which bcutils
bcutils --help 2>&1 | head -5
"

echo -e "\n=== Testing simple Dockerfile ==="
docker build -f Dockerfile.simple -t bcutils-simple-debug .
docker run --rm bcutils-simple-debug bash -c "
echo 'Simple build test:'
which bcutils
bcutils --help 2>&1 | head -3
"