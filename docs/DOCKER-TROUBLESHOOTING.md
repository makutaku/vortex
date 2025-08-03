# Docker Build Troubleshooting

## Common Build Issues

### 1. Docker Permission Denied

**Error:**
```
permission denied while trying to connect to the Docker daemon socket
```

**Solutions:**
```bash
# Option 1: Run with sudo
sudo docker build -t bcutils:latest .

# Option 2: Add user to docker group (recommended)
sudo usermod -aG docker $USER
newgrp docker  # or logout/login

# Option 3: Use rootless Docker
```

### 2. UV Installation Issues

**Error:**
```
/bin/sh: 1: uv: not found
mv: cannot stat '/root/.cargo/bin/uv': No such file or directory
```

**Solutions:**
```bash
# Use the simple Dockerfile without uv (recommended for production)
docker build -f Dockerfile.simple -t bcutils:latest .

# Main Dockerfile uses uv for faster builds but may have version-dependent issues
# The simple version is more reliable across different environments
```

### 3. Build Context Too Large

**Error:**
```
Sending build context to Docker daemon  XXXMb
```

**Solutions:**
```bash
# Make sure .dockerignore exists and excludes:
echo "data/" >> .dockerignore
echo "config/" >> .dockerignore
echo ".git/" >> .dockerignore
echo "*.log" >> .dockerignore
```

### 4. Network Issues During Build

**Error:**
```
Could not reach servers
```

**Solutions:**
```bash
# Use Docker buildkit with network mode
DOCKER_BUILDKIT=1 docker build --network=host -t bcutils:latest .

# Or configure proxy if behind corporate firewall
docker build --build-arg HTTP_PROXY=http://proxy:8080 -t bcutils:latest .
```

### 5. Python Dependencies Fail

**Error:**
```
ERROR: Could not install packages due to an OSError
```

**Solutions:**
```bash
# Use simple build method
docker build -f Dockerfile.simple -t bcutils:latest .

# Or add build tools
# (already included in Dockerfile)
```

## Quick Tests

### Test 1: Simple Build Test
```bash
# Test if Docker works
docker run hello-world

# Test simple build
docker build -f Dockerfile.simple -t bcutils:test .
```

### Test 2: Check Image Contents
```bash
# Inspect the built image
docker run --rm -it bcutils:test bash

# Inside container:
bcutils --help
python -c "import bcutils; print('OK')"
ls -la /app/assets/
```

### Test 3: Test Without Dependencies
```bash
# Minimal test
docker run --rm bcutils:test python --version
docker run --rm bcutils:test which bcutils
```

### Test 4: Test Script
```bash
# Run comprehensive tests
./scripts/test-docker-build.sh

# If permission issues:
sudo ./scripts/test-docker-build.sh
```

## Alternative Approaches

### 1. Use Pre-built Python Image with Dependencies
```dockerfile
FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y cron tini && rm -rf /var/lib/apt/lists/*

# Install BC-Utils
RUN pip install bc-utils  # When published to PyPI

# Rest of Dockerfile...
```

### 2. Multi-stage with System Python
```dockerfile
# Build stage
FROM ubuntu:22.04 as builder
RUN apt-get update && apt-get install -y python3 python3-pip
COPY . /app
WORKDIR /app
RUN python3 -m pip install .

# Runtime stage
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3 cron tini
COPY --from=builder /usr/local/lib/python3.*/dist-packages /usr/local/lib/python3.10/dist-packages/
COPY --from=builder /usr/local/bin/bcutils /usr/local/bin/
```

### 3. Local Installation Test
```bash
# Test locally first
pip install -e .
bcutils --help
bcutils providers --list

# Then build Docker
docker build -t bcutils:latest .
```

## Debugging Commands

```bash
# Build with verbose output
docker build --progress=plain --no-cache -t bcutils:test .

# Check build logs
docker build -t bcutils:test . 2>&1 | tee build.log

# Inspect intermediate layers
docker build --target builder -t bcutils:builder .
docker run --rm -it bcutils:builder bash

# Check final image
docker run --rm -it bcutils:test bash
```

## Environment-Specific Issues

### WSL2/Windows
```bash
# Ensure Docker Desktop is running
# Use WSL2 backend in Docker Desktop settings
```

### macOS
```bash
# Ensure Docker Desktop is running
# Check available memory (needs 2GB+ for builds)
```

### Linux
```bash
# Install Docker if not present
sudo apt-get install docker.io docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

## Getting Help

If you're still having issues:

1. Check [Docker documentation](https://docs.docker.com/)
2. Verify your system meets requirements
3. Try the simple Dockerfile first
4. Check the test script output
5. Open an issue with build logs