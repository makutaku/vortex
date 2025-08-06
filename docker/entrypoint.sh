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
    
    # Create config directory at user home location
    if ! mkdir -p "$(dirname "$VORTEX_CONFIG_DIR")" "$VORTEX_CONFIG_DIR" 2>/dev/null; then
        # Fallback to temp directory if home not writable
        VORTEX_CONFIG_DIR="/tmp/.vortex"
        mkdir -p "$VORTEX_CONFIG_DIR"
        log_warning "Using fallback config directory: $VORTEX_CONFIG_DIR"
    fi
    
    # Check if config.toml exists
    if [ ! -f "$VORTEX_CONFIG_DIR/config.toml" ]; then
        log_info "Creating default config.toml..."
        
        # Try to create config file, with fallback on failure
        if ! {
            cat > "$VORTEX_CONFIG_DIR/config.toml" << 'EOF'
# Vortex Configuration (automatically generated)
[general]
output_directory = "/data"
backup_enabled = false
default_provider = "yahoo"

[general.logging]
level = "INFO"
format = "console"

[providers.barchart]
# Set credentials via environment variables
daily_limit = 150

[providers.yahoo]
# No configuration required - works out of the box

[providers.ibkr]
host = "localhost"
port = 7497
client_id = 1
EOF
        } 2>/dev/null; then
            # Fallback if config file creation fails
            VORTEX_CONFIG_DIR="/tmp/.vortex"
            mkdir -p "$VORTEX_CONFIG_DIR"
            log_warning "Config file creation failed, using fallback: $VORTEX_CONFIG_DIR"
            cat > "$VORTEX_CONFIG_DIR/config.toml" << 'EOF'
# Vortex Configuration (automatically generated)
[general]
output_directory = "/data"
backup_enabled = false
default_provider = "yahoo"

[general.logging]
level = "INFO"
format = "console"

[providers.barchart]
# Set credentials via environment variables
daily_limit = 150

[providers.yahoo]
# No configuration required - works out of the box

[providers.ibkr]
host = "localhost"
port = 7497
client_id = 1
EOF
        fi
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
        log_info "Setting up user crontab with schedule: $VORTEX_SCHEDULE"
        
        # Create cron entry for current user (vortex or root)
        cat > /tmp/vortex-cron << EOF
SHELL=/bin/bash
PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Vortex download schedule
$VORTEX_SCHEDULE $(build_download_command) >> $VORTEX_OUTPUT_DIR/vortex.log 2>&1

# Health check
0 * * * * date > $VORTEX_OUTPUT_DIR/health.check
EOF
        
        # Install crontab for current user
        if crontab /tmp/vortex-cron 2>/dev/null; then
            log_info "User crontab installed successfully for user $(whoami)"
        else
            log_warning "Failed to install user crontab - cron jobs will not run"
        fi
        rm -f /tmp/vortex-cron
    fi
}

# Function to setup crontab for vortex user (called when running as root)
setup_user_crontab() {
    VORTEX_SCHEDULE="${VORTEX_SCHEDULE:-0 8 * * *}"
    VORTEX_OUTPUT_DIR="${VORTEX_OUTPUT_DIR:-/data}"
    
    if [ -n "$VORTEX_SCHEDULE" ]; then
        log_info "Setting up crontab for vortex user with schedule: $VORTEX_SCHEDULE"
        
        # Create cron entry for vortex user
        cat > /tmp/vortex-user-cron << EOF
SHELL=/bin/bash
PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
HOME=/home/vortex

# Vortex download schedule (running as vortex user)
$VORTEX_SCHEDULE $(build_download_command) >> $VORTEX_OUTPUT_DIR/vortex.log 2>&1

# Health check (running as vortex user)
0 * * * * date > $VORTEX_OUTPUT_DIR/health.check
EOF
        
        # Install crontab for vortex user (using su to switch user)
        if su vortex -c "crontab /tmp/vortex-user-cron" 2>/dev/null; then
            log_info "Crontab installed successfully for vortex user"
        else
            log_warning "Failed to install crontab for vortex user"
        fi
        rm -f /tmp/vortex-user-cron
    fi
}

# Main execution
main() {
    log_info "Starting Vortex container with modern configuration..."
    
    # Initialize cron daemon as root if needed
    if [ "$(id -u)" -eq 0 ] && [ -n "$VORTEX_SCHEDULE" ]; then
        log_info "Starting cron daemon as root for proper initialization..."
        if command -v cron >/dev/null 2>&1; then
            cron || log_warning "Cron daemon failed to start"
        else
            log_warning "Cron not available in container"
        fi
    fi
    
    # Set HOME if not set (happens with --user flag)  
    if [ -z "$HOME" ] || [ "$HOME" = "/" ]; then
        if [ "$(id -u)" -eq 0 ]; then
            HOME="/root"
        else
            HOME="/home/vortex"
        fi
        export HOME
    fi
    
    # Set defaults for required directories
    VORTEX_OUTPUT_DIR="${VORTEX_OUTPUT_DIR:-/data}"
    VORTEX_CONFIG_DIR="${VORTEX_CONFIG_DIR:-$HOME/.config/vortex}"
    VORTEX_RUN_ON_STARTUP="${VORTEX_RUN_ON_STARTUP:-true}"
    
    # Validate required directories
    if ! check_write_permission "$VORTEX_OUTPUT_DIR"; then
        log_error "Output directory $VORTEX_OUTPUT_DIR is not writable"
        exit 1
    fi
    
    # Check config directory permissions (with fallback)
    if ! check_write_permission "$(dirname "$VORTEX_CONFIG_DIR")" 2>/dev/null; then
        log_warning "Config directory $(dirname "$VORTEX_CONFIG_DIR") not writable, will use fallback"
    fi
    
    # Setup configuration
    setup_configuration
    
    # Display configuration summary
    log_info "Configuration summary:"
    log_info "  Default Provider: ${VORTEX_DEFAULT_PROVIDER:-yahoo}"
    log_info "  Output Directory: $VORTEX_OUTPUT_DIR"
    log_info "  Config Directory: $VORTEX_CONFIG_DIR"
    log_info "  Schedule: ${VORTEX_SCHEDULE:-0 8 * * *}"
    
    # Setup cron schedule (as root, but install for vortex user if we're root)
    if [ "$(id -u)" -eq 0 ] && [ -n "$VORTEX_SCHEDULE" ]; then
        # Setup crontab for vortex user
        setup_user_crontab
    else
        # Setup crontab for current user
        update_cron_schedule
    fi
    
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
    
    # Start cron daemon
    log_info "Starting cron daemon..."
    if command -v cron >/dev/null 2>&1; then
        if [ "$(id -u)" -eq 0 ]; then
            # Running as root - start cron daemon directly
            cron || log_warning "Cron daemon failed to start"
        else
            # Running as non-root - cron daemon should be started by init system
            log_info "Running as non-root user $(whoami) - cron daemon should be managed by system"
            # Check if cron daemon is already running
            if ! pgrep -x cron >/dev/null 2>&1; then
                log_warning "Cron daemon not running and cannot start as non-root user"
                log_info "User crontab jobs will not execute without running cron daemon"
            else
                log_info "Cron daemon is running - user crontab jobs will execute"
            fi
        fi
    else
        log_warning "Cron not available in container"
    fi
    
    # Create initial health check
    date > "$VORTEX_OUTPUT_DIR/health.check"
    
    # Switch to vortex user for main application if we started as root
    if [ "$(id -u)" -eq 0 ]; then
        log_info "Switching to vortex user for main application..."
        # Ensure vortex user owns data directories
        chown -R vortex:vortex "$VORTEX_OUTPUT_DIR" "$VORTEX_CONFIG_DIR" /home/vortex
        # Switch to vortex user and tail logs
        log_info "Vortex container is ready. Tailing logs as vortex user..."
        touch "$VORTEX_OUTPUT_DIR/vortex.log"
        chown vortex:vortex "$VORTEX_OUTPUT_DIR/vortex.log"
        exec su vortex -c "tail -f $VORTEX_OUTPUT_DIR/vortex.log"
    else
        # Already running as non-root user
        log_info "Vortex container is ready. Tailing logs..."
        touch "$VORTEX_OUTPUT_DIR/vortex.log"
        tail -f "$VORTEX_OUTPUT_DIR/vortex.log"
    fi
}

# Run main function
main "$@"