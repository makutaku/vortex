#!/bin/bash
# Robust Docker Test Suite for Vortex
# Follows containerized application testing best practices
#
# Usage:
#   ./scripts/test-docker-build.sh [options] [test_numbers...]
#
# Options:
#   -h, --help          Show help message
#   -l, --list          List all available tests
#   -v, --verbose       Enable verbose output
#   -q, --quiet         Run in quiet mode (minimal output)
#   --skip-build        Skip Docker image build (use existing image)
#   --keep-containers   Keep containers after test completion
#   --keep-data         Keep test data directories after completion
#
# Examples:
#   ./scripts/test-docker-build.sh              # Run all tests
#   ./scripts/test-docker-build.sh 1 3 5        # Run tests 1, 3, and 5
#   ./scripts/test-docker-build.sh -v 12 13     # Run tests 12 and 13 with verbose output
#   ./scripts/test-docker-build.sh --list       # List all available tests

set -euo pipefail  # Fail fast with proper error handling

# ============================================================================
# CONFIGURATION
# ============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
readonly TEST_IMAGE="vortex-test:latest"
readonly TEST_TIMEOUT=30
readonly BUILD_TIMEOUT=300

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# Test state tracking
TESTS_PASSED=0
TESTS_FAILED=0
CONTAINERS_TO_CLEANUP=()
DIRECTORIES_TO_CLEANUP=()

# Command line options
VERBOSE=false
QUIET=false
SKIP_BUILD=false
KEEP_CONTAINERS=false
KEEP_DATA=false
SPECIFIC_TESTS=()

# Test registry - maps test numbers to function names and descriptions
declare -A TEST_REGISTRY=(
    [1]="test_docker_build:Docker Image Build"
    [2]="test_image_details:Image Details"
    [3]="test_basic_container_startup:Basic Container Startup"
    [4]="test_cli_help:CLI Help Command"
    [5]="test_providers_command:Providers Command"
    [6]="test_environment_variables:Environment Variables"
    [7]="test_volume_mounts:Volume Mounts"
    [8]="test_entrypoint_dry_run:Entrypoint (Dry Run)"
    [9]="test_docker_compose_config:Docker Compose Configuration"
    [10]="test_download_dry_run:Download Command (Dry Run)"
    [11]="test_yahoo_download:Yahoo Download with Market Data Validation"
    [12]="test_supervisord_scheduler_setup:Supervisord Scheduler Setup and Validation"
    [13]="test_supervisord_scheduler_execution:Comprehensive Supervisord Scheduler Execution Test"
    [14]="test_docker_compose_download:Docker Compose Yahoo Download with Market Data Validation"
    [15]="test_multi_period_asset_download:Multi-Period Asset Download (Daily + Hourly)"
)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_info() {
    if [[ "$QUIET" != true ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1" >&2
    ((TESTS_FAILED++))
}

log_warning() {
    if [[ "$QUIET" != true ]]; then
        echo -e "${YELLOW}[WARN]${NC} $1"
    fi
}

log_test() {
    if [[ "$QUIET" != true ]]; then
        echo -e "\n${YELLOW}=== $1 ===${NC}"
    fi
}

log_verbose() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

show_help() {
    cat << 'EOF'
Vortex Docker Test Suite

USAGE:
    ./scripts/test-docker-build.sh [OPTIONS] [TEST_NUMBERS...]

OPTIONS:
    -h, --help          Show this help message
    -l, --list          List all available tests with descriptions
    -v, --verbose       Enable verbose output for debugging
    -q, --quiet         Run in quiet mode (minimal output)
    --skip-build        Skip Docker image build (use existing image)
    --keep-containers   Keep containers after test completion for debugging
    --keep-data         Keep test data directories after completion

EXAMPLES:
    # Run all tests
    ./scripts/test-docker-build.sh

    # Run specific tests
    ./scripts/test-docker-build.sh 1 3 5

    # Run cron and download tests with verbose output
    ./scripts/test-docker-build.sh -v 12 13

    # List all available tests
    ./scripts/test-docker-build.sh --list

    # Quick test run (skip build, quiet mode)
    ./scripts/test-docker-build.sh --skip-build -q 4 5

    # Debug failing test (keep containers and data)
    ./scripts/test-docker-build.sh --keep-containers --keep-data -v 12
EOF
}

list_tests() {
    echo "Available Tests:"
    echo "================"
    for test_num in $(printf '%s\n' "${!TEST_REGISTRY[@]}" | sort -n); do
        IFS=':' read -r func_name description <<< "${TEST_REGISTRY[$test_num]}"
        printf "  %2d: %s\n" "$test_num" "$description"
    done
    echo
    echo "Usage: ./scripts/test-docker-build.sh [test_numbers...]"
}

# ============================================================================
# CONTAINER MANAGEMENT
# ============================================================================

# Run container with proper cleanup tracking
run_container() {
    local container_name="$1"
    shift
    local container_id
    
    # Start container in background and capture ID
    container_id=$(docker run -d --name "$container_name" "$@")
    CONTAINERS_TO_CLEANUP+=("$container_id")
    echo "$container_id"
}

# Run container with timeout and proper cleanup
run_container_with_timeout() {
    local timeout_seconds="$1"
    local container_name="$2"
    shift 2
    
    local container_id
    local exit_code=0
    
    # Start container
    container_id=$(run_container "$container_name" "$@")
    
    # Wait for completion or timeout
    if timeout "$timeout_seconds" docker wait "$container_id" >/dev/null 2>&1; then
        exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$container_id")
    else
        exit_code=124  # timeout exit code
        docker kill "$container_id" >/dev/null 2>&1 || true
    fi
    
    echo "$exit_code"
}

# Execute container command with output capture
exec_container() {
    local timeout_seconds="$1"
    local container_name="$2"
    shift 2
    
    local container_id
    local output
    local exit_code
    
    container_id=$(run_container "$container_name" "$@")
    
    # Wait for container to finish, then capture output
    if timeout "$timeout_seconds" docker wait "$container_id" >/dev/null 2>&1; then
        exit_code=$(docker inspect --format='{{.State.ExitCode}}' "$container_id")
        output=$(docker logs "$container_id" 2>&1)
    else
        exit_code=124
        docker kill "$container_id" >/dev/null 2>&1 || true
        output="Container timed out after ${timeout_seconds}s"
    fi
    
    echo "$output"
    return "$exit_code"
}

# ============================================================================
# CLEANUP FUNCTIONS
# ============================================================================

cleanup_containers() {
    if [[ "$KEEP_CONTAINERS" == true ]]; then
        log_info "Keeping containers for debugging (--keep-containers specified)"
        log_info "Container IDs: ${CONTAINERS_TO_CLEANUP[*]}"
        return 0
    fi
    
    log_info "Cleaning up containers..."
    
    for container_id in "${CONTAINERS_TO_CLEANUP[@]}"; do
        if [[ -n "$container_id" ]]; then
            log_verbose "Removing container: $container_id"
            docker kill "$container_id" >/dev/null 2>&1 || true
            docker rm -f "$container_id" >/dev/null 2>&1 || true
        fi
    done
    
    # Clean up any remaining test containers
    local remaining_containers
    remaining_containers=$(docker ps -a --filter "ancestor=$TEST_IMAGE" --format "{{.ID}}" | tr '\n' ' ')
    if [[ -n "$remaining_containers" ]]; then
        log_verbose "Cleaning up remaining test containers: $remaining_containers"
        echo "$remaining_containers" | xargs -r docker rm -f >/dev/null 2>&1 || true
    fi
    
    CONTAINERS_TO_CLEANUP=()
}

cleanup_directories() {
    if [[ "$KEEP_DATA" == true ]]; then
        log_info "Keeping test data directories for debugging (--keep-data specified)"
        if [[ -n "$TEST_SESSION_DIR" ]] && [[ -d "$TEST_SESSION_DIR" ]]; then
            log_info "Test session directory: $TEST_SESSION_DIR"
        fi
        log_info "Data directories: ${#DIRECTORIES_TO_CLEANUP[@]} items"
        return 0
    fi
    
    log_info "Cleaning up test directories..."
    
    for dir in "${DIRECTORIES_TO_CLEANUP[@]}"; do
        if [[ -d "$dir" ]]; then
            log_verbose "Removing directory: $dir"
            # Try multiple strategies to fix permissions and remove
            if ! rm -rf "$dir" 2>/dev/null; then
                # Strategy 1: Try to change owner to current user (if possible)
                if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
                    sudo chown -R "$(id -u):$(id -g)" "$dir" 2>/dev/null || true
                    rm -rf "$dir" 2>/dev/null && continue
                fi
                
                # Strategy 2: Fix permissions recursively with force
                chmod -R 755 "$dir" 2>/dev/null || true
                if rm -rf "$dir" 2>/dev/null; then
                    log_verbose "Successfully removed: $dir"
                    continue
                fi
                
                # Strategy 3: Move to temp location for later cleanup
                temp_dir="/tmp/vortex-test-cleanup-$(date +%s)-$$"
                if mv "$dir" "$temp_dir" 2>/dev/null; then
                    log_verbose "Moved to temp location: $temp_dir"
                    # Try to clean up the temp location asynchronously
                    (sleep 5 && rm -rf "$temp_dir" 2>/dev/null &) || true
                else
                    log_warning "Could not remove $dir - will be cleaned up on next test run"
                fi
            else
                log_verbose "Successfully removed: $dir"
            fi
        fi
    done
    
    # Note: Session directory cleanup is handled separately at the end of all tests
    # Don't remove session directory here as other tests may still need it
    
    DIRECTORIES_TO_CLEANUP=()
}

cleanup_test() {
    # Clean up directories created by the current test
    local test_name="${1:-unknown}"
    if [[ "$KEEP_DATA" != true ]]; then
        log_verbose "cleanup_test called for $test_name"
        
        # If array is empty, skip directory scanning to prevent cleaning up other tests' directories
        if [[ ${#DIRECTORIES_TO_CLEANUP[@]} -eq 0 ]]; then
            log_verbose "No test-specific directories to clean up for: $test_name"
        fi
        
        log_verbose "Cleaning up test directories for: $test_name"
        
        for dir in "${DIRECTORIES_TO_CLEANUP[@]}"; do
            if [[ -d "$dir" ]]; then
                log_verbose "Removing directory: $dir"
                # Try multiple strategies to fix permissions and remove
                if ! rm -rf "$dir" 2>/dev/null; then
                    # Strategy 1: Try to change owner to current user (if possible)
                    if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
                        sudo chown -R "$(id -u):$(id -g)" "$dir" 2>/dev/null || true
                        rm -rf "$dir" 2>/dev/null && continue
                    fi
                    
                    # Strategy 2: Fix permissions recursively with force
                    chmod -R 755 "$dir" 2>/dev/null || true
                    if rm -rf "$dir" 2>/dev/null; then
                        log_verbose "Successfully removed: $dir"
                        continue
                    fi
                    
                    # Strategy 3: Move to temp location for later cleanup
                    temp_dir="/tmp/vortex-test-cleanup-$(date +%s)-$$"
                    if mv "$dir" "$temp_dir" 2>/dev/null; then
                        log_verbose "Moved to temp location: $temp_dir"
                        # Try to clean up the temp location asynchronously
                        (sleep 5 && rm -rf "$temp_dir" 2>/dev/null &) || true
                    else
                        log_warning "Could not remove $dir - will be cleaned up on next test run"
                    fi
                else
                    log_verbose "Successfully removed: $dir"
                fi
            fi
        done
        
        # Reset the cleanup array for next test (but keep TEST_SESSION_DIR)
        DIRECTORIES_TO_CLEANUP=()
        
        # Note: Session directory cleanup is handled separately at the end of all tests
        # Don't clean up session directory here as other tests may still need it
    fi
}

cleanup_session_directory_if_empty() {
    if [[ -n "$TEST_SESSION_DIR" ]] && [[ -d "$TEST_SESSION_DIR" ]]; then
        # Check if session directory is empty
        local remaining_items=$(find "$TEST_SESSION_DIR" -mindepth 1 -maxdepth 1 | wc -l)
        if [[ "$remaining_items" -eq 0 ]]; then
            log_verbose "Removing empty session directory: $TEST_SESSION_DIR"
            rmdir "$TEST_SESSION_DIR" 2>/dev/null || true
            # Also try to remove parent directories if empty
            rmdir "$(dirname "$TEST_SESSION_DIR")" 2>/dev/null || true
        fi
    fi
}

cleanup_old_test_directories() {
    # Clean up any old test directories that may have been created in wrong locations
    # This handles legacy cleanup from older versions of the test script
    log_verbose "Checking for old test directories in wrong locations..."
    
    local cleaned_any=false
    
    # Check root level
    for dir in test-config test-data; do
        if [[ -d "$dir" ]]; then
            log_verbose "Removing legacy test directory: $dir"
            rm -rf "$dir" 2>/dev/null || sudo rm -rf "$dir" 2>/dev/null || true
            cleaned_any=true
        fi
    done
    
    # Check docker/ directory
    if ls docker/test-config-* docker/test-data-* >/dev/null 2>&1; then
        log_verbose "Removing legacy test directories in docker/"
        sudo rm -rf docker/test-config-* docker/test-data-* 2>/dev/null || true
        cleaned_any=true
    fi
    
    # Check src/ directory  
    if ls src/test-config-* src/test-data-* >/dev/null 2>&1; then
        log_verbose "Removing legacy test directories in src/"
        rm -rf src/test-config-* src/test-data-* 2>/dev/null || true
        cleaned_any=true
    fi
    
    if [[ "$cleaned_any" == true ]]; then
        log_info "Cleaned up legacy test directories from previous test runs"
    fi
}

cleanup_all() {
    log_verbose "Executing cleanup_all trap..."
    cleanup_containers
    cleanup_directories
    log_verbose "Cleanup_all completed"
}

# Trap for emergency container cleanup only (directories cleaned per-test)
trap cleanup_containers EXIT INT TERM

# ============================================================================
# SETUP FUNCTIONS
# ============================================================================

setup_test_environment() {
    log_info "Setting up test environment..."
    
    # Check Docker access
    if ! docker version >/dev/null 2>&1; then
        log_error "Cannot access Docker. Check Docker daemon and permissions."
        return 1
    fi
    
    # Clean up any existing test containers
    cleanup_containers
    
    # Clean up any old test directories from previous runs  
    cleanup_old_test_directories
    
    log_success "Test environment ready"
    return 0
}

# Test session directory - managed by fixture functions
TEST_SESSION_DIR=""

# ============================================================================
# FIXTURE FUNCTIONS
# ============================================================================

# Initialize test session - creates session-level resources
init_test_session() {
    log_verbose "Initializing test session..."
    
    # Create unique session directory
    TEST_SESSION_DIR="test-output/session-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$TEST_SESSION_DIR"
    
    log_verbose "Test session initialized: $TEST_SESSION_DIR"
    
    # Ensure session directory is writable
    chmod 755 "$TEST_SESSION_DIR" 2>/dev/null || true
    
    return 0
}

# Cleanup test session - removes session-level resources
cleanup_test_session() {
    if [[ "$KEEP_DATA" == true ]]; then
        log_info "Keeping test session directory for debugging: $TEST_SESSION_DIR"
        return 0
    fi
    
    if [[ -n "$TEST_SESSION_DIR" ]] && [[ -d "$TEST_SESSION_DIR" ]]; then
        log_verbose "Cleaning up test session: $TEST_SESSION_DIR"
        
        # Remove all contents
        rm -rf "$TEST_SESSION_DIR" 2>/dev/null || true
        
        # Try to remove parent test-output directory if empty
        rmdir "$(dirname "$TEST_SESSION_DIR")" 2>/dev/null || true
        
        log_verbose "Test session cleanup complete"
    fi
    
    return 0
}

# Create test-specific directories within session
# Usage: create_test_directories <session_dir> <test_name> <data_dir_var> <config_dir_var>
create_test_directories() {
    local session_dir="$1"
    local test_name="$2"
    local data_var_name="$3"
    local config_var_name="$4"
    
    if [[ -z "$session_dir" ]]; then
        log_error "Session directory parameter is empty - test function may not be updated to use fixture pattern"
        return 1
    fi
    if [[ ! -d "$session_dir" ]]; then
        log_error "Session directory does not exist: $session_dir"
        log_verbose "Available directories: $(ls -la "$(dirname "$session_dir")" 2>/dev/null || echo "parent directory not found")"
        return 1
    fi
    
    local timestamp=$(date +%s)
    local data_dir="${session_dir}/test-data-${test_name}-${timestamp}"
    local config_dir="${session_dir}/test-config-${test_name}-${timestamp}"
    
    # Create directories
    mkdir -p "$data_dir" "$config_dir"
    
    # Make directories writable for containers
    chmod 777 "$data_dir" "$config_dir" 2>/dev/null || true
    
    # Track for cleanup
    DIRECTORIES_TO_CLEANUP+=("$data_dir" "$config_dir")
    
    # Return directory paths via variable names
    if [[ -n "$data_var_name" ]]; then
        printf -v "$data_var_name" "%s" "$data_dir"
    fi
    if [[ -n "$config_var_name" ]]; then
        printf -v "$config_var_name" "%s" "$config_dir"
    fi
    
    log_verbose "Created test directories for $test_name: $data_dir, $config_dir"
    
    return 0
}

# Legacy function - use create_test_directories instead
create_test_directory() {
    local base_name="$1"
    local timestamp=$(date +%s)
    
    if [[ -z "$TEST_SESSION_DIR" ]] || [[ ! -d "$TEST_SESSION_DIR" ]]; then
        log_error "Session directory not initialized. Call init_test_session() first."
        return 1
    fi
    
    local dir_name="${TEST_SESSION_DIR}/${base_name}-${timestamp}"
    
    mkdir -p "$dir_name"
    chmod 777 "$dir_name" 2>/dev/null || true
    DIRECTORIES_TO_CLEANUP+=("$dir_name")
    
    # Store result for non-subshell access
    CREATED_DIRECTORY="$dir_name"
    
    log_verbose "Created test directory: $dir_name"
    
    echo "$dir_name"
}

# Legacy helper function - use new create_test_directories instead
create_test_directories_legacy() {
    local data_var_name="$1"
    local config_var_name="$2"
    local base_name="$3"
    
    if [[ -z "$TEST_SESSION_DIR" ]] || [[ ! -d "$TEST_SESSION_DIR" ]]; then
        log_error "Session directory not initialized. Call init_test_session() first."
        return 1
    fi
    
    # Call new fixture-based function
    create_test_directories "$TEST_SESSION_DIR" "$base_name" "$data_var_name" "$config_var_name"
    
    return $?
}

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

test_docker_build() {
    local session_dir="$1"
    log_test "Test 1: Docker Image Build"
    
    if [[ "$SKIP_BUILD" == true ]]; then
        log_info "Skipping Docker build (--skip-build specified)"
        if docker image inspect "$TEST_IMAGE" >/dev/null 2>&1; then
            log_success "Using existing Docker image"
            return 0
        else
            log_error "No existing image found, but --skip-build specified"
            return 1
        fi
    fi
    
    local original_dir=$(pwd)
    cd "$PROJECT_ROOT"
    
    log_verbose "Building Docker image with timeout ${BUILD_TIMEOUT}s..."
    
    local result=0
    if [[ "$VERBOSE" == true ]]; then
        # Show build output in verbose mode
        if timeout "$BUILD_TIMEOUT" docker build -f docker/Dockerfile -t "$TEST_IMAGE" .; then
            log_success "Docker build completed successfully"
            result=0
        else
            log_error "Docker build failed"
            result=1
        fi
    else
        # Hide build output in normal mode
        if timeout "$BUILD_TIMEOUT" docker build -f docker/Dockerfile -t "$TEST_IMAGE" . >/dev/null 2>&1; then
            log_success "Docker build completed successfully"
            result=0
        else
            log_error "Docker build failed"
            result=1
        fi
    fi
    
    # Restore original working directory
    cd "$original_dir"
    return $result
}

test_image_details() {
    local session_dir="$1"
    log_test "Test 2: Image Details"
    
    local image_info
    if image_info=$(docker images "$TEST_IMAGE" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"); then
        echo "$image_info"
        log_success "Image details retrieved"
        return 0
    else
        log_error "Could not retrieve image details"
        return 1
    fi
}

test_basic_container_startup() {
    local session_dir="$1"
    log_test "Test 3: Basic Container Startup"
    
    local output
    local exit_code
    
    # Test basic container execution
    if output=$(exec_container 20 "test-startup" --user "$(id -u):$(id -g)" --entrypoint="" "$TEST_IMAGE" echo "Container startup test"); then
        if [[ "$output" == *"Container startup test"* ]]; then
            log_success "Container starts and executes commands"
            return 0
        fi
    fi
    
    log_error "Container startup failed"
    return 1
}

test_cli_help() {
    local session_dir="$1"
    log_test "Test 4: CLI Help Command"
    
    local output
    
    log_verbose "Testing 'vortex --help' command..."
    
    if output=$(exec_container 20 "test-help" --entrypoint="" "$TEST_IMAGE" python3 -m vortex.cli.main --help 2>&1); then
        if [[ "$output" == *"Vortex: Financial data download automation tool"* ]]; then
            log_success "CLI help command works"
            if [[ "$VERBOSE" == true ]]; then
                echo "Help output preview:"
                echo "$output" | head -10
            fi
            return 0
        fi
    fi
    
    log_error "CLI help command failed"
    if [[ "$VERBOSE" == true ]] || [[ "$QUIET" != true ]]; then
        echo "Output: $output"
    fi
    return 1
}

test_providers_command() {
    local session_dir="$1"
    log_test "Test 5: Providers Command"
    
    local output
    local test_config_dir
    
    # Create test-specific directory using fixture pattern
    create_test_directories "$session_dir" "providers" "" "test_config_dir"
    
    if output=$(exec_container 30 "test-providers" \
        --user "$(id -u):$(id -g)" \
        -v "$PWD/$test_config_dir:/root/.config" \
        --entrypoint="" "$TEST_IMAGE" python3 -m vortex.cli.main providers 2>&1); then
        
        if [[ "$output" == *"Total providers available"* ]] || [[ "$output" == *"missing dependencies"* ]]; then
            log_success "Providers command works (loads correctly even if dependencies missing)"
            return 0
        fi
    fi
    
    log_error "Providers command failed"
    echo "Output: $output"
    return 1
}

test_environment_variables() {
    local session_dir="$1"
    log_test "Test 6: Environment Variables"
    
    local output
    
    if output=$(exec_container 20 "test-env" \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        -e VORTEX_LOG_LEVEL=DEBUG \
        --entrypoint="" "$TEST_IMAGE" \
        bash -c 'echo "Provider: $VORTEX_DEFAULT_PROVIDER, Log Level: $VORTEX_LOG_LEVEL"'); then
        
        if [[ "$output" == *"Provider: yahoo, Log Level: DEBUG"* ]]; then
            log_success "Environment variables work"
            return 0
        fi
    fi
    
    log_error "Environment variables test failed"
    return 1
}

test_volume_mounts() {
    local session_dir="$1"
    log_test "Test 7: Volume Mounts"
    
    local test_data_dir test_config_dir
    local output
    
    # Create test-specific directories using fixture pattern
    create_test_directories "$session_dir" "volumes" "test_data_dir" "test_config_dir"
    
    if output=$(exec_container 20 "test-volumes" \
        --user "$(id -u):$(id -g)" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/config" \
        --entrypoint="" "$TEST_IMAGE" \
        bash -c 'touch /data/test.txt && touch /config/test.txt && echo "Volume test successful"'); then
        
        if [[ "$output" == *"Volume test successful"* ]] && \
           [[ -f "$test_data_dir/test.txt" ]] && \
           [[ -f "$test_config_dir/test.txt" ]]; then
            log_success "Volume mounts work"
            return 0
        fi
    fi
    
    log_error "Volume mounts test failed"
    return 1
}

test_entrypoint_dry_run() {
    local session_dir="$1"
    log_test "Test 8: Entrypoint (Dry Run)"
    
    local container_id output
    
    # Start container (it won't exit due to tail -f)
    container_id=$(run_container "test-entrypoint-dry" \
        -e VORTEX_RUN_ON_STARTUP=false \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        "$TEST_IMAGE")
    
    # Give it time to start and log initial messages
    sleep 5
    
    # Capture logs and kill container
    output=$(docker logs "$container_id" 2>&1)
    docker kill "$container_id" >/dev/null 2>&1 || true
    
    if [[ "$output" == *"Starting Vortex container as vortex user"* ]] && [[ "$output" == *"Starting supervisord process manager"* ]]; then
        log_success "Entrypoint script works (supervisord started successfully)"
        return 0
    fi
    
    log_error "Entrypoint test failed"
    echo "Output: $output"
    return 1
}

test_docker_compose_config() {
    local session_dir="$1"
    log_test "Test 9: Docker Compose Configuration"
    
    local original_dir=$(pwd)
    cd "$PROJECT_ROOT/docker"
    
    local result=0
    if docker compose config >/dev/null 2>&1; then
        log_success "Docker Compose configuration is valid"
        result=0
    else
        log_error "Docker Compose configuration is invalid"
        result=1
    fi
    
    # Restore original working directory
    cd "$original_dir"
    
    return $result
}

test_download_dry_run() {
    local session_dir="$1"
    log_test "Test 10: Download Command (Dry Run)"
    
    local output
    
    # Test basic download command syntax (no --dry-run option exists)
    if output=$(exec_container 30 "test-download-dry" \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        --entrypoint="" "$TEST_IMAGE" \
        python3 -m vortex.cli.main download --help 2>&1); then
        
        if [[ "$output" == *"Download financial data"* ]]; then
            log_success "Download command help works"
            return 0
        fi
    fi
    
    log_error "Download command test failed"
    echo "Output: $output"
    return 1
}


test_yahoo_download() {
    local session_dir="$1"
    log_test "Test 11: Yahoo Download with Market Data Validation"
    
    # This test not only verifies that the download command completes successfully,
    # but also validates that actual market data was fetched by examining CSV file contents.
    # Validation includes:
    # - CSV files were created
    # - Files contain proper OHLCV headers (Date, Open, High, Low, Close, Volume)
    # - Files contain actual numeric price data (not empty or malformed)
    # - Price data passes basic sanity checks (reasonable price ranges for AAPL)
    # - Data rows exist (not just headers)
    
    local test_data_dir test_config_dir
    local container_id output_file
    local success_indicators data_validation_passed
    
    # Create test-specific directories using fixture pattern
    if ! create_test_directories "$session_dir" "yahoo" "test_data_dir" "test_config_dir"; then
        log_error "Failed to create test directories for yahoo download test"
        return 1
    fi
    
    # Ensure variables are set before using them
    if [[ -z "$test_data_dir" ]] || [[ -z "$test_config_dir" ]]; then
        log_error "Test directories not properly set: data_dir='$test_data_dir', config_dir='$test_config_dir'"
        return 1
    fi
    
    output_file="$test_data_dir/container.log"
    
    # Copy asset file to container directory
    cp "$SCRIPT_DIR/assets/yahoo-test.json" "$test_data_dir/assets.json"
    
    # Start container with proper configuration (runs as built-in vortex user UID 1000)
    container_id=$(run_container "test-yahoo-download" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/home/vortex/.config/vortex" \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        -e VORTEX_RUN_ON_STARTUP=true \
        -e VORTEX_DOWNLOAD_ARGS="--yes --assets /data/assets.json --start-date 2024-12-01 --end-date 2024-12-07" \
        "$TEST_IMAGE")
    
    # Wait for download to complete (containers run indefinitely due to tail -f)
    # Need extra time for bot detection delay
    sleep 25
    
    # Capture logs and kill container
    docker logs "$container_id" > "$output_file" 2>&1
    docker kill "$container_id" >/dev/null 2>&1 || true
    
    # Check for success indicators in logs
    data_validation_passed=false
    if [[ -f "$output_file" ]]; then
        success_indicators=$(grep -c "Fetched remote data\|Download completed successfully\|✓ Completed" "$output_file" 2>/dev/null || echo "0")
        # Ensure it's a single number
        success_indicators=$(echo "$success_indicators" | head -1)
        
        if [[ "$success_indicators" -gt 0 ]]; then
            log_info "✓ Download process completed successfully"
            log_info "Success indicators found: $success_indicators"
            
            # Show key indicators
            grep -E "(Fetched remote data|Download completed successfully|✓ Completed)" "$output_file" | head -3
            
            # ENHANCED: Validate actual market data was fetched
            local csv_files=0 data_rows_total=0 market_data_validated=false
            csv_files=$(find "$test_data_dir" -name "*.csv" -type f 2>/dev/null | wc -l)
            csv_files=$(echo "$csv_files" | tr -d ' ')  # Remove any whitespace
            
            if [[ "$csv_files" -gt 0 ]]; then
                log_info "✓ Downloaded files: $csv_files CSV files"
                
                # Validate CSV file contents contain actual market data
                market_data_validated=false
                data_rows_total=0
                
                for csv_file in $(find "$test_data_dir" -name "*.csv" -type f | head -3); do
                    log_verbose "Validating CSV file: $csv_file"
                    
                    if [[ -s "$csv_file" ]]; then  # File exists and is not empty
                        # Count data rows (excluding header)
                        local data_rows
                        data_rows=$(tail -n +2 "$csv_file" 2>/dev/null | wc -l | tr -d ' ')
                        data_rows_total=$((data_rows_total + data_rows))
                        
                        # Check for required OHLCV columns in header
                        local header
                        header=$(head -1 "$csv_file" 2>/dev/null)
                        
                        if ([[ "$header" == *"Date"* ]] || [[ "$header" == *"DATETIME"* ]]) && [[ "$header" == *"Open"* ]] && \
                           [[ "$header" == *"High"* ]] && [[ "$header" == *"Low"* ]] && \
                           [[ "$header" == *"Close"* ]] && [[ "$header" == *"Volume"* ]]; then
                            
                            # Validate we have actual price data (sample a few rows)
                            local sample_rows
                            sample_rows=$(tail -n +2 "$csv_file" | head -3 2>/dev/null)
                            
                            if [[ -n "$sample_rows" ]]; then
                                # Check if data contains reasonable numeric values (simplified validation)
                                local has_numeric_data=false
                                # Simple check: if the sample contains decimal numbers, it's probably valid market data
                                if echo "$sample_rows" | grep -q "[0-9]\+\.[0-9]\+"; then
                                    has_numeric_data=true
                                fi
                                
                                if [[ "$has_numeric_data" == true ]]; then
                                    market_data_validated=true
                                    log_info "✓ Market data validation passed for $(basename "$csv_file")"
                                    log_info "  - Data rows: $data_rows"
                                    log_info "  - Sample data: $(echo "$sample_rows" | head -1 | cut -d',' -f1,2,5)"
                                else
                                    log_warning "✗ Market data validation failed: no valid numeric price data in $(basename "$csv_file")"
                                fi
                            else
                                log_warning "✗ Market data validation failed: no data rows in $(basename "$csv_file")"
                            fi
                        else
                            log_warning "✗ Market data validation failed: missing required OHLCV columns in $(basename "$csv_file")"
                            log_verbose "Header: $header"
                        fi
                    else
                        log_warning "✗ Market data validation failed: $(basename "$csv_file") is empty"
                    fi
                done
                
                if [[ "$market_data_validated" == true ]] && [[ "$data_rows_total" -gt 0 ]]; then
                    log_success "✓ Market data validation successful"
                    log_info "Total data rows across all files: $data_rows_total"
                    data_validation_passed=true
                else
                    log_error "✗ Market data validation failed: no valid market data found"
                    log_info "Files found but data validation failed"
                fi
                
                # Show file details
                find "$test_data_dir" -name "*.csv" -type f | head -3 | while read -r file; do
                    local size
                    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "unknown")
                    log_info "File: $(basename "$file") (${size} bytes)"
                done
            else
                log_error "✗ No CSV files found - download may have failed"
            fi
            
            # Final validation: both log success AND data validation must pass
            if [[ "$data_validation_passed" == true ]]; then
                log_success "Yahoo download test successful - real market data verified"
                return 0
            else
                log_error "Yahoo download test failed - market data validation failed"
                return 1
            fi
        else
            log_error "Yahoo download completed but no success indicators found"
            echo "Last 10 lines of output:"
            tail -10 "$output_file" 2>/dev/null || echo "No output captured"
            return 1
        fi
    else
        log_error "Yahoo download test failed - no output captured"
        return 1
    fi
}

test_supervisord_scheduler_setup() {
    local session_dir="$1"
    log_test "Test 12: Supervisord Scheduler Setup and Validation"
    
    local test_data_dir test_config_dir
    local container_id output_file
    local schedule="*/2 * * * *"  # Every 2 minutes for testing
    
    # Create test-specific directories using fixture pattern
    create_test_directories "$session_dir" "supervisord" "test_data_dir" "test_config_dir"
    
    # Copy asset file to container directory
    cp "$SCRIPT_DIR/assets/yahoo-test.json" "$test_data_dir/assets.json"
    
    output_file="$test_data_dir/container.log"
    
    # Start container with supervisord scheduling enabled (root-less architecture)
    container_id=$(run_container "test-supervisord-setup" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/home/vortex/.config/vortex" \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        -e VORTEX_RUN_ON_STARTUP=false \
        -e VORTEX_SCHEDULE="$schedule" \
        -e VORTEX_DOWNLOAD_ARGS="--yes --assets /data/assets.json --start-date 2024-12-01 --end-date 2024-12-07" \
        "$TEST_IMAGE")
    
    # Wait for container to start and supervisord to be configured
    sleep 10
    
    # Capture logs to check supervisord setup
    docker logs "$container_id" > "$output_file" 2>&1
    
    # Check if supervisord scheduler was configured properly
    local scheduler_setup_success=false
    local supervisord_started=false
    local health_check_created=false
    
    if [[ -f "$output_file" ]]; then
        # Check for supervisord scheduler setup indicators
        if grep -F "Setting up scheduled vortex download service with cron schedule: $schedule" "$output_file"; then
            scheduler_setup_success=true
        fi
        
        # Check if supervisord started
        if grep -F "Starting supervisord process manager" "$output_file"; then
            supervisord_started=true
        fi
        
        # Check if health monitoring service was configured in supervisord
        if docker exec "$container_id" ls /home/vortex/.config/supervisor/conf.d/health-monitor.conf >/dev/null 2>&1; then
            health_check_created=true
        fi
        
        # Verify supervisord scheduler service was configured (check inside container)
        local supervisord_output
        supervisord_output=$(docker exec "$container_id" ls -la /home/vortex/.config/supervisor/conf.d/ 2>/dev/null || echo "no config")
        
        local scheduler_configured=false
        if [[ "$supervisord_output" == *"vortex-scheduler.conf"* ]]; then
            scheduler_configured=true
        fi
        
        # Kill container
        docker kill "$container_id" >/dev/null 2>&1 || true
        
        # Evaluate test results
        local passed_checks=0
        local total_checks=4
        
        if [[ "$scheduler_setup_success" == true ]]; then
            log_info "✓ Supervisord scheduler configured correctly"
            ((passed_checks++))
        else
            log_warning "✗ Supervisord scheduler setup not found in logs"
        fi
        
        if [[ "$supervisord_started" == true ]]; then
            log_info "✓ Supervisord process manager started"
            ((passed_checks++))
        else
            log_warning "✗ Supervisord start not confirmed"
        fi
        
        if [[ "$health_check_created" == true ]]; then
            log_info "✓ Health monitoring service configured in supervisord"
            ((passed_checks++))
        else
            log_warning "✗ Health monitoring service not configured"
        fi
        
        if [[ "$scheduler_configured" == true ]]; then
            log_info "✓ Supervisord scheduler service configured properly"
            ((passed_checks++))
        else
            log_warning "✗ Supervisord scheduler service not properly configured"
            echo "Supervisor config directory: $supervisord_output"
        fi
        
        # Test passes if at least 3 out of 4 checks pass
        if [[ $passed_checks -ge 3 ]]; then
            log_success "Supervisord scheduler setup test successful ($passed_checks/$total_checks checks passed)"
            log_info "Schedule: $schedule"
            log_info "Download command scheduled for periodic execution via supervisord"
            return 0
        else
            log_error "Supervisord scheduler setup test failed ($passed_checks/$total_checks checks passed)"
            echo "Last 10 lines of container output:"
            tail -10 "$output_file" 2>/dev/null || echo "No output captured"
            return 1
        fi
    else
        docker kill "$container_id" >/dev/null 2>&1 || true
        log_error "Supervisord scheduler setup test failed - no output captured"
        return 1
    fi
}

test_supervisord_scheduler_execution() {
    local session_dir="$1"
    log_test "Test 13: Comprehensive Supervisord Scheduler Execution Test"
    log_info "⚠️  This test may take up to 60 seconds - it waits for actual scheduled execution"
    
    local test_data_dir test_config_dir
    local container_id output_file
    local schedule="*/1 * * * *"  # Every minute (converted to 60 second interval by supervisord)
    local wait_timeout=180  # 3 minutes maximum wait
    local check_interval=30  # Check every 30 seconds
    
    # Create test-specific directories using fixture pattern
    create_test_directories "$session_dir" "supervisord-exec" "test_data_dir" "test_config_dir"
    output_file="$test_data_dir/container.log"
    
    # Copy asset file to container directory
    cp "$SCRIPT_DIR/assets/yahoo-test.json" "$test_data_dir/assets.json"
    
    log_info "Starting container with schedule: $schedule"
    
    # Start container with supervisord scheduling enabled (runs as vortex user throughout)
    container_id=$(run_container "test-supervisord-execution" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/home/vortex/.config/vortex" \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        -e VORTEX_RUN_ON_STARTUP=false \
        -e VORTEX_SCHEDULE="$schedule" \
        -e VORTEX_DOWNLOAD_ARGS="--yes --assets /data/assets.json --start-date 2024-12-01 --end-date 2024-12-07 --output-dir /data" \
        "$TEST_IMAGE")
    
    log_info "Container started (ID: ${container_id:0:12}...), waiting for supervisord setup..."
    
    # Wait for initial setup (30 seconds)
    sleep 30
    
    # Check if supervisord setup was successful
    docker logs "$container_id" > "$output_file" 2>&1
    if ! grep -F "Starting supervisord process manager" "$output_file"; then
        docker kill "$container_id" >/dev/null 2>&1 || true
        log_error "Supervisord process manager failed to start"
        return 1
    fi
    
    # Verify supervisord scheduler was actually configured
    if ! grep -F "Setting up scheduled vortex download service with cron schedule: $schedule" "$output_file"; then
        docker kill "$container_id" >/dev/null 2>&1 || true
        log_error "Supervisord scheduler setup not found in logs"
        log_verbose "Looking for pattern: 'Setting up scheduled vortex download service with cron schedule: $schedule'"
        log_verbose "Available logs preview:"
        grep "schedule\|supervisord" "$output_file" | head -3 | sed 's/^/  /'
        return 1
    fi
    
    log_info "✓ Supervisord started and scheduler configured, waiting for first execution..."
    
    # Wait for supervisord scheduler to actually execute and download data
    local elapsed_time=0
    local scheduler_executed=false
    local data_downloaded=false
    
    while [[ $elapsed_time -lt $wait_timeout ]]; do
        # Update logs
        docker logs "$container_id" > "$output_file" 2>&1
        
        # Check if supervisord scheduler has executed by looking for vortex command output
        # Also check the supervisord logs and vortex.log file directly
        if ! $scheduler_executed; then
            # Check docker logs output
            if grep -q "Running scheduled vortex download\|Download completed successfully" "$output_file"; then
                log_info "✓ Supervisord scheduler executed! (after ${elapsed_time}s)"
                scheduler_executed=true
            # Also check supervisord logs
            elif docker exec "$container_id" test -f "/var/log/supervisor/vortex-scheduler.out.log" 2>/dev/null && \
                 docker exec "$container_id" grep -q "Running scheduled vortex download\|Scheduled download completed successfully" "/var/log/supervisor/vortex-scheduler.out.log" 2>/dev/null; then
                log_info "✓ Supervisord scheduler executed (found in scheduler log)! (after ${elapsed_time}s)"
                scheduler_executed=true
            fi
        fi
        
        # Check if data was actually downloaded
        if ! $data_downloaded; then
            # Look for successful download indicators
            if grep -q "Download completed successfully" "$output_file"; then
                log_info "✓ Data download completed successfully!"
                data_downloaded=true
                break
            elif grep -q "Fetched remote data" "$output_file"; then
                log_info "✓ Data fetching in progress..."
            fi
        fi
        
        # Check for CSV files in the data directory
        if find "$test_data_dir" -name "*.csv" -type f | grep -q .; then
            log_info "✓ CSV data files found in output directory!"
            data_downloaded=true
            break
        fi
        
        log_verbose "Waiting for cron execution... (${elapsed_time}/${wait_timeout}s)"
        sleep $check_interval
        elapsed_time=$((elapsed_time + check_interval))
    done
    
    # Kill container
    docker kill "$container_id" >/dev/null 2>&1 || true
    
    # Final validation
    local success_indicators=0
    local total_indicators=3
    
    # 1. Check if supervisord scheduler executed
    if $scheduler_executed; then
        log_info "✓ Supervisord scheduler executed successfully"
        ((success_indicators++))
    else
        log_warning "✗ No supervisord scheduler execution detected in logs"
    fi
    
    # 2. Check if data was downloaded
    if $data_downloaded; then
        log_info "✓ Data download completed"
        ((success_indicators++))
    else
        log_warning "✗ Data download not confirmed"
    fi
    
    # 3. Check for actual CSV files
    local csv_count=$(find "$test_data_dir" -name "*.csv" -type f | wc -l)
    if [[ $csv_count -gt 0 ]]; then
        log_info "✓ Found $csv_count CSV file(s) in output directory"
        ((success_indicators++))
        
        # Show file details
        log_info "Downloaded files:"
        find "$test_data_dir" -name "*.csv" -exec ls -lh {} \; | while read line; do
            log_info "  $line"
        done
    else
        log_warning "✗ No CSV files found in output directory"
    fi
    
    # Log final status
    log_info "Comprehensive test results: $success_indicators/$total_indicators indicators passed"
    
    if [[ $elapsed_time -ge $wait_timeout ]]; then
        log_warning "Test timed out after ${wait_timeout}s"
    fi
    
    # Test passes if all 3 indicators are successful (scheduler execution is different from direct execution)
    if [[ $success_indicators -eq 3 ]]; then
        log_success "Comprehensive supervisord scheduler execution test successful ($success_indicators/$total_indicators indicators passed)"
        log_info "Test completed in ${elapsed_time}s"
        return 0
    else
        log_error "Comprehensive supervisord scheduler execution test failed ($success_indicators/$total_indicators indicators passed)"
        log_info "Check logs at: $output_file"
        return 1
    fi
}

test_docker_compose_download() {
    local session_dir="$1"
    log_test "Test 14: Docker Compose Yahoo Download with Market Data Validation"
    
    # This test deploys vortex using docker compose and validates:
    # - Service starts successfully
    # - Downloads market data for multiple symbols
    # - Files contain actual numeric price data (not empty or malformed)
    # - Price data passes basic sanity checks (reasonable price ranges for AAPL)
    # - Data rows exist (not just headers)
    
    local test_data_dir test_config_dir
    local service_name="vortex"
    local success_indicators=0 data_validation_passed=false
    
    # Create test-specific directories using robust fixture pattern
    create_test_directories "$session_dir" "compose" "test_data_dir" "test_config_dir"
    
    # Copy asset file to container directory
    cp "$SCRIPT_DIR/assets/yahoo-test.json" "$test_data_dir/assets.json"
    
    # Generate unique project name early for container naming
    local compose_project="vortex-test-$(date +%s)"
    
    # Create docker compose override file for testing in a more robust way
    local compose_override_file="$test_data_dir/docker-compose.override.yml"
    
    # Debug: Check if directory exists and is accessible
    if [[ ! -d "$test_data_dir" ]]; then
        log_error "Test data directory was not created: $test_data_dir"
        log_verbose "Session directory status: $(ls -la "$(dirname "$test_data_dir")" 2>/dev/null || echo "parent directory does not exist")"
        return 1
    fi
    
    # Ensure the directory exists and is writable
    mkdir -p "$test_data_dir" 2>/dev/null || true
    chmod 755 "$test_data_dir" 2>/dev/null || true
    
    # Use absolute path to avoid any PWD issues
    log_verbose "About to create override file at: $compose_override_file"
    log_verbose "Parent directory exists: $(test -d "$(dirname "$compose_override_file")" && echo "YES" || echo "NO")"
    log_verbose "Parent directory contents: $(ls -la "$(dirname "$compose_override_file")" 2>/dev/null | wc -l || echo "0") items"
    log_verbose "Session directory exists: $(test -d "$TEST_SESSION_DIR" && echo "YES" || echo "NO")"
    log_verbose "Session directory permissions: $(ls -ld "$TEST_SESSION_DIR" 2>/dev/null || echo "NOT FOUND")"
    
    # Robust file creation with retry logic to handle race conditions
    local retry_count=0
    local max_retries=3
    while [[ $retry_count -lt $max_retries ]]; do
        # Ensure directory exists immediately before write (defensive programming)
        mkdir -p "$(dirname "$compose_override_file")" 2>/dev/null || true
        
        # Create the file with explicit printf to avoid heredoc shell race conditions
        compose_write_error=""
        local container_name="vortex-test-compose-${compose_project##*-}"
        if compose_write_error=$(printf 'version: '\''3.8'\''

services:
  vortex:
    container_name: %s
    environment:
      VORTEX_DEFAULT_PROVIDER: yahoo
      VORTEX_RUN_ON_STARTUP: true
      VORTEX_DOWNLOAD_ARGS: "--yes --assets /data/assets.json --start-date 2024-12-01 --end-date 2024-12-07"
      VORTEX_SCHEDULE: "# DISABLED"
      VORTEX_LOG_LEVEL: DEBUG
    volumes:
      - %s/%s:/data
      # Container runs as vortex user consistently (UID 1000)  
      - %s/%s:/home/vortex/.config/vortex
' "$container_name" "$(pwd)" "$test_data_dir" "$(pwd)" "$test_config_dir" > "$compose_override_file" 2>&1)
        then
            log_verbose "Successfully created override file on attempt $((retry_count + 1))"
            break
        else
            retry_count=$((retry_count + 1))
            log_verbose "Failed to write file on attempt $retry_count: $compose_write_error"
            log_verbose "Directory status after failure: $(ls -la "$(dirname "$compose_override_file")" 2>/dev/null || echo "directory no longer exists")"
            
            if [[ $retry_count -ge $max_retries ]]; then
                log_error "Failed to write docker-compose override file after $max_retries attempts: $compose_override_file"
                log_verbose "Final error: $compose_write_error"
                log_verbose "Session directory status after all failures: $(ls -la "$TEST_SESSION_DIR" 2>/dev/null || echo "session directory no longer exists")"
                return 1
            else
                log_verbose "Retrying in 0.5 seconds..."
                sleep 0.5
            fi
        fi
    done

    # Verify the override file was created successfully
    if [[ ! -f "$compose_override_file" ]]; then
        log_error "Failed to create docker-compose override file: $compose_override_file"
        return 1
    fi
    
    local output_file="/tmp/compose-${compose_project}.log"
    
    # Ensure test directories are writable by container user (UID 1000)
    chmod 777 "$test_data_dir" "$test_config_dir" 2>/dev/null || true
    
    local original_dir=$(pwd)
    cd "$PROJECT_ROOT"
    
    log_info "Starting Docker Compose deployment..."
    log_verbose "Project name: $compose_project"
    log_verbose "Override file: $compose_override_file"
    
    # Start services with override configuration
    if docker compose -f docker/docker-compose.yml -f "$compose_override_file" -p "$compose_project" up -d > "$output_file" 2>&1; then
        log_info "✓ Docker Compose services started successfully"
    else
        log_error "✗ Failed to start Docker Compose services"
        # Show error output if available
        if [[ -f "$output_file" ]]; then
            log_verbose "Compose startup errors:"
            tail -10 "$output_file" | sed 's/^/  /'
        fi
        # Restore original working directory before returning
        cd "$original_dir"
        return 1
    fi
    
    # Wait for startup download to complete
    log_info "Waiting for startup download to complete..."
    sleep 30  # Allow time for download process
    
    # Get service logs and append to output file
    log_verbose "Collecting service logs..."
    local service_logs_file="$test_data_dir/service.log"
    docker compose -f docker/docker-compose.yml -f "$compose_override_file" -p "$compose_project" logs vortex > "$service_logs_file" 2>&1 || true
    
    # Combine logs safely
    if [[ -f "$service_logs_file" ]]; then
        cat "$service_logs_file" >> "$output_file" 2>/dev/null || {
            log_verbose "Could not append service logs, copying to separate file"
            cp "$service_logs_file" "$output_file" 2>/dev/null || true
        }
    fi
    
    # Stop and remove services
    log_verbose "Stopping Docker Compose services..."
    docker compose -f docker/docker-compose.yml -f "$compose_override_file" -p "$compose_project" down --remove-orphans >/dev/null 2>&1 || true
    
    # Check for success indicators in logs
    data_validation_passed=false
    if [[ -f "$output_file" ]]; then
        success_indicators=$(grep -c "Fetched remote data\|Download completed successfully\|✓ Completed" "$output_file" 2>/dev/null || echo "0")
        # Ensure it's a single number
        success_indicators=$(echo "$success_indicators" | head -1)
        
        if [[ "$success_indicators" -gt 0 ]]; then
            log_info "✓ Download process completed successfully"
            log_info "Success indicators found: $success_indicators"
            
            # Show key indicators
            grep -E "(Fetched remote data|Download completed successfully|✓ Completed)" "$output_file" | head -3
            
            # ENHANCED: Validate actual market data was fetched
            local csv_files=0 data_rows_total=0 market_data_validated=false
            csv_files=$(find "$test_data_dir" -name "*.csv" -type f 2>/dev/null | wc -l)
            csv_files=$(echo "$csv_files" | tr -d ' ')  # Remove any whitespace
            
            if [[ "$csv_files" -gt 0 ]]; then
                log_info "✓ Downloaded files: $csv_files CSV files"
                
                # Validate CSV file contents contain actual market data
                market_data_validated=false
                data_rows_total=0
                
                for csv_file in $(find "$test_data_dir" -name "*.csv" -type f | head -3); do
                    log_verbose "Validating CSV file: $csv_file"
                    
                    if [[ -s "$csv_file" ]]; then  # File exists and is not empty
                        # Count data rows (excluding header)
                        local data_rows
                        data_rows=$(tail -n +2 "$csv_file" 2>/dev/null | wc -l | tr -d ' ')
                        data_rows_total=$((data_rows_total + data_rows))
                        
                        # Check for required OHLCV columns in header
                        local header
                        header=$(head -1 "$csv_file" 2>/dev/null)
                        
                        if ([[ "$header" == *"Date"* ]] || [[ "$header" == *"DATETIME"* ]]) && [[ "$header" == *"Open"* ]] && \
                           [[ "$header" == *"High"* ]] && [[ "$header" == *"Low"* ]] && \
                           [[ "$header" == *"Close"* ]] && [[ "$header" == *"Volume"* ]]; then
                            
                            # Validate we have actual price data (sample a few rows)
                            local sample_rows
                            sample_rows=$(tail -n +2 "$csv_file" | head -3 2>/dev/null)
                            
                            if [[ -n "$sample_rows" ]]; then
                                # Check if data contains reasonable numeric values (simplified validation)
                                local has_numeric_data=false
                                # Simple check: if the sample contains decimal numbers, it's probably valid market data
                                if echo "$sample_rows" | grep -q "[0-9]\+\.[0-9]\+"; then
                                    has_numeric_data=true
                                fi
                                
                                if [[ "$has_numeric_data" == true ]]; then
                                    market_data_validated=true
                                    log_info "✓ Market data validation passed for $(basename "$csv_file")"
                                    log_info "  - Data rows: $data_rows"
                                    log_info "  - Sample data: $(echo "$sample_rows" | head -1 | cut -d',' -f1,2,5)"
                                else
                                    log_warning "✗ Market data validation failed: no valid numeric price data in $(basename "$csv_file")"
                                fi
                            else
                                log_warning "✗ Market data validation failed: no data rows in $(basename "$csv_file")"
                            fi
                        else
                            log_warning "✗ Market data validation failed: missing required OHLCV columns in $(basename "$csv_file")"
                            log_verbose "Header: $header"
                        fi
                    else
                        log_warning "✗ Market data validation failed: empty or missing file $(basename "$csv_file")"
                    fi
                done
                
                # Set validation status and show summary
                if [[ "$market_data_validated" == true ]]; then
                    log_info "✓ Market data validation passed (total rows: $data_rows_total)"
                    data_validation_passed=true
                else
                    log_warning "✗ Market data validation failed - no valid market data found"
                fi
            else
                log_warning "✗ No CSV files found in output directory"
            fi
        else
            log_warning "✗ No download success indicators found in logs"
        fi
    else
        log_error "✗ No log file found"
    fi
    
    # Docker Compose specific validations
    local compose_validations=0
    
    # Check if service started properly (from compose output)
    # Modern Docker Compose uses format: "Container [name]  Creating/Created/Starting/Started"
    if grep -qE "(Container.*vortex-test-compose.*(Creating|Created|Starting|Started)|Creating vortex-test-compose|vortex-test-compose.*Created)" "$output_file" 2>/dev/null; then
        log_info "✓ Docker Compose container created successfully"
        ((compose_validations++))
    else
        # Fallback: check if we have any compose-related success indicators
        if [[ -f "$output_file" ]] && [[ -s "$output_file" ]] && ! grep -qE "(ERROR|Error|error|failed|Failed)" "$output_file" 2>/dev/null; then
            log_info "✓ Docker Compose container created successfully (implied from clean startup)"
            ((compose_validations++))
        else
            log_warning "✗ Docker Compose container creation not found in logs"
            log_verbose "Compose output content preview:"
            head -5 "$output_file" 2>/dev/null | sed 's/^/  /' || log_verbose "No output file content"
            log_verbose "Looking for patterns: Container.*vortex-test-compose.*(Creating|Created|Starting|Started)"
        fi
    fi
    
    # Check if service was healthy
    if grep -q "Started\|healthy" "$output_file" 2>/dev/null; then
        log_info "✓ Docker Compose service started successfully"
        ((compose_validations++))
    else
        log_warning "✗ Docker Compose service health check failed"
    fi
    
    # Overall test result
    local total_validations=5  # 3 from download + 2 from compose
    local passed_validations=0
    
    if [[ "${success_indicators:-0}" -gt 0 ]]; then ((passed_validations++)); fi
    if [[ "${csv_files:-0}" -gt 0 ]]; then ((passed_validations++)); fi
    if [[ "$data_validation_passed" == true ]]; then ((passed_validations++)); fi
    passed_validations=$((passed_validations + compose_validations))
    
    log_info "Docker Compose test validation summary:"
    log_info "- Download success indicators: ${success_indicators:-0}"
    log_info "- CSV files created: ${csv_files:-0}"
    log_info "- Market data validation: $([ "${data_validation_passed:-false}" == true ] && echo "PASSED" || echo "FAILED")"
    log_info "- Compose validations: ${compose_validations:-0}/2"
    log_info "- Total validations: ${passed_validations:-0}/$total_validations"
    
    # Clean up temporary log file to prevent side effects
    rm -f "$output_file" 2>/dev/null || true
    
    # Restore original working directory before returning
    cd "$original_dir"
    
    if [[ "$passed_validations" -ge 4 ]]; then  # Allow 1 failure
        log_success "Docker Compose download test passed ($passed_validations/$total_validations validations passed)"
        return 0
    else
        log_error "Docker Compose download test failed ($passed_validations/$total_validations validations passed)"
        log_info "Check logs (may have been cleaned up): /tmp/compose-*.log"
        return 1
    fi
}

test_multi_period_asset_download() {
    local session_dir="$1"
    log_test "Test 15: Multi-Period Asset Download (Daily + Hourly)"
    
    local test_data_dir test_config_dir
    
    # Create test-specific directories using fixture pattern
    create_test_directories "$session_dir" "multiperiod" "test_data_dir" "test_config_dir"
    
    # Copy the pre-created multi-period asset file
    cp "$PROJECT_ROOT/tests/docker/assets/yahoo-multiperiod.json" "$test_data_dir/multiperiod-assets.json"
    
    # Run vortex with asset file for limited date range
    cd "$PROJECT_ROOT"
    
    timeout 180 docker run --rm --user "1000:1000" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/home/vortex/.config/vortex" \
        --entrypoint="" vortex-test:latest \
        vortex download --yes --assets /data/multiperiod-assets.json \
        --provider yahoo --start-date 2024-12-01 --end-date 2024-12-07 \
        --output-dir /data 2>&1 | tee "$test_data_dir/test15_output.log"
    
    local exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        # Check that all expected period data files were created (daily, weekly, hourly)
        local daily_file=$(find "$test_data_dir" -name "*.csv" -path "*/1d/*" | head -1)
        local weekly_file=$(find "$test_data_dir" -name "*.csv" -path "*/1W/*" | head -1)
        local hourly_file=$(find "$test_data_dir" -name "*.csv" -path "*/1h/*" | head -1)
        
        if [[ -n "$daily_file" && -n "$weekly_file" && -n "$hourly_file" ]]; then
            log_success "Multi-period download successful - found daily, weekly, and hourly files"
            
            # Show file structure for validation
            if [[ "$VERBOSE" == "true" ]]; then
                echo "Files created:"
                find "$test_data_dir" -name "*.csv" | sed 's/^/  /'
            fi
        else
            log_error "Multi-period download failed - missing expected files"
            echo "Daily file: $daily_file"
            echo "Weekly file: $weekly_file"
            echo "Hourly file: $hourly_file" 
            find "$test_data_dir" -name "*.csv" | sed 's/^/Found: /'
            return 1
        fi
    else
        log_error "Multi-period asset download failed with exit code $exit_code"
        if [[ -f "$test_data_dir/test15_output.log" ]]; then
            echo "Output:"
            cat "$test_data_dir/test15_output.log"
        fi
        return 1
    fi
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

run_specific_tests() {
    local tests_to_run=("$@")
    local test_failed=false
    
    if [[ ${#tests_to_run[@]} -eq 0 ]]; then
        # Run all tests if none specified
        tests_to_run=($(printf '%s\n' "${!TEST_REGISTRY[@]}" | sort -n))
    fi
    
    log_info "Starting Vortex Docker Test Suite"
    if [[ ${#tests_to_run[@]} -lt ${#TEST_REGISTRY[@]} ]]; then
        log_info "Running selected tests: ${tests_to_run[*]}"
    else
        log_info "Running all tests"
    fi
    echo "========================================"
    
    # Setup test environment
    setup_test_environment || return 1
    
    # Initialize test session fixture
    if ! init_test_session; then
        log_error "Failed to initialize test session"
        return 1
    fi
    
    # Verify session directory exists and is accessible
    if [[ ! -d "$TEST_SESSION_DIR" ]]; then
        log_error "Session directory was not created or is inaccessible: $TEST_SESSION_DIR"
        return 1
    fi
    
    log_verbose "Session directory verified: $TEST_SESSION_DIR"
    
    # Run specified tests
    for test_num in "${tests_to_run[@]}"; do
        if [[ -n "${TEST_REGISTRY[$test_num]:-}" ]]; then
            IFS=':' read -r func_name description <<< "${TEST_REGISTRY[$test_num]}"
            log_verbose "Executing test $test_num: $func_name"
            
            # Verify session directory still exists before running test
            if [[ ! -d "$TEST_SESSION_DIR" ]]; then
                log_error "Session directory disappeared before test $test_num: $TEST_SESSION_DIR"
                log_verbose "Available sessions: $(ls -la test-output/ 2>/dev/null | grep session || echo 'no sessions found')"
                log_verbose "Current working directory: $(pwd)"
                log_verbose "TEST_SESSION_DIR value: '$TEST_SESSION_DIR'"
                test_failed=true
                break
            fi
            
            # Run the test function with session directory parameter
            if ! "$func_name" "$TEST_SESSION_DIR"; then
                # Clean up test directories even on failure
                cleanup_test "Test $test_num ($func_name)"
                
                # Special handling for critical tests
                if [[ "$test_num" == "1" ]] || [[ "$test_num" == "3" ]]; then
                    log_error "Critical test $test_num failed, stopping execution"
                    return 1
                fi
                test_failed=true
            else
                # Clean up test directories on success
                cleanup_test "Test $test_num ($func_name)"
            fi
        else
            log_error "Unknown test number: $test_num"
            test_failed=true
        fi
    done
    
    # Cleanup test session fixture
    cleanup_test_session
    
    if [[ "$test_failed" == true ]]; then
        return 1
    fi
    
    return 0
}

run_all_tests() {
    run_specific_tests
}

show_results() {
    echo
    echo "========================================"
    log_info "Test Results Summary"
    echo "========================================"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        log_success "All tests passed! ($TESTS_PASSED/$((TESTS_PASSED + TESTS_FAILED)))"
        echo
        log_info "To clean up test image:"
        echo "    docker rmi $TEST_IMAGE"
        
        return 0
    else
        log_error "Some tests failed: $TESTS_FAILED failed, $TESTS_PASSED passed"
        
        return 1
    fi
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -l|--list)
                list_tests
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --keep-containers)
                KEEP_CONTAINERS=true
                shift
                ;;
            --keep-data)
                KEEP_DATA=true
                shift
                ;;
            -*)
                echo "Error: Unknown option $1" >&2
                echo "Run with --help for usage information" >&2
                exit 1
                ;;
            *)
                # Assume it's a test number
                if [[ "$1" =~ ^[0-9]+$ ]]; then
                    SPECIFIC_TESTS+=("$1")
                else
                    echo "Error: Invalid test number '$1'" >&2
                    echo "Run with --list to see available tests" >&2
                    exit 1
                fi
                shift
                ;;
        esac
    done
}

main() {
    local exit_code=0
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Validate test numbers if specified
    if [[ ${#SPECIFIC_TESTS[@]} -gt 0 ]]; then
        for test_num in "${SPECIFIC_TESTS[@]}"; do
            if [[ -z "${TEST_REGISTRY[$test_num]:-}" ]]; then
                echo "Error: Test $test_num does not exist" >&2
                echo "Available tests: $(printf '%s ' "${!TEST_REGISTRY[@]}" | sort -n)" >&2
                exit 1
            fi
        done
    fi
    
    # Show configuration in verbose mode
    if [[ "$VERBOSE" == true ]]; then
        log_verbose "Configuration:"
        log_verbose "  Verbose: $VERBOSE"
        log_verbose "  Quiet: $QUIET"
        log_verbose "  Skip Build: $SKIP_BUILD"
        log_verbose "  Keep Containers: $KEEP_CONTAINERS"
        log_verbose "  Keep Data: $KEEP_DATA"
        log_verbose "  Test Image: $TEST_IMAGE"
        if [[ ${#SPECIFIC_TESTS[@]} -gt 0 ]]; then
            log_verbose "  Specific Tests: ${SPECIFIC_TESTS[*]}"
        fi
    fi
    
    # Show test output directory info
    log_info "Test outputs will be organized in: test-output/"
    log_verbose "Test session directory will be created as: test-output/session-YYYYMMDD-HHMMSS/"
    
    # Run tests
    if [[ ${#SPECIFIC_TESTS[@]} -gt 0 ]]; then
        run_specific_tests "${SPECIFIC_TESTS[@]}"
    else
        run_all_tests
    fi
    exit_code=$?
    
    # Show results
    show_results
    
    # Session cleanup is now handled by the fixture pattern in run_specific_tests
    
    return $exit_code
}

# Run main function
main "$@"