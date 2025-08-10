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
    
    # Use dynamic cron scheduling instead of fixed intervals
    log_info "Using dynamic cron scheduling for: $VORTEX_SCHEDULE"
    
    # Remove quotes from VORTEX_SCHEDULE for supervisord (it will be inside double quotes)
    VORTEX_SCHEDULE_CLEAN="${VORTEX_SCHEDULE//\"/}"
    
    cat > /home/vortex/.config/supervisor/conf.d/vortex-scheduler.conf << EOF
[program:vortex-scheduler]
command=/home/vortex/vortex-scheduler.sh
user=vortex
autostart=true
autorestart=true
stderr_logfile=/home/vortex/logs/vortex-scheduler.err.log
stdout_logfile=/home/vortex/logs/vortex-scheduler.out.log
environment=HOME="/home/vortex",VORTEX_OUTPUT_DIR="$VORTEX_OUTPUT_DIR",VORTEX_DOWNLOAD_ARGS="$VORTEX_DOWNLOAD_ARGS",VORTEX_SCHEDULE="$VORTEX_SCHEDULE_CLEAN"
EOF

    # Create scheduler script with comprehensive cron parser
    cat > /home/vortex/vortex-scheduler.sh << 'EOF'
#!/bin/bash
# Advanced cron-compatible scheduler for Vortex
set -euo pipefail

VORTEX_SCHEDULE="${VORTEX_SCHEDULE:-0 8 * * *}"
VORTEX_OUTPUT_DIR="${VORTEX_OUTPUT_DIR:-/data}"
VORTEX_DOWNLOAD_ARGS="${VORTEX_DOWNLOAD_ARGS:---yes}"

echo "[$(date)] Vortex cron scheduler started with schedule: $VORTEX_SCHEDULE"

# Function to parse cron field and check if current value matches
match_cron_field() {
    local field="$1"
    local current="$2"
    local min_val="$3"
    local max_val="$4"
    
    # Handle wildcard
    [[ "$field" == "*" ]] && return 0
    
    # Handle step values (e.g., */5, 0-30/10)
    if [[ "$field" =~ ^(.+)/([0-9]+)$ ]]; then
        local base="${BASH_REMATCH[1]}"
        local step="${BASH_REMATCH[2]}"
        
        if [[ "$base" == "*" ]]; then
            # */N pattern - check if current % step == 0
            [[ $((current % step)) -eq 0 ]] && return 0
        else
            # Range/step pattern (e.g., 0-30/10)
            if [[ "$base" =~ ^([0-9]+)-([0-9]+)$ ]]; then
                local start="${BASH_REMATCH[1]}"
                local end="${BASH_REMATCH[2]}"
                # Check if current is in range and matches step
                [[ $current -ge $start && $current -le $end && $(((current - start) % step)) -eq 0 ]] && return 0
            fi
        fi
        return 1
    fi
    
    # Handle ranges (e.g., 1-5)
    if [[ "$field" =~ ^([0-9]+)-([0-9]+)$ ]]; then
        local start="${BASH_REMATCH[1]}"
        local end="${BASH_REMATCH[2]}"
        [[ $current -ge $start && $current -le $end ]] && return 0
        return 1
    fi
    
    # Handle comma-separated lists (e.g., 1,3,5)
    if [[ "$field" =~ , ]]; then
        IFS=',' read -ra values <<< "$field"
        for value in "${values[@]}"; do
            [[ "$value" == "$current" ]] && return 0
        done
        return 1
    fi
    
    # Handle single value
    [[ "$field" == "$current" ]] && return 0
    return 1
}

# Function to check if current time matches cron schedule
matches_cron_schedule() {
    local schedule="$1"
    local now_min now_hour now_day now_month now_dow
    
    # Get current time components
    now_min=$(date +%M | sed 's/^0*//')   # Remove leading zeros
    now_hour=$(date +%H | sed 's/^0*//')
    now_day=$(date +%d | sed 's/^0*//')
    now_month=$(date +%m | sed 's/^0*//')
    now_dow=$(date +%w)  # 0=Sunday, 1=Monday, etc.
    
    # Handle empty values (treat as 0)
    [[ -z "$now_min" ]] && now_min=0
    [[ -z "$now_hour" ]] && now_hour=0
    [[ -z "$now_day" ]] && now_day=1
    [[ -z "$now_month" ]] && now_month=1
    
    # Parse cron schedule: minute hour day month dow
    read -r cron_min cron_hour cron_day cron_month cron_dow <<< "$schedule"
    
    echo "[$(date)] Checking schedule: min=$cron_min hour=$cron_hour day=$cron_day month=$cron_month dow=$cron_dow"
    echo "[$(date)] Current time: min=$now_min hour=$now_hour day=$now_day month=$now_month dow=$now_dow"
    
    # Check each field
    match_cron_field "$cron_min" "$now_min" 0 59 || return 1
    match_cron_field "$cron_hour" "$now_hour" 0 23 || return 1  
    match_cron_field "$cron_day" "$now_day" 1 31 || return 1
    match_cron_field "$cron_month" "$now_month" 1 12 || return 1
    match_cron_field "$cron_dow" "$now_dow" 0 7 || return 1  # 0 and 7 both = Sunday
    
    return 0
}

# Function to calculate seconds until next minute boundary
seconds_to_next_minute() {
    local current_seconds
    current_seconds=$(date +%S | sed 's/^0*//')
    [[ -z "$current_seconds" ]] && current_seconds=0
    echo $((60 - current_seconds))
}

echo "[$(date)] Starting cron scheduler loop..."

# Main scheduling loop - check every minute
while true; do
    if matches_cron_schedule "$VORTEX_SCHEDULE"; then
        echo "[$(date)] Running scheduled vortex download..."
        
        if vortex download --output-dir "$VORTEX_OUTPUT_DIR" $VORTEX_DOWNLOAD_ARGS; then
            echo "[$(date)] ✓ Scheduled download completed successfully"
        else
            echo "[$(date)] ✗ Scheduled download failed with exit code $?"
        fi
        
        # Sleep for at least 60 seconds to avoid running twice in the same minute
        echo "[$(date)] Sleeping for 60 seconds to avoid duplicate runs..."
        sleep 60
    else
        # Sleep until the next minute boundary for precise timing
        sleep_seconds=$(seconds_to_next_minute)
        echo "[$(date)] Next check in ${sleep_seconds}s (at next minute boundary)"
        sleep "$sleep_seconds"
    fi
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