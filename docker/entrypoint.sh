#!/bin/bash
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} INFO: $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} ERROR: $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} WARNING: $1"
}

# Function to check write permissions
check_write_permission() {
    local dir=$1
    local testfile="$dir/.test_write_permissions"
    
    if ! touch "$testfile" 2>/dev/null; then
        log_error "Unable to write to directory: $dir"
        return 1
    else
        rm -f "$testfile"
        return 0
    fi
}

# Function to setup configuration
setup_configuration() {
    log_info "Setting up configuration..."
    
    # Create config directory if needed
    mkdir -p "$BCU_CONFIG_DIR"
    
    # Check if config.toml exists
    if [ ! -f "$BCU_CONFIG_DIR/config.toml" ]; then
        log_info "Creating default config.toml..."
        cat > "$BCU_CONFIG_DIR/config.toml" << EOF
# BC-Utils Configuration
output_directory = "/data"
backup_enabled = false
log_level = "${BCU_LOG_LEVEL:-INFO}"

[providers.barchart]
# Set credentials via environment or update here
# username = "your_email@example.com"
# password = "your_password"
daily_limit = 150

[providers.yahoo]
# No configuration required

[providers.ibkr]
host = "localhost"
port = 7497
client_id = 1
EOF
    fi
    
    # Check for assets file
    if [ -n "$BCU_ASSETS_FILE" ] && [ ! -f "$BCU_ASSETS_FILE" ]; then
        # If custom assets file doesn't exist, copy default
        if [ -f "/app/assets/${BCU_PROVIDER}.json" ]; then
            log_info "Copying default assets for provider: $BCU_PROVIDER"
            cp "/app/assets/${BCU_PROVIDER}.json" "$BCU_ASSETS_FILE"
        elif [ -f "/app/assets/default.json" ]; then
            log_info "Copying default assets file"
            cp "/app/assets/default.json" "$BCU_ASSETS_FILE"
        else
            log_warning "No default assets file found"
        fi
    fi
}

# Function to build download command
build_download_command() {
    local cmd="bcutils download"
    
    # Add provider
    cmd="$cmd --provider $BCU_PROVIDER"
    
    # Add output directory (ensure it exists)
    mkdir -p "$BCU_OUTPUT_DIR"
    cmd="$cmd --output-dir $BCU_OUTPUT_DIR"
    
    # Add assets file if specified
    if [ -n "$BCU_ASSETS_FILE" ] && [ -f "$BCU_ASSETS_FILE" ]; then
        cmd="$cmd --assets $BCU_ASSETS_FILE"
    fi
    
    # Always add --yes for non-interactive mode unless explicitly overridden
    if [ -z "$BCU_DOWNLOAD_ARGS" ]; then
        cmd="$cmd --yes"
    else
        cmd="$cmd $BCU_DOWNLOAD_ARGS"
    fi
    
    echo "$cmd"
}

# Function to update cron schedule
update_cron_schedule() {
    if [ -n "$BCU_SCHEDULE" ]; then
        log_info "Updating cron schedule to: $BCU_SCHEDULE"
        
        # Create cron entry
        cat > /tmp/bcutils-cron << EOF
SHELL=/bin/bash
PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# BC-Utils download schedule
$BCU_SCHEDULE $(build_download_command) >> $BCU_OUTPUT_DIR/bcutils.log 2>&1

# Health check
0 * * * * date > $BCU_OUTPUT_DIR/health.check
EOF
        
        # Install crontab
        crontab /tmp/bcutils-cron
        rm -f /tmp/bcutils-cron
    fi
}

# Main execution
main() {
    log_info "Starting BC-Utils container..."
    
    # Validate required directories
    if ! check_write_permission "$BCU_OUTPUT_DIR"; then
        log_error "Output directory $BCU_OUTPUT_DIR is not writable"
        exit 1
    fi
    
    if ! check_write_permission "$BCU_CONFIG_DIR"; then
        log_error "Config directory $BCU_CONFIG_DIR is not writable"
        exit 1
    fi
    
    # Setup configuration
    setup_configuration
    
    # Update cron schedule
    update_cron_schedule
    
    # Run on startup if enabled
    if [ "$BCU_RUN_ON_STARTUP" = "True" ] || [ "$BCU_RUN_ON_STARTUP" = "true" ]; then
        log_info "Running download on startup..."
        download_cmd=$(build_download_command)
        log_info "Executing: $download_cmd"
        
        if $download_cmd 2>&1 | tee -a "$BCU_OUTPUT_DIR/bcutils.log"; then
            log_info "Download completed successfully"
        else
            log_error "Download failed"
        fi
    else
        log_info "Skipping download on startup (BCU_RUN_ON_STARTUP=$BCU_RUN_ON_STARTUP)"
    fi
    
    # Start cron (as root since container runs as root)
    log_info "Starting cron daemon..."
    if command -v cron >/dev/null 2>&1; then
        cron || log_warning "Cron failed to start (permission issue)"
    else
        log_warning "Cron not available"
    fi
    
    # Create initial health check
    date > "$BCU_OUTPUT_DIR/health.check"
    
    # Keep container running and tail logs
    log_info "BC-Utils container is ready. Tailing logs..."
    touch "$BCU_OUTPUT_DIR/bcutils.log"
    tail -f "$BCU_OUTPUT_DIR/bcutils.log"
}

# Run main function
main "$@"