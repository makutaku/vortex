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
    
    # Create config directory at standard location
    VORTEX_CONFIG_DIR="${VORTEX_CONFIG_DIR:-/root/.config/vortex}"
    mkdir -p "$VORTEX_CONFIG_DIR"
    
    # Check if config.toml exists
    if [ ! -f "$VORTEX_CONFIG_DIR/config.toml" ]; then
        log_info "Creating default config.toml..."
        cat > "$VORTEX_CONFIG_DIR/config.toml" << EOF
# Vortex Configuration (automatically generated)
[general]
output_directory = "${VORTEX_OUTPUT_DIR:-/data}"
backup_enabled = ${VORTEX_BACKUP_ENABLED:-false}
default_provider = "${VORTEX_DEFAULT_PROVIDER:-yahoo}"

[general.logging]
level = "${VORTEX_LOG_LEVEL:-INFO}"
format = "${VORTEX_LOGGING_FORMAT:-console}"

[providers.barchart]
# Set credentials via environment variables
daily_limit = ${VORTEX_BARCHART_DAILY_LIMIT:-150}

[providers.yahoo]
# No configuration required - works out of the box

[providers.ibkr]
host = "${VORTEX_IBKR_HOST:-localhost}"
port = ${VORTEX_IBKR_PORT:-7497}
client_id = ${VORTEX_IBKR_CLIENT_ID:-1}
EOF
    fi
    
    log_info "Using configuration directory: $VORTEX_CONFIG_DIR"
}

# Function to build download command
build_download_command() {
    local cmd="vortex download"
    
    # Provider is now handled by configuration system (defaults to yahoo)
    if [ -n "$VORTEX_DEFAULT_PROVIDER" ] && [ "$VORTEX_DEFAULT_PROVIDER" != "yahoo" ]; then
        cmd="$cmd --provider $VORTEX_DEFAULT_PROVIDER"
    fi
    
    # Output directory (ensure it exists)
    VORTEX_OUTPUT_DIR="${VORTEX_OUTPUT_DIR:-/data}"
    mkdir -p "$VORTEX_OUTPUT_DIR"
    cmd="$cmd --output-dir $VORTEX_OUTPUT_DIR"
    
    # Add additional arguments
    if [ -n "$VORTEX_DOWNLOAD_ARGS" ]; then
        cmd="$cmd $VORTEX_DOWNLOAD_ARGS"
    else
        cmd="$cmd --yes"  # Default to non-interactive
    fi
    
    echo "$cmd"
}

# Function to update cron schedule
update_cron_schedule() {
    VORTEX_SCHEDULE="${VORTEX_SCHEDULE:-0 8 * * *}"
    VORTEX_OUTPUT_DIR="${VORTEX_OUTPUT_DIR:-/data}"
    
    if [ -n "$VORTEX_SCHEDULE" ]; then
        log_info "Updating cron schedule to: $VORTEX_SCHEDULE"
        
        # Create cron entry
        cat > /tmp/vortex-cron << EOF
SHELL=/bin/bash
PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Vortex download schedule
$VORTEX_SCHEDULE $(build_download_command) >> $VORTEX_OUTPUT_DIR/vortex.log 2>&1

# Health check
0 * * * * date > $VORTEX_OUTPUT_DIR/health.check
EOF
        
        # Install crontab
        crontab /tmp/vortex-cron
        rm -f /tmp/vortex-cron
    fi
}

# Main execution
main() {
    log_info "Starting Vortex container with modern configuration..."
    
    # Set defaults for required directories
    VORTEX_OUTPUT_DIR="${VORTEX_OUTPUT_DIR:-/data}"
    VORTEX_CONFIG_DIR="${VORTEX_CONFIG_DIR:-/root/.config/vortex}"
    VORTEX_RUN_ON_STARTUP="${VORTEX_RUN_ON_STARTUP:-true}"
    
    # Validate required directories
    if ! check_write_permission "$VORTEX_OUTPUT_DIR"; then
        log_error "Output directory $VORTEX_OUTPUT_DIR is not writable"
        exit 1
    fi
    
    if ! check_write_permission "$(dirname "$VORTEX_CONFIG_DIR")"; then
        log_error "Config parent directory $(dirname "$VORTEX_CONFIG_DIR") is not writable"
        exit 1
    fi
    
    # Setup configuration
    setup_configuration
    
    # Display configuration summary
    log_info "Configuration summary:"
    log_info "  Default Provider: ${VORTEX_DEFAULT_PROVIDER:-yahoo}"
    log_info "  Output Directory: $VORTEX_OUTPUT_DIR"
    log_info "  Config Directory: $VORTEX_CONFIG_DIR"
    log_info "  Schedule: ${VORTEX_SCHEDULE:-0 8 * * *}"
    
    # Update cron schedule
    update_cron_schedule
    
    # Run on startup if enabled
    if [ "$VORTEX_RUN_ON_STARTUP" = "true" ] || [ "$VORTEX_RUN_ON_STARTUP" = "True" ]; then
        log_info "Running download on startup..."
        download_cmd=$(build_download_command)
        log_info "Executing: $download_cmd"
        
        # Execute the command and capture the exit code
        if eval "$download_cmd" 2>&1 | tee -a "$VORTEX_OUTPUT_DIR/vortex.log"; then
            exit_code=0
        else
            exit_code=$?
        fi
        
        if [ $exit_code -eq 0 ]; then
            log_info "Download completed successfully"
        else
            log_error "Download failed with exit code $exit_code"
        fi
    else
        log_info "Skipping download on startup (VORTEX_RUN_ON_STARTUP=$VORTEX_RUN_ON_STARTUP)"
    fi
    
    # Start cron (as root since container runs as root)
    log_info "Starting cron daemon..."
    if command -v cron >/dev/null 2>&1; then
        cron || log_warning "Cron failed to start (permission issue)"
    else
        log_warning "Cron not available"
    fi
    
    # Create initial health check
    date > "$VORTEX_OUTPUT_DIR/health.check"
    
    # Keep container running and tail logs
    log_info "Vortex container is ready. Tailing logs..."
    touch "$VORTEX_OUTPUT_DIR/vortex.log"
    tail -f "$VORTEX_OUTPUT_DIR/vortex.log"
}

# Run main function
main "$@"