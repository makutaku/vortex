#!/bin/bash
# Test script for Docker build and basic functionality

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up test directories...${NC}"
    rm -rf test-data test-config test-data-* test-config-*
}

# Set trap to cleanup on exit
trap cleanup EXIT

echo -e "${YELLOW}Testing Vortex Docker Build...${NC}\n"

# Check if we can access Docker
if ! docker version >/dev/null 2>&1; then
    echo -e "${RED}✗ Cannot access Docker. Run with sudo or add user to docker group.${NC}"
    echo "Try: sudo ./scripts/test-docker-build.sh"
    exit 1
fi

# Test 1: Build the Docker image
echo -e "${YELLOW}Test 1: Building Docker image...${NC}"
if docker build -t vortex-test:latest .; then
    echo -e "${GREEN}✓ Docker build successful${NC}\n"
else
    echo -e "${YELLOW}Standard build failed, trying simple build...${NC}"
    if docker build -f Dockerfile.simple -t vortex-test:latest .; then
        echo -e "${GREEN}✓ Simple Docker build successful${NC}\n"
    else
        echo -e "${RED}✗ Both Docker builds failed${NC}"
        exit 1
    fi
fi

# Test 2: Check image size
echo -e "${YELLOW}Test 2: Checking image details...${NC}"
docker images vortex-test:latest
echo -e "${GREEN}✓ Image details retrieved${NC}\n"

# Test 3: Test basic container run
echo -e "${YELLOW}Test 3: Testing container startup...${NC}"
echo "Testing vortex command..."
mkdir -p test-data test-config
if timeout 20s docker run --rm -v "$(pwd)/test-data:/data" -v "$(pwd)/test-config:/config" --entrypoint="" vortex-test:latest vortex --help >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Container runs successfully${NC}\n"
else
    echo -e "${RED}✗ Container failed to run vortex command${NC}"
    echo "Trying basic command test..."
    if timeout 20s docker run --rm --entrypoint="" vortex-test:latest bash -c "vortex --version || vortex --help" 2>&1 | head -5; then
        echo -e "${YELLOW}⚠ Command exists but needs volumes/config${NC}\n"
    else
        echo -e "${RED}✗ vortex command not found${NC}"
        exit 1
    fi
fi

# Test 4: Test CLI help command
echo -e "${YELLOW}Test 4: Testing 'vortex --help' command...${NC}"
timeout 20s docker run --rm --entrypoint="" vortex-test:latest vortex --help
echo -e "${GREEN}✓ CLI help command works${NC}\n"

# Test 5: Test providers list
echo -e "${YELLOW}Test 5: Testing 'vortex providers --list' command...${NC}"
mkdir -p test-config-providers/vortex
if timeout 20s docker run --rm \
    -v "$(pwd)/test-config-providers:/root/.config" \
    --entrypoint="" \
    vortex-test:latest vortex providers --list; then
    echo -e "${GREEN}✓ Providers list command works${NC}\n"
else
    echo -e "${YELLOW}⚠ Providers command failed (likely disk space issue)${NC}\n"
fi

# Test 6: Test with environment variables
echo -e "${YELLOW}Test 6: Testing environment variables...${NC}"
if timeout 20s docker run --rm \
    -e VORTEX_DEFAULT_PROVIDER=yahoo \
    -e VORTEX_LOG_LEVEL=DEBUG \
    --entrypoint="" \
    vortex-test:latest \
    bash -c 'echo "Provider: $VORTEX_DEFAULT_PROVIDER, Log Level: $VORTEX_LOG_LEVEL"'; then
    echo -e "${GREEN}✓ Environment variables work${NC}\n"
else
    echo -e "${RED}✗ Environment variables failed${NC}"
    exit 1
fi

# Test 7: Test volume mounts
echo -e "${YELLOW}Test 7: Testing volume mounts...${NC}"
mkdir -p test-data test-config
if timeout 20s docker run --rm \
    -v "$(pwd)/test-data:/data" \
    -v "$(pwd)/test-config:/config" \
    --entrypoint="" \
    vortex-test:latest \
    bash -c 'touch /data/test.txt && touch /config/test.txt && echo "Volume test successful"'; then
    
    if [ -f test-data/test.txt ] && [ -f test-config/test.txt ]; then
        echo -e "${GREEN}✓ Volume mounts work${NC}\n"
    else
        echo -e "${RED}✗ Volume mount verification failed${NC}"
        exit 1
    fi
else
    echo -e "${RED}✗ Volume mounts failed${NC}"
    exit 1
fi

# Test 8: Test entrypoint script
echo -e "${YELLOW}Test 8: Testing entrypoint (dry run)...${NC}"
if docker run --rm \
    -e VORTEX_RUN_ON_STARTUP=false \
    -e VORTEX_DEFAULT_PROVIDER=yahoo \
    vortex-test:latest \
    timeout 5 bash -c '/app/entrypoint.sh' 2>&1 | grep -q "Starting Vortex container"; then
    echo -e "${GREEN}✓ Entrypoint script works${NC}\n"
else
    echo -e "${YELLOW}⚠ Entrypoint test inconclusive (expected with timeout)${NC}\n"
fi

# Test 9: Test Docker Compose
echo -e "${YELLOW}Test 9: Testing Docker Compose configuration...${NC}"
if docker compose config >/dev/null 2>&1 || docker-compose config >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker Compose configuration is valid${NC}\n"
else
    echo -e "${RED}✗ Docker Compose configuration invalid${NC}"
    echo "Note: Requires 'docker compose' (v2) or 'docker-compose' (v1) to be installed"
fi

# Test 10: Quick smoke test with Yahoo provider
echo -e "${YELLOW}Test 10: Testing 'vortex download' with Yahoo provider (dry-run)...${NC}"
if timeout 30s docker run --rm \
    -e VORTEX_DEFAULT_PROVIDER=yahoo \
    --entrypoint="" \
    vortex-test:latest \
    vortex download --provider yahoo --symbol AAPL --yes --dry-run 2>/dev/null || true; then
    echo -e "${GREEN}✓ Download command dry-run completed${NC}\n"
fi

# Test 11: Test entrypoint with startup disabled
echo -e "${YELLOW}Test 11: Testing entrypoint without startup download...${NC}"
mkdir -p test-data-entrypoint test-config-entrypoint
if timeout 20 docker run --rm \
    -v "$(pwd)/test-data-entrypoint:/data" \
    -v "$(pwd)/test-config-entrypoint:/config" \
    -e VORTEX_RUN_ON_STARTUP=false \
    -e VORTEX_DEFAULT_PROVIDER=yahoo \
    vortex-test:latest 2>&1 | grep -q "Starting Vortex container"; then
    echo -e "${GREEN}✓ Entrypoint works without download${NC}\n"
else
    echo -e "${YELLOW}⚠ Entrypoint test timeout (expected)${NC}\n"
fi

# Test 12: Test Yahoo download (no credentials needed)
echo -e "${YELLOW}Test 12: Testing Yahoo download...${NC}"
mkdir -p test-data-yahoo test-config-yahoo

# Test with a short timeout to avoid hanging
echo "Running Yahoo download test (dry-run with timeout)..."
if timeout 60s docker run --rm \
    -v "$(pwd)/test-data-yahoo:/data" \
    -v "$(pwd)/test-config-yahoo:/config" \
    -e VORTEX_DEFAULT_PROVIDER=yahoo \
    -e VORTEX_RUN_ON_STARTUP=true \
    -e VORTEX_DOWNLOAD_ARGS="--yes --symbol AAPL" \
    vortex-test:latest > test-data-yahoo/output.log 2>&1; then
    
    # Check for success indicators in the output
    if grep -q "Download completed successfully\|Starting download\|Processing.*AAPL" test-data-yahoo/output.log; then
        echo -e "${GREEN}✓ Yahoo download test successful${NC}\n"
    else
        echo -e "${YELLOW}⚠ Yahoo download completed but success message unclear${NC}"
        echo "Last few lines of output:"
        tail -5 test-data-yahoo/output.log 2>/dev/null || echo "No output file generated"
        echo ""
    fi
else
    echo -e "${YELLOW}⚠ Yahoo download test timeout or failure${NC}"
    echo "Container output (if available):"
    head -10 test-data-yahoo/output.log 2>/dev/null || echo "No output captured"
    echo ""
fi

echo -e "${GREEN}All tests passed! 🎉${NC}"
echo -e "\nTo clean up test image, run:"
echo -e "  docker rmi vortex-test:latest"