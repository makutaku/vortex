#!/bin/bash

# Modern health monitoring script for supervisord
# Provides continuous health status without legacy file creation

while true; do
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    
    # Perform health check - verify vortex CLI is available
    if command -v vortex >/dev/null 2>&1; then
        echo "$timestamp HEALTHY - vortex CLI available"
    else
        echo "$timestamp UNHEALTHY - vortex CLI not found"
        exit 1
    fi
    
    # Check every 30 minutes for responsive monitoring
    sleep 1800
done
