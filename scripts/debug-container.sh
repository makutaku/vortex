#!/bin/bash
# Debug script for container issues

echo "Building test container..."
docker build -t vortex-debug .

echo -e "\n=== Testing container interactively ==="
echo "Running container with bash..."
docker run -it --rm vortex-debug bash -c "
echo 'PATH: $PATH'
echo 'Python location:' \$(which python)
echo 'Pip list:'
pip list | grep vortex
echo 'Testing vortex import:'
python -c 'import vortex; print(\"vortex imported successfully\")'
echo 'Testing vortex command:'
which vortex
vortex --help 2>&1 | head -5
"

echo -e "\n=== Testing simple Dockerfile ==="
docker build -f docker/Dockerfile.simple -t vortex-simple-debug .
docker run --rm vortex-simple-debug bash -c "
echo 'Simple build test:'
which vortex
vortex --help 2>&1 | head -3
"