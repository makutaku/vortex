# Vortex Production Scripts

This directory contains scripts for building and deploying Vortex to production environments.

## Scripts

### `build-production.sh`
Comprehensive Docker build script for production deployments to Docker Hub.

**Features:**
- Build Docker images with version tags
- Push to Docker Hub registry
- Run Docker tests before publishing
- Support for dry-run mode
- Comprehensive error handling and logging
- Automatic latest tagging

**Usage:**
```bash
# Basic build
./scripts/build-production.sh -u your-dockerhub-username v1.0.0

# Build and push to Docker Hub
./scripts/build-production.sh -u your-dockerhub-username -p v1.0.0

# Build with tests
./scripts/build-production.sh -u your-dockerhub-username --test v1.0.0

# Dry run (see what would happen)
./scripts/build-production.sh -u your-dockerhub-username --dry-run -p v1.0.0
```

### `example-docker-publish.sh`
Example workflow for publishing Vortex to Docker Hub. Copy and customize for your account.

## Environment Variables

Set these environment variables for automated builds:

```bash
export DOCKER_USERNAME="your-dockerhub-username"
export DOCKER_PASSWORD="your-dockerhub-password"  # For CI/CD
```

## Quick Start

1. **Set up Docker Hub account**: Create account at hub.docker.com

2. **Login to Docker Hub**:
   ```bash
   docker login
   ```

3. **Build and test locally**:
   ```bash
   ./scripts/build-production.sh -u your-username --test v1.0.0
   ```

4. **Push to Docker Hub**:
   ```bash
   ./scripts/build-production.sh -u your-username -p v1.0.0
   ```

5. **Deploy**:
   ```bash
   docker run -d --name vortex your-username/vortex:v1.0.0
   ```

## Docker Compose Example

Update your `docker-compose.yml` to use the published image:

```yaml
version: '3.8'
services:
  vortex:
    image: your-username/vortex:v1.0.0  # Use your published image
    container_name: vortex-prod
    environment:
      - VORTEX_DEFAULT_PROVIDER=yahoo
      - VORTEX_RUN_ON_STARTUP=true
    volumes:
      - ./data:/data
      - ./config:/home/vortex/.config/vortex
    restart: unless-stopped
```

## CI/CD Integration

For GitHub Actions, see `.github/workflows/docker-publish.yml` (if available) or use:

```yaml
- name: Build and Push
  run: |
    ./scripts/build-production.sh -u ${{ secrets.DOCKER_USERNAME }} -p ${{ github.ref_name }}
  env:
    DOCKER_PASSWORD: ${{ secrets.DOCKER_PASSWORD }}
```

## Troubleshooting

**Build fails**: Ensure Docker is running and you have sufficient disk space.

**Push fails**: Check Docker Hub credentials and network connectivity.

**Tests fail**: Run `./run-all-tests.sh --docker-only` to see detailed test output.

**Permission denied**: Make sure scripts are executable (`chmod +x scripts/*.sh`).