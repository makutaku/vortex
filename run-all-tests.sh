#!/bin/bash
# Comprehensive Test Runner for Vortex
# Runs all test suites: unit, integration, e2e, and Docker tests

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Configuration
VERBOSE=false
SKIP_DOCKER=false
DOCKER_ONLY=false

# Results tracking
UNIT_RESULT=""
INTEGRATION_RESULT=""
E2E_RESULT=""
DOCKER_RESULT=""

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}🧪 Vortex Comprehensive Test Suite${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_usage() {
    cat << EOF
Usage: $0 [options]

Options:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output
    --skip-docker       Skip Docker tests (faster for development)
    --docker-only       Run only Docker tests
    --python-only       Run only Python tests (unit, integration, e2e)

Examples:
    $0                  # Run all tests
    $0 -v               # Run all tests with verbose output
    $0 --skip-docker    # Skip Docker tests (development workflow)
    $0 --docker-only    # Run only Docker deployment tests
EOF
}

run_python_tests() {
    local test_type="$1"
    local test_path="$2"
    local description="$3"
    
    echo -e "${YELLOW}=== Running $description ===${NC}"
    
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}Command: uv run pytest $test_path -c pytest-no-cov.ini -v${NC}"
    fi
    
    # Activate virtual environment and run tests WITHOUT coverage for individual runs
    if source .venv/bin/activate && uv run pytest "$test_path" -c pytest-no-cov.ini $([ "$VERBOSE" = true ] && echo "-v" || echo "-q"); then
        echo -e "${GREEN}✅ $description PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ $description FAILED${NC}"
        return 1
    fi
}

run_docker_tests() {
    echo -e "${YELLOW}=== Running Docker Deployment Tests ===${NC}"
    
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}Command: ./tests/docker/test-docker-build.sh -v${NC}"
        ./tests/docker/test-docker-build.sh -v
    else
        echo -e "${BLUE}Command: ./tests/docker/test-docker-build.sh${NC}"
        ./tests/docker/test-docker-build.sh
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Docker Tests PASSED${NC}"
        return 0
    else
        echo -e "${RED}❌ Docker Tests FAILED${NC}"
        return 1
    fi
}

print_summary() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}📊 Test Results Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    
    if [ "$DOCKER_ONLY" != true ]; then
        echo -e "Unit Tests:        $UNIT_RESULT"
        echo -e "Integration Tests: $INTEGRATION_RESULT" 
        echo -e "E2E Tests:         $E2E_RESULT"
    fi
    
    if [ "$SKIP_DOCKER" != true ]; then
        echo -e "Docker Tests:      $DOCKER_RESULT"
    fi
    
    echo -e "${BLUE}========================================${NC}"
    
    # Check if all tests passed
    local all_passed=true
    
    if [ "$DOCKER_ONLY" != true ]; then
        [ "$UNIT_RESULT" = "${GREEN}✅ PASSED${NC}" ] || all_passed=false
        [ "$INTEGRATION_RESULT" = "${GREEN}✅ PASSED${NC}" ] || all_passed=false
        [ "$E2E_RESULT" = "${GREEN}✅ PASSED${NC}" ] || all_passed=false
    fi
    
    if [ "$SKIP_DOCKER" != true ]; then
        [ "$DOCKER_RESULT" = "${GREEN}✅ PASSED${NC}" ] || all_passed=false
    fi
    
    if [ "$all_passed" = true ]; then
        echo -e "${GREEN}🎉 ALL TESTS PASSED! 🎉${NC}"
        return 0
    else
        echo -e "${RED}💥 SOME TESTS FAILED 💥${NC}"
        return 1
    fi
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            print_usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --skip-docker)
            SKIP_DOCKER=true
            shift
            ;;
        --docker-only)
            DOCKER_ONLY=true
            shift
            ;;
        --python-only)
            SKIP_DOCKER=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            print_usage
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header
    
    # Check if virtual environment exists
    if [ ! -d ".venv" ] && [ "$DOCKER_ONLY" != true ]; then
        echo -e "${RED}❌ Virtual environment not found. Please run: uv venv .venv && source .venv/bin/activate && uv pip install -e .${NC}"
        exit 1
    fi
    
    # Run Python tests unless docker-only
    if [ "$DOCKER_ONLY" != true ]; then
        echo -e "${BLUE}🐍 Running Python Test Suite...${NC}"
        
        # Unit Tests
        if run_python_tests "unit" "tests/unit/" "Unit Tests"; then
            UNIT_RESULT="${GREEN}✅ PASSED${NC}"
        else
            UNIT_RESULT="${RED}❌ FAILED${NC}"
        fi
        
        # Integration Tests  
        if run_python_tests "integration" "tests/integration/" "Integration Tests"; then
            INTEGRATION_RESULT="${GREEN}✅ PASSED${NC}"
        else
            INTEGRATION_RESULT="${RED}❌ FAILED${NC}"
        fi
        
        # E2E Tests
        if run_python_tests "e2e" "tests/e2e/" "E2E Tests"; then
            E2E_RESULT="${GREEN}✅ PASSED${NC}"
        else
            E2E_RESULT="${RED}❌ FAILED${NC}"
        fi
        
        # Overall Coverage Check (only if all Python tests passed)
        if [ "$UNIT_RESULT" = "${GREEN}✅ PASSED${NC}" ] && [ "$INTEGRATION_RESULT" = "${GREEN}✅ PASSED${NC}" ] && [ "$E2E_RESULT" = "${GREEN}✅ PASSED${NC}" ]; then
            echo -e "${YELLOW}=== Running Overall Coverage Check ===${NC}"
            if source .venv/bin/activate && uv run pytest tests/ --cov=src/vortex --cov-report=term-missing --cov-fail-under=80 --quiet; then
                echo -e "${GREEN}✅ Overall Coverage Check PASSED (80% threshold)${NC}"
            else
                echo -e "${YELLOW}⚠️ Overall Coverage Check FAILED (below 80% threshold)${NC}"
                echo -e "${YELLOW}Note: E2E and Integration tests are not marked as failed due to coverage${NC}"
                # Don't mark any tests as failed - coverage is separate from functional tests
            fi
        fi
    fi
    
    # Run Docker tests unless skipped
    if [ "$SKIP_DOCKER" != true ]; then
        echo -e "${BLUE}🐳 Running Docker Test Suite...${NC}"
        
        if run_docker_tests; then
            DOCKER_RESULT="${GREEN}✅ PASSED${NC}"
        else
            DOCKER_RESULT="${RED}❌ FAILED${NC}"
        fi
    fi
    
    print_summary
}

# Run main function
main "$@"