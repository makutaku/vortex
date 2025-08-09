#!/bin/bash
# Example usage of build-production.sh for Docker Hub publishing
# Copy this file and customize for your Docker Hub account

# Replace 'youruser' with your actual Docker Hub username
DOCKER_USERNAME="youruser"
VERSION="v1.0.0"

echo "=== Vortex Docker Hub Publishing Example ==="
echo ""

# Step 1: Build the image locally
echo "1. Building image locally..."
./scripts/build-production.sh -u "$DOCKER_USERNAME" "$VERSION"

# Step 2: Test the image (optional but recommended)
echo ""
echo "2. Testing the built image..."
./scripts/build-production.sh -u "$DOCKER_USERNAME" --test "$VERSION"

# Step 3: Build and push to Docker Hub
echo ""
echo "3. Building and pushing to Docker Hub..."
echo "Note: This will require Docker Hub login"
./scripts/build-production.sh -u "$DOCKER_USERNAME" -p "$VERSION"

echo ""
echo "=== Publishing Complete ==="
echo "Your Vortex image is now available at:"
echo "  docker pull $DOCKER_USERNAME/vortex:$VERSION"
echo "  docker pull $DOCKER_USERNAME/vortex:latest"
echo ""
echo "To deploy:"
echo "  docker run -d --name vortex $DOCKER_USERNAME/vortex:$VERSION"
echo ""
echo "Or update your docker-compose.yml:"
echo "  image: $DOCKER_USERNAME/vortex:$VERSION"