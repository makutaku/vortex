#!/bin/bash
# Robust Docker Test Suite for Vortex
# Follows containerized application testing best practices

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

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
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
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_test() {
    echo -e "\n${YELLOW}=== $1 ===${NC}"
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
    log_info "Cleaning up containers..."
    
    for container_id in "${CONTAINERS_TO_CLEANUP[@]}"; do
        if [[ -n "$container_id" ]]; then
            docker kill "$container_id" >/dev/null 2>&1 || true
            docker rm -f "$container_id" >/dev/null 2>&1 || true
        fi
    done
    
    # Clean up any remaining test containers
    docker ps -a --filter "ancestor=$TEST_IMAGE" --format "{{.ID}}" | xargs -r docker rm -f >/dev/null 2>&1 || true
    
    CONTAINERS_TO_CLEANUP=()
}

cleanup_directories() {
    log_info "Cleaning up test directories..."
    
    for dir in "${DIRECTORIES_TO_CLEANUP[@]}"; do
        if [[ -d "$dir" ]]; then
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
    
    cd "$PROJECT_ROOT"
    
    if timeout "$BUILD_TIMEOUT" docker build -t "$TEST_IMAGE" . >/dev/null 2>&1; then
        log_success "Docker build completed successfully"
        return 0
    else
        log_error "Docker build failed"
        return 1
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
    
    if output=$(exec_container 20 "test-help" --entrypoint="" "$TEST_IMAGE" vortex --help 2>&1); then
        if [[ "$output" == *"Vortex: Financial data download automation tool"* ]]; then
            log_success "CLI help command works"
            return 0
        fi
    fi
    
    log_error "CLI help command failed"
    echo "Output: $output"
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
        --entrypoint="" "$TEST_IMAGE" vortex providers 2>&1); then
        
        if [[ "$output" == *"Total providers available"* ]]; then
            log_success "Providers command works"
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
    
    cd "$PROJECT_ROOT"
    
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
        vortex download --help 2>&1); then
        
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
    
    if [[ "$output" == *"Starting Vortex container"* ]] && [[ "$output" == *"Skipping download on startup"* ]]; then
        log_success "Entrypoint works without download"
        return 0
    fi
    
    log_error "Entrypoint without startup test failed"
    echo "Output: $output"
    return 1
}

test_yahoo_download() {
    log_test "Test 12: Yahoo Download (Real Data)"
    
    local test_data_dir test_config_dir
    local container_id output_file
    local success_indicators
    
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
        -e VORTEX_DOWNLOAD_ARGS="--yes --symbol AAPL" \
        "$TEST_IMAGE")
    
    # Wait for download to complete (containers run indefinitely due to tail -f)
    # Need extra time for bot detection delay
    sleep 25
    
    # Capture logs and kill container
    docker logs "$container_id" > "$output_file" 2>&1
    docker kill "$container_id" >/dev/null 2>&1 || true
    
    # Check for success indicators
    if [[ -f "$output_file" ]]; then
        success_indicators=$(grep -c "Fetched remote data\|Download completed successfully\|✓ Completed" "$output_file" 2>/dev/null || echo "0")
        # Ensure it's a single number
        success_indicators=$(echo "$success_indicators" | head -1)
        
        if [[ "$success_indicators" -gt 0 ]]; then
            log_success "Yahoo download test successful"
            log_info "Success indicators found: $success_indicators"
            
            # Show key indicators
            grep -E "(Fetched remote data|Download completed successfully|✓ Completed)" "$output_file" | head -3
            
            # Check for downloaded files
            local csv_files
            csv_files=$(find "$test_data_dir" -name "*.csv" -type f 2>/dev/null | wc -l)
            csv_files=$(echo "$csv_files" | tr -d ' ')  # Remove any whitespace
            if [[ "$csv_files" -gt 0 ]]; then
                log_info "Downloaded files: $csv_files CSV files"
                find "$test_data_dir" -name "*.csv" -type f | head -3
            fi
            
            return 0
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
    
    # Start container with cron job enabled and short schedule
    container_id=$(run_container "test-cron-setup" \
        --user "0:0" \
        -v "$PWD/$test_data_dir:/data" \
        -v "$PWD/$test_config_dir:/config" \
        -e VORTEX_DEFAULT_PROVIDER=yahoo \
        -e VORTEX_RUN_ON_STARTUP=false \
        -e VORTEX_SCHEDULE="$cron_schedule" \
        -e VORTEX_DOWNLOAD_ARGS="--yes --symbol AAPL" \
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
        # Check for cron setup indicators
        if grep -q "Updating cron schedule to: $cron_schedule" "$output_file"; then
            cron_setup_success=true
        fi
        
        # Check if cron daemon started
        if grep -q "Starting cron daemon" "$output_file"; then
            cron_daemon_started=true
        fi
        
        # Check if health check file was created
        if [[ -f "$test_data_dir/health.check" ]]; then
            health_check_created=true
        fi
        
        # Verify crontab was installed (check inside container)
        local crontab_output
        crontab_output=$(docker exec "$container_id" crontab -l 2>/dev/null || echo "no crontab")
        
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
            log_info "✓ Cron schedule configured correctly"
            ((passed_checks++))
        else
            log_warning "✗ Cron schedule setup not found in logs"
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
            log_info "✓ Crontab contains proper download command"
            ((passed_checks++))
        else
            log_warning "✗ Crontab not properly configured"
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

# ============================================================================
# MAIN EXECUTION
# ============================================================================

run_all_tests() {
    log_info "Starting Vortex Docker Test Suite"
    echo "========================================"
    
    # Setup
    setup_test_environment || return 1
    
    # Core tests - continue even if some fail to get full picture
    test_docker_build || return 1  # Critical - must pass
    test_image_details || true
    test_basic_container_startup || return 1  # Critical - must pass  
    test_cli_help || true
    test_providers_command || true
    test_environment_variables || true
    test_volume_mounts || true
    test_entrypoint_dry_run || true
    test_docker_compose_config || true
    test_download_dry_run || true
    test_entrypoint_no_startup || true
    test_yahoo_download || true
    test_cron_job_setup || true
    
    return 0
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

main() {
    local exit_code=0
    
    run_all_tests
    exit_code=$?
    
    show_results
    
    return $exit_code
}

# Run main function
main "$@"