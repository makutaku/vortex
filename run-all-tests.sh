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
UNIT_ONLY=false
FAST_ONLY=false

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
    --unit-only         Run only unit tests (fastest for development)
    --fast              Run only fast tests (excludes slow E2E and Docker tests)

Examples:
    $0                  # Run all tests (including slow E2E and Docker)
    $0 -v               # Run all tests with verbose output
    $0 --skip-docker    # Skip Docker tests (development workflow)
    $0 --docker-only    # Run only Docker deployment tests
    $0 --unit-only      # Run only unit tests (fastest for development)
    $0 --fast           # Run fast tests only (unit, integration, fast E2E - no slow/Docker)
    $0 --fast -v        # Run fast tests with verbose output

Test Speed Comparison:
    --unit-only         ~30s  (unit tests only)
    --fast              ~60s  (unit + integration + fast E2E, no Docker/slow tests)
    --skip-docker       ~120s (all Python tests including slow E2E)
    (default)           ~300s (all tests including Docker deployment)
EOF
}

run_python_tests() {
    local test_type="$1"
    local test_path="$2"
    local description="$3"
    local marker_args="$4"  # Optional marker arguments
    
    echo -e "${YELLOW}=== Running $description ===${NC}"
    
    # Build the pytest command with optional marker filtering
    local pytest_cmd="uv run pytest $test_path -c pytest-no-cov.ini"
    if [ -n "$marker_args" ]; then
        pytest_cmd="$pytest_cmd $marker_args"
    fi
    pytest_cmd="$pytest_cmd $([ "$VERBOSE" = true ] && echo "-v" || echo "-q")"
    
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}Command: $pytest_cmd${NC}"
    fi
    
    # Activate virtual environment and run tests WITHOUT coverage for individual runs
    if source .venv/bin/activate && eval "$pytest_cmd"; then
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
        if [ "$UNIT_ONLY" != true ]; then
            echo -e "Integration Tests: $INTEGRATION_RESULT" 
            echo -e "E2E Tests:         $E2E_RESULT"
        fi
    fi
    
    if [ "$SKIP_DOCKER" != true ]; then
        echo -e "Docker Tests:      $DOCKER_RESULT"
    fi
    
    echo -e "${BLUE}========================================${NC}"
    
    # Check if all tests passed
    local all_passed=true
    
    if [ "$DOCKER_ONLY" != true ]; then
        [ "$UNIT_RESULT" = "${GREEN}✅ PASSED${NC}" ] || all_passed=false
        if [ "$UNIT_ONLY" != true ]; then
            [ "$INTEGRATION_RESULT" = "${GREEN}✅ PASSED${NC}" ] || all_passed=false
            [ "$E2E_RESULT" = "${GREEN}✅ PASSED${NC}" ] || all_passed=false
        fi
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
        --unit-only)
            UNIT_ONLY=true
            SKIP_DOCKER=true
            shift
            ;;
        --fast)
            FAST_ONLY=true
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
        if [ "$UNIT_ONLY" = true ]; then
            echo -e "${BLUE}🧪 Running Unit Tests Only...${NC}"
        elif [ "$FAST_ONLY" = true ]; then
            echo -e "${BLUE}⚡ Running Fast Tests Only (excluding slow E2E and Docker)...${NC}"
        else
            echo -e "${BLUE}🐍 Running Python Test Suite...${NC}"
        fi
        
        # Unit Tests (always run unless docker-only)
        if run_python_tests "unit" "tests/unit/" "Unit Tests" ""; then
            UNIT_RESULT="${GREEN}✅ PASSED${NC}"
        else
            UNIT_RESULT="${RED}❌ FAILED${NC}"
        fi
        
        # Integration Tests (skip if unit-only)
        if [ "$UNIT_ONLY" != true ]; then
            if run_python_tests "integration" "tests/integration/" "Integration Tests" ""; then
                INTEGRATION_RESULT="${GREEN}✅ PASSED${NC}"
            else
                INTEGRATION_RESULT="${RED}❌ FAILED${NC}"
            fi
        fi
        
        # E2E Tests (skip if unit-only)
        if [ "$UNIT_ONLY" != true ]; then
            # Set marker args based on fast flag
            local e2e_marker_args=""
            local e2e_description="E2E Tests"
            if [ "$FAST_ONLY" = true ]; then
                e2e_marker_args="-m \"not slow\""
                e2e_description="E2E Tests (Fast Only)"
            fi
            
            if run_python_tests "e2e" "tests/e2e/" "$e2e_description" "$e2e_marker_args"; then
                E2E_RESULT="${GREEN}✅ PASSED${NC}"
            else
                E2E_RESULT="${RED}❌ FAILED${NC}"
            fi
        fi
        
        # Overall Coverage Check (only if all enabled Python tests passed)
        coverage_check_condition=false
        if [ "$UNIT_ONLY" = true ]; then
            # For unit-only, just check unit tests passed
            [ "$UNIT_RESULT" = "${GREEN}✅ PASSED${NC}" ] && coverage_check_condition=true
        else
            # For full test suite or fast tests, check all enabled tests passed
            [ "$UNIT_RESULT" = "${GREEN}✅ PASSED${NC}" ] && [ "$INTEGRATION_RESULT" = "${GREEN}✅ PASSED${NC}" ] && [ "$E2E_RESULT" = "${GREEN}✅ PASSED${NC}" ] && coverage_check_condition=true
        fi
        
        if [ "$coverage_check_condition" = true ]; then
            echo -e "${YELLOW}=== Running Overall Coverage Check ===${NC}"
            coverage_test_path="tests/"
            coverage_marker_args=""
            
            if [ "$UNIT_ONLY" = true ]; then
                coverage_test_path="tests/unit/"
            elif [ "$FAST_ONLY" = true ]; then
                # For fast tests, exclude slow tests from coverage calculation
                coverage_marker_args="-m \"not slow\""
            fi
            
            # Build coverage command
            local coverage_cmd="uv run pytest $coverage_test_path --cov=src/vortex --cov-report=term-missing --cov-fail-under=80 --quiet"
            if [ -n "$coverage_marker_args" ]; then
                coverage_cmd="uv run pytest $coverage_test_path $coverage_marker_args --cov=src/vortex --cov-report=term-missing --cov-fail-under=80 --quiet"
            fi
            
            if source .venv/bin/activate && eval "$coverage_cmd"; then
                echo -e "${GREEN}✅ Overall Coverage Check PASSED (80% threshold)${NC}"
            else
                echo -e "${YELLOW}⚠️ Overall Coverage Check FAILED (below 80% threshold)${NC}"
                if [ "$FAST_ONLY" = true ]; then
                    echo -e "${YELLOW}Note: Fast mode excludes slow tests from coverage calculation${NC}"
                fi
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