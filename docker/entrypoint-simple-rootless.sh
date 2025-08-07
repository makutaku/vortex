#!/bin/bash
#
# Simple Root-less Entrypoint Script for Vortex
# Runs entirely as vortex user (UID 1000) with minimal complexity
# Uses supervisord for process management instead of system cron
#
set -euo pipefail

# Simple logging function
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] INFO: $1"
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] WARNING: $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1"
}

# Ensure we're running as vortex user
if [[ "$(id -u)" -ne 1000 ]]; then
    log_error "This script must run as vortex user (UID 1000), currently running as UID $(id -u)"
    exit 1
fi

log_info "Starting Vortex container as vortex user ($(whoami))..."

# Set environment
export HOME=/home/vortex
VORTEX_CONFIG_DIR="${HOME}/.config/vortex"
VORTEX_OUTPUT_DIR="${VORTEX_OUTPUT_DIR:-/data}"
VORTEX_DEFAULT_PROVIDER="${VORTEX_DEFAULT_PROVIDER:-yahoo}"
VORTEX_RUN_ON_STARTUP="${VORTEX_RUN_ON_STARTUP:-true}"
VORTEX_DOWNLOAD_ARGS="${VORTEX_DOWNLOAD_ARGS:---yes}"
VORTEX_SCHEDULE="${VORTEX_SCHEDULE:-0 8 * * *}"

# Create configuration directory
mkdir -p "$VORTEX_CONFIG_DIR" || {
    log_error "Cannot create config directory: $VORTEX_CONFIG_DIR"
    exit 1
}

# Create minimal configuration
log_info "Creating vortex configuration..."
cat > "$VORTEX_CONFIG_DIR/config.toml" << EOF
# Vortex Configuration (automatically generated)
[general]
output_directory = "$VORTEX_OUTPUT_DIR"
backup_enabled = false
default_provider = "$VORTEX_DEFAULT_PROVIDER"

[providers.barchart]
# Set VORTEX_BARCHART_USERNAME and VORTEX_BARCHART_PASSWORD environment variables

[providers.yahoo]
# No configuration required - works out of the box

[providers.ibkr]
host = "localhost"
port = 7497
client_id = 1
EOF

# Run startup download if enabled
if [[ "$VORTEX_RUN_ON_STARTUP" == "true" ]]; then
    log_info "Running vortex download on startup..."
    download_cmd="vortex download --output-dir $VORTEX_OUTPUT_DIR $VORTEX_DOWNLOAD_ARGS"
    log_info "Executing: $download_cmd"
    
    if eval "$download_cmd"; then
        log_info "Startup download completed successfully"
    else
        log_warning "Startup download failed with exit code $?, continuing anyway..."
    fi
fi

# Simple scheduling: if scheduling is enabled, run once and exit
# For continuous scheduling, use docker-compose restart policies or external schedulers
if [[ "$VORTEX_SCHEDULE" != "# DISABLED" && "$VORTEX_SCHEDULE" != "" ]]; then
    log_info "Simple container - scheduling handled by external systems"
    log_info "Configured schedule: $VORTEX_SCHEDULE"
    log_info "Use docker-compose restart policies or external schedulers for recurring runs"
fi

# Keep container running with a simple monitoring loop
log_info "Container startup complete. Monitoring..."
while true; do
    # Simple health check
    if vortex config --show >/dev/null 2>&1; then
        log_info "Health check passed"
    else
        log_warning "Health check failed"
    fi
    
    # Wait 1 hour between health checks
    sleep 3600
done