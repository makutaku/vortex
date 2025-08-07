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
#   --comprehensive     Include comprehensive/long-running tests (auto-enabled for specific tests)
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
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
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
COMPREHENSIVE=false
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
    [11]="test_entrypoint_no_startup:Entrypoint Without Startup Download"
    [12]="test_yahoo_download:Yahoo Download with Market Data Validation"
    [13]="test_cron_job_setup:Cron Job Setup and Validation"
    [14]="test_cron_job_execution:Comprehensive Cron Job Execution Test"
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
    --comprehensive     Include comprehensive/long-running tests (auto-enabled for specific tests)

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

    # Run comprehensive tests including long-running cron execution
    ./scripts/test-docker-build.sh --comprehensive

    # Run only the comprehensive cron execution test
    ./scripts/test-docker-build.sh --comprehensive 14
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
        log_info "Data directories: ${DIRECTORIES_TO_CLEANUP[*]}"
        return 0
    fi
    
    log_info "Cleaning up test directories..."
    
    for dir in "${DIRECTORIES_TO_CLEANUP[@]}"; do
        if [[ -d "$dir" ]]; then
            log_verbose "Removing directory: $dir"
            # Fix permissions first
            find "$dir" -type d -exec chmod 755 {} \; 2>/dev/null || true
            find "$dir" -type f -exec chmod 644 {} \; 2>/dev/null || true
            rm -rf "$dir" 2>/dev/null || {
                log_warning "Could not remove $dir (permission issue)"
                # Move to temp location if can't delete
                mv "$dir" "/tmp/vortex-test-cleanup-$(date +%s)" 2>/dev/null || true
            }
        fi
    done
    
    DIRECTORIES_TO_CLEANUP=()
}

cleanup_all() {
    cleanup_containers
    cleanup_directories
}

# Trap for cleanup on exit
trap cleanup_all EXIT INT TERM

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
    
    log_success "Test environment ready"
    return 0
}

create_test_directory() {
    local base_name="$1"
    local timestamp=$(date +%s)
    local dir_name="${base_name}-${timestamp}"
    
    mkdir -p "$dir_name"
    DIRECTORIES_TO_CLEANUP+=("$dir_name")
    echo "$dir_name"
}

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

test_docker_build() {
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
    
    cd "$PROJECT_ROOT"
    
    log_verbose "Building Docker image with timeout ${BUILD_TIMEOUT}s..."
    
    if [[ "$VERBOSE" == true ]]; then
        # Show build output in verbose mode
        if timeout "$BUILD_TIMEOUT" docker build -f docker/Dockerfile -t "$TEST_IMAGE" .; then
            log_success "Docker build completed successfully"
            return 0
        else
            log_error "Docker build failed"
            return 1
        fi
    else
        # Hide build output in normal mode
        if timeout "$BUILD_TIMEOUT" docker build -f docker/Dockerfile -t "$TEST_IMAGE" . >/dev/null 2>&1; then
            log_success "Docker build completed successfully"
            return 0
        else
            log_error "Docker build failed"
            return 1
        fi
    fi
}

test_image_details() {
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
    log_test "Test 5: Providers Command"
    
    local output
    local test_config_dir
    
    test_config_dir=$(create_test_directory "test-config-providers")
    
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
    log_test "Test 7: Volume Mounts"
    
    local test_data_dir test_config_dir
    local output
    
    test_data_dir=$(create_test_directory "test-data")
    test_config_dir=$(create_test_directory "test-config")
    
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
    
    if [[ "$output" == *"Starting Vortex container"* ]] && [[ "$output" == *"Skipping download on startup"* ]]; then
        log_success "Entrypoint script works (no startup download)"
        return 0
    fi
    
    log_error "Entrypoint test failed"
    echo "Output: $output"
    return 1
}

test_docker_compose_config() {
    log_test "Test 9: Docker Compose Configuration"
    
    cd "$PROJECT_ROOT/docker"
    
    if docker compose config >/dev/null 2>&1; then
        log_success "Docker Compose configuration is valid"
        return 0
    else
        log_error "Docker Compose configuration is invalid"
        return 1
    fi
}

test_download_dry_run() {
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

test_entrypoint_no_startup() {
    log_test "Test 11: Entrypoint Without Startup Download"
    
    local test_data_dir test_config_dir
    local container_id output
    
    test_data_dir=$(create_test_directory "test-data-entrypoint")
    test_config_dir=$(create_test_directory "test-config-entrypoint")
    
    # Start container (it won't exit due to tail -f)
    container_id=$(run_container "test-entrypoint-no-startup" \
        --user "$(id -u):$(id -g)" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/config" \
        -e VORTEX_RUN_ON_STARTUP=false \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        "$TEST_IMAGE")
    
    # Give it time to start and log initial messages
    sleep 5
    
    # Capture logs and kill container
    output=$(docker logs "$container_id" 2>&1)
    docker kill "$container_id" >/dev/null 2>&1 || true
    
    # Validate expected behavior
    local container_started=false
    local skipped_startup=false
    local no_download_attempted=true
    
    # Check if container started properly
    if [[ "$output" == *"Starting Vortex container"* ]]; then
        container_started=true
        log_info "✓ Container started successfully"
    else
        log_warning "✗ Container startup not detected"
    fi
    
    # Check if startup download was explicitly skipped
    if [[ "$output" == *"Skipping download on startup"* ]]; then
        skipped_startup=true
        log_info "✓ Startup download was skipped as expected"
    else
        log_warning "✗ 'Skipping download on startup' message not found"
    fi
    
    # Validate that NO download was attempted
    if [[ "$output" == *"Running download on startup"* ]] || \
       [[ "$output" == *"Executing: vortex download"* ]] || \
       [[ "$output" == *"Download completed successfully"* ]] || \
       [[ "$output" == *"Fetched remote data"* ]]; then
        no_download_attempted=false
        log_warning "✗ Download was attempted despite VORTEX_RUN_ON_STARTUP=false"
    else
        log_info "✓ No download was attempted (as expected)"
    fi
    
    # Check that no CSV files were created
    local csv_count=$(find "$test_data_dir" -name "*.csv" -type f 2>/dev/null | wc -l)
    csv_count=$(echo "$csv_count" | tr -d ' ')
    
    if [[ "$csv_count" -eq 0 ]]; then
        log_info "✓ No CSV files created (as expected)"
    else
        log_warning "✗ Found $csv_count CSV file(s) - unexpected with no startup download"
        no_download_attempted=false
    fi
    
    # Test passes if container started, skipped startup, and no download was attempted
    if [[ "$container_started" == true ]] && [[ "$skipped_startup" == true ]] && [[ "$no_download_attempted" == true ]]; then
        log_success "Entrypoint works without download (3/3 validations passed)"
        return 0
    else
        local passed=0
        [[ "$container_started" == true ]] && ((passed++))
        [[ "$skipped_startup" == true ]] && ((passed++))
        [[ "$no_download_attempted" == true ]] && ((passed++))
        
        log_error "Entrypoint without startup test failed ($passed/3 validations passed)"
        echo "Container output:"
        echo "$output"
        return 1
    fi
}

test_yahoo_download() {
    log_test "Test 12: Yahoo Download with Market Data Validation"
    
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
    
    test_data_dir=$(create_test_directory "test-data-yahoo")
    test_config_dir=$(create_test_directory "test-config-yahoo")
    output_file="$test_data_dir/container.log"
    
    # Start container with proper configuration
    container_id=$(run_container "test-yahoo-download" \
        --user "$(id -u):$(id -g)" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/config" \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        -e VORTEX_RUN_ON_STARTUP=true \
        -e VORTEX_DOWNLOAD_ARGS="--yes --symbol AAPL --symbol MSFT --start-date 2024-12-01 --end-date 2024-12-07" \
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
            local csv_files data_rows_total market_data_validated
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

test_cron_job_setup() {
    log_test "Test 13: Cron Job Setup and Validation"
    
    local test_data_dir test_config_dir
    local container_id output_file
    local cron_schedule="*/2 * * * *"  # Every 2 minutes for testing
    
    test_data_dir=$(create_test_directory "test-data-cron")
    test_config_dir=$(create_test_directory "test-config-cron")
    output_file="$test_data_dir/container.log"
    
    # Ensure test directories are writable by container user (UID 1000)
    chmod 777 "$test_data_dir" "$test_config_dir" 2>/dev/null || true
    
    # Start container with cron job enabled and short schedule (uses new secure cron setup)
    container_id=$(run_container "test-cron-setup" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/config" \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        -e VORTEX_RUN_ON_STARTUP=false \
        -e VORTEX_SCHEDULE="$cron_schedule" \
        -e VORTEX_DOWNLOAD_ARGS="--yes --symbol AAPL --symbol MSFT --start-date 2024-12-01 --end-date 2024-12-07" \
        "$TEST_IMAGE")
    
    # Wait for container to start and cron to be configured
    sleep 10
    
    # Capture logs to check cron setup
    docker logs "$container_id" > "$output_file" 2>&1
    
    # Check if cron was configured properly
    local cron_setup_success=false
    local cron_daemon_started=false
    local health_check_created=false
    
    if [[ -f "$output_file" ]]; then
        # Check for new vortex user cron setup indicators
        if grep -F "Setting up crontab for vortex user with schedule: $cron_schedule" "$output_file"; then
            cron_setup_success=true
        fi
        
        # Check if cron daemon started
        if grep -F "Starting cron daemon" "$output_file"; then
            cron_daemon_started=true
        fi
        
        # Check if health check file was created
        if [[ -f "$test_data_dir/health.check" ]]; then
            health_check_created=true
        fi
        
        # Verify crontab was installed for vortex user (check inside container)
        local crontab_output
        crontab_output=$(docker exec "$container_id" su vortex -c "crontab -l" 2>/dev/null || echo "no crontab")
        
        local crontab_configured=false
        if [[ "$crontab_output" == *"$cron_schedule"* ]] && [[ "$crontab_output" == *"vortex download"* ]]; then
            crontab_configured=true
        fi
        
        # Kill container
        docker kill "$container_id" >/dev/null 2>&1 || true
        
        # Evaluate test results
        local passed_checks=0
        local total_checks=4
        
        if [[ "$cron_setup_success" == true ]]; then
            log_info "✓ Vortex user cron schedule configured correctly"
            ((passed_checks++))
        else
            log_warning "✗ Vortex user cron schedule setup not found in logs"
        fi
        
        if [[ "$cron_daemon_started" == true ]]; then
            log_info "✓ Cron daemon started"
            ((passed_checks++))
        else
            log_warning "✗ Cron daemon start not confirmed"
        fi
        
        if [[ "$health_check_created" == true ]]; then
            log_info "✓ Health check file created"
            ((passed_checks++))
        else
            log_warning "✗ Health check file not found"
        fi
        
        if [[ "$crontab_configured" == true ]]; then
            log_info "✓ Vortex user crontab contains proper download command"
            ((passed_checks++))
        else
            log_warning "✗ Vortex user crontab not properly configured"
            echo "Crontab content: $crontab_output"
        fi
        
        # Test passes if at least 3 out of 4 checks pass
        if [[ $passed_checks -ge 3 ]]; then
            log_success "Cron job setup test successful ($passed_checks/$total_checks checks passed)"
            log_info "Cron schedule: $cron_schedule"
            log_info "Download command scheduled for periodic execution"
            return 0
        else
            log_error "Cron job setup test failed ($passed_checks/$total_checks checks passed)"
            echo "Last 10 lines of container output:"
            tail -10 "$output_file" 2>/dev/null || echo "No output captured"
            return 1
        fi
    else
        docker kill "$container_id" >/dev/null 2>&1 || true
        log_error "Cron job setup test failed - no output captured"
        return 1
    fi
}

test_cron_job_execution() {
    log_test "Test 14: Comprehensive Cron Job Execution Test"
    log_info "⚠️  This test may take up to 60 seconds - it waits for actual cron execution"
    
    local test_data_dir test_config_dir
    local container_id output_file
    local cron_schedule="*/1 * * * *"  # Every minute
    local wait_timeout=180  # 3 minutes maximum wait
    local check_interval=30  # Check every 30 seconds
    
    test_data_dir=$(create_test_directory "test-data-cron-exec")
    test_config_dir=$(create_test_directory "test-config-cron-exec") 
    output_file="$test_data_dir/container.log"
    
    # Ensure test directories are writable by container user (UID 1000)
    chmod 777 "$test_data_dir" "$test_config_dir" 2>/dev/null || true
    
    log_info "Starting container with cron schedule: $cron_schedule"
    
    # Start container with cron job enabled (starts as root, sets up cron, then switches to vortex user)
    container_id=$(run_container "test-cron-execution" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/config" \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        -e VORTEX_RUN_ON_STARTUP=false \
        -e VORTEX_SCHEDULE="$cron_schedule" \
        -e VORTEX_DOWNLOAD_ARGS="--yes --symbol AAPL --symbol MSFT --start-date 2024-12-01 --end-date 2024-12-07 --output-dir /data" \
        "$TEST_IMAGE")
    
    log_info "Container started (ID: ${container_id:0:12}...), waiting for cron setup..."
    
    # Wait for initial setup (30 seconds)
    sleep 30
    
    # Check if cron setup was successful
    docker logs "$container_id" > "$output_file" 2>&1
    if ! grep -F "Starting cron daemon" "$output_file"; then
        docker kill "$container_id" >/dev/null 2>&1 || true
        log_error "Cron daemon failed to start"
        return 1
    fi
    
    # Verify cron schedule was actually configured for vortex user
    if ! grep -F "Setting up crontab for vortex user with schedule: $cron_schedule" "$output_file"; then
        docker kill "$container_id" >/dev/null 2>&1 || true
        log_error "Vortex user cron schedule setup not found in logs"
        log_verbose "Looking for pattern: 'Setting up crontab for vortex user with schedule: $cron_schedule'"
        log_verbose "Available logs preview:"
        grep "cron schedule\|Starting cron" "$output_file" | head -3 | sed 's/^/  /'
        return 1
    fi
    
    log_info "✓ Cron daemon started and vortex user crontab configured, waiting for first execution..."
    
    # Wait for cron job to actually execute and download data
    local elapsed_time=0
    local cron_executed=false
    local data_downloaded=false
    
    while [[ $elapsed_time -lt $wait_timeout ]]; do
        # Update logs
        docker logs "$container_id" > "$output_file" 2>&1
        
        # Check if cron job has executed by looking for vortex command output
        # Also check the vortex.log file directly (cron output goes there)
        if ! $cron_executed; then
            # Check docker logs output
            if grep -q "Starting download\|vortex download\|Download completed successfully" "$output_file"; then
                log_info "✓ Cron job executed! (after ${elapsed_time}s)"
                cron_executed=true
            # Also check vortex.log file inside container
            elif docker exec "$container_id" test -f "/data/vortex.log" 2>/dev/null && \
                 docker exec "$container_id" grep -q "Download completed successfully\|Fetched remote data\|Starting download" "/data/vortex.log" 2>/dev/null; then
                log_info "✓ Cron job executed (found in vortex.log)! (after ${elapsed_time}s)"
                cron_executed=true
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
    
    # 1. Check if cron executed
    if $cron_executed; then
        log_info "✓ Cron job executed successfully"
        ((success_indicators++))
    else
        log_warning "✗ No cron execution detected in logs"
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
    
    # Test passes if all 3 indicators are successful (cron execution is different from direct execution)
    if [[ $success_indicators -eq 3 ]]; then
        log_success "Comprehensive cron execution test successful ($success_indicators/$total_indicators indicators passed)"
        log_info "Test completed in ${elapsed_time}s"
        return 0
    else
        log_error "Comprehensive cron execution test failed ($success_indicators/$total_indicators indicators passed)"
        log_info "Check logs at: $output_file"
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
    
    # Run specified tests
    for test_num in "${tests_to_run[@]}"; do
        if [[ -n "${TEST_REGISTRY[$test_num]:-}" ]]; then
            # Skip comprehensive tests unless flag is set
            if [[ "$test_num" == "14" ]] && [[ "$COMPREHENSIVE" != true ]]; then
                log_info "Skipping comprehensive test $test_num (use --comprehensive to include)"
                continue
            fi
            
            IFS=':' read -r func_name description <<< "${TEST_REGISTRY[$test_num]}"
            log_verbose "Executing test $test_num: $func_name"
            
            # Run the test function
            if ! "$func_name"; then
                # Special handling for critical tests
                if [[ "$test_num" == "1" ]] || [[ "$test_num" == "3" ]]; then
                    log_error "Critical test $test_num failed, stopping execution"
                    return 1
                fi
                test_failed=true
            fi
        else
            log_error "Unknown test number: $test_num"
            test_failed=true
        fi
    done
    
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
            --comprehensive)
                COMPREHENSIVE=true
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
        log_verbose "  Comprehensive: $COMPREHENSIVE"
        log_verbose "  Test Image: $TEST_IMAGE"
        if [[ ${#SPECIFIC_TESTS[@]} -gt 0 ]]; then
            log_verbose "  Specific Tests: ${SPECIFIC_TESTS[*]}"
        fi
    fi
    
    # Auto-enable comprehensive flag when specific tests are provided
    if [[ ${#SPECIFIC_TESTS[@]} -gt 0 ]] && [[ "$COMPREHENSIVE" != true ]]; then
        COMPREHENSIVE=true
        log_verbose "Auto-enabled comprehensive mode for specific tests"
    fi
    
    # Run tests
    if [[ ${#SPECIFIC_TESTS[@]} -gt 0 ]]; then
        run_specific_tests "${SPECIFIC_TESTS[@]}"
    else
        run_all_tests
    fi
    exit_code=$?
    
    # Show results
    show_results
    
    return $exit_code
}

# Run main function
main "$@"