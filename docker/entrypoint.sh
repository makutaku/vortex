#!/bin/bash
#
# Vortex Root-less Entrypoint Script
# Runs entirely as vortex user (UID 1000) for security best practices
# Uses supervisord for process management instead of system cron daemon
#
set -euo pipefail

# Color codes for logging
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} INFO: $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} WARNING: $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} ERROR: $1"
}

# Ensure we're running as vortex user
if [[ "$(id -u)" -ne 1000 ]]; then
    log_error "This script must run as vortex user (UID 1000), currently running as UID $(id -u)"
    exit 1
fi

log_info "Starting Vortex container as vortex user (UID $(id -u))..."

# Set HOME environment
export HOME=/home/vortex

# Configuration setup
VORTEX_CONFIG_DIR="${VORTEX_CONFIG_DIR:-$HOME/.config/vortex}"
VORTEX_OUTPUT_DIR="${VORTEX_OUTPUT_DIR:-/data}"
VORTEX_LOG_LEVEL="${VORTEX_LOG_LEVEL:-INFO}"
VORTEX_DEFAULT_PROVIDER="${VORTEX_DEFAULT_PROVIDER:-yahoo}"
VORTEX_SCHEDULE="${VORTEX_SCHEDULE:-0 8 * * *}"
VORTEX_RUN_ON_STARTUP="${VORTEX_RUN_ON_STARTUP:-true}"
VORTEX_DOWNLOAD_ARGS="${VORTEX_DOWNLOAD_ARGS:---yes}"

log_info "Environment setup:"
log_info "  User: $(whoami) (UID: $(id -u), GID: $(id -g))"
log_info "  Home: $HOME"
log_info "  Config Dir: $VORTEX_CONFIG_DIR"
log_info "  Output Dir: $VORTEX_OUTPUT_DIR"
log_info "  Provider: $VORTEX_DEFAULT_PROVIDER"
log_info "  Schedule: $VORTEX_SCHEDULE"

# Create configuration directory
mkdir -p "$VORTEX_CONFIG_DIR" || {
    log_error "Cannot create config directory: $VORTEX_CONFIG_DIR"
    exit 1
}

# Create default configuration file
log_info "Creating vortex configuration..."
cat > "$VORTEX_CONFIG_DIR/config.toml" << EOF
# Vortex Configuration (automatically generated)
[general]
output_directory = "$VORTEX_OUTPUT_DIR"
backup_enabled = false
default_provider = "$VORTEX_DEFAULT_PROVIDER"

# Logging configuration via environment variables
# VORTEX_LOG_LEVEL = "$VORTEX_LOG_LEVEL"

[providers.barchart]
# Requires credentials via environment variables
# VORTEX_BARCHART_USERNAME and VORTEX_BARCHART_PASSWORD

[providers.yahoo]
# No configuration required - works out of the box

[providers.ibkr]
host = "localhost"
port = 7497
client_id = 1
EOF

# Create supervisord configuration
log_info "Setting up supervisord configuration..."
mkdir -p /home/vortex/.config/supervisor/conf.d /home/vortex/logs

cat > /home/vortex/.config/supervisor/supervisord.conf << EOF
[supervisord]
nodaemon=true
user=vortex
logfile=/home/vortex/logs/supervisord.log
pidfile=/home/vortex/.config/supervisor/supervisord.pid
childlogdir=/home/vortex/logs

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[supervisorctl]
serverurl=unix:///home/vortex/.config/supervisor/supervisor.sock

[unix_http_server]
file=/home/vortex/.config/supervisor/supervisor.sock
chmod=0700

[include]
files = /home/vortex/.config/supervisor/conf.d/*.conf
EOF

# Create vortex download service for supervisord
if [[ "$VORTEX_SCHEDULE" != "# DISABLED" && "$VORTEX_SCHEDULE" != "" ]]; then
    log_info "Setting up scheduled vortex download service with cron schedule: $VORTEX_SCHEDULE"
    
    # Convert cron schedule to sleep interval (simplified for common cases)
    SLEEP_INTERVAL=3600  # Default to 1 hour
    if [[ "$VORTEX_SCHEDULE" == "0 8 * * *" ]]; then
        SLEEP_INTERVAL=86400  # Daily
    elif [[ "$VORTEX_SCHEDULE" =~ ^\*/([0-9]+).* ]]; then
        # Extract minute interval from */N pattern
        INTERVAL="${BASH_REMATCH[1]}"
        SLEEP_INTERVAL=$((INTERVAL * 60))
    fi
    
    cat > /home/vortex/.config/supervisor/conf.d/vortex-scheduler.conf << EOF
[program:vortex-scheduler]
command=/home/vortex/vortex-scheduler.sh
user=vortex
autostart=true
autorestart=true
stderr_logfile=/home/vortex/logs/vortex-scheduler.err.log
stdout_logfile=/home/vortex/logs/vortex-scheduler.out.log
environment=HOME="/home/vortex",VORTEX_OUTPUT_DIR="$VORTEX_OUTPUT_DIR",VORTEX_DOWNLOAD_ARGS="$VORTEX_DOWNLOAD_ARGS",SLEEP_INTERVAL="$SLEEP_INTERVAL"
EOF

    # Create scheduler script in user's home directory
    cat > /home/vortex/vortex-scheduler.sh << 'EOF'
#!/bin/bash
# Simple scheduler that replaces cron functionality
set -euo pipefail

SLEEP_INTERVAL="${SLEEP_INTERVAL:-3600}"
VORTEX_OUTPUT_DIR="${VORTEX_OUTPUT_DIR:-/data}"
VORTEX_DOWNLOAD_ARGS="${VORTEX_DOWNLOAD_ARGS:---yes}"

echo "[$(date)] Vortex scheduler started with interval: ${SLEEP_INTERVAL}s"

while true; do
    echo "[$(date)] Running scheduled vortex download..."
    if vortex download --output-dir "$VORTEX_OUTPUT_DIR" $VORTEX_DOWNLOAD_ARGS; then
        echo "[$(date)] Scheduled download completed successfully"
    else
        echo "[$(date)] Scheduled download failed with exit code $?"
    fi
    
    echo "[$(date)] Sleeping for ${SLEEP_INTERVAL} seconds..."
    sleep "$SLEEP_INTERVAL"
done
EOF
    chmod +x /home/vortex/vortex-scheduler.sh
else
    log_info "Cron scheduling disabled (VORTEX_SCHEDULE='$VORTEX_SCHEDULE')"
fi

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
else
    log_info "Skipping download on startup (VORTEX_RUN_ON_STARTUP=false)"
fi

# Health check setup
log_info "Setting up health monitoring..."
cat > /home/vortex/.config/supervisor/conf.d/health-monitor.conf << EOF
[program:health-monitor]
command=/app/ping.sh
user=vortex
autostart=true
autorestart=true
stderr_logfile=/home/vortex/logs/health-monitor.err.log
stdout_logfile=/home/vortex/logs/health-monitor.out.log
environment=HOME="/home/vortex"
EOF

# Create log file for tail monitoring
touch "$VORTEX_OUTPUT_DIR/vortex.log"

# Start supervisord and monitor logs
log_info "Starting supervisord process manager..."
exec supervisord -c /home/vortex/.config/supervisor/supervisord.conf