#!/bin/bash

# Quick validation script for Tests 5 and 12 
# Run this after any refactoring to ensure critical functionality works

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}🚨 Validating Critical Docker Tests (5 & 12)${NC}\n"

# Ensure Docker image exists
if ! docker images | grep -q "vortex-test.*latest"; then
    echo -e "${YELLOW}Building Docker image first...${NC}"
    docker build -t vortex-test:latest . --quiet
fi

echo -e "${YELLOW}Test 5: Providers Command Validation${NC}"
if timeout 20s docker run --rm --entrypoint=/usr/local/bin/vortex vortex-test:latest providers 2>/dev/null | grep -q "Total providers available: 3"; then
    echo -e "${GREEN}✅ Test 5 PASSED - Providers command works (3 providers loaded)${NC}"
    TEST5_PASSED=true
else 
    echo -e "${RED}❌ Test 5 FAILED - Providers command broken${NC}"
    echo -e "${YELLOW}Debug info:${NC}"
    timeout 15s docker run --rm --entrypoint=/usr/local/bin/python3 vortex-test:latest -c "
import sys
sys.path.insert(0, '/app/src')
try:
    from vortex.cli.dependencies import get_availability_summary
    print('Dependency availability:', get_availability_summary())
except Exception as e:
    print('Dependency check failed:', e)
" 2>/dev/null || echo "Could not run dependency check"
    TEST5_PASSED=false
fi

echo ""

echo -e "${YELLOW}Test 4: CLI Help Validation (bonus check)${NC}"
if timeout 10s docker run --rm --entrypoint=/usr/local/bin/vortex vortex-test:latest --help 2>/dev/null | grep -q "Commands:"; then
    echo -e "${GREEN}✅ CLI Help works - Commands are registered${NC}"
else
    echo -e "${RED}❌ CLI Help failed - Commands not registered${NC}"
fi

echo ""

echo -e "${YELLOW}Test 12: Download System Validation (quick check)${NC}"
# Quick test without actual download - just verify command parsing
if timeout 15s docker run --rm --entrypoint=/usr/local/bin/vortex vortex-test:latest download --help 2>/dev/null | grep -q "Download financial data"; then
    echo -e "${GREEN}✅ Test 12 PASSED - Download command available and functional${NC}"
    TEST12_PASSED=true
else
    echo -e "${RED}❌ Test 12 FAILED - Download command broken or missing${NC}"
    TEST12_PASSED=false
fi

echo ""

# Summary
if [ "$TEST5_PASSED" = true ] && [ "$TEST12_PASSED" = true ]; then
    echo -e "${GREEN}🎉 All critical tests PASSED! Safe to commit.${NC}"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo -e "  1. Run full test suite: ./scripts/test-docker-build.sh"
    echo -e "  2. Commit your changes"
    exit 0
else
    echo -e "${RED}🚨 CRITICAL TESTS FAILED! Do NOT commit yet.${NC}"
    echo ""
    echo -e "${YELLOW}Fix steps:${NC}"
    if [ "$TEST5_PASSED" = false ]; then
        echo -e "  1. Check plugin exception imports in vortex/plugins/__init__.py"
        echo -e "  2. Verify dependency injection system is working"
        echo -e "  3. Test: docker run --rm vortex-test:latest vortex providers"
    fi
    if [ "$TEST12_PASSED" = false ]; then
        echo -e "  1. Check CLI command registration"
        echo -e "  2. Verify download module imports"
        echo -e "  3. Test: docker run --rm vortex-test:latest vortex download --help"
    fi
    echo ""
    echo -e "${YELLOW}After fixing, run this script again before committing.${NC}"
    exit 1
fi