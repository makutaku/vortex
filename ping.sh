#!/bin/bash

timestamp=$(date -u +"%Y-%m-%d %H:%M:%S")

if [ -n "$BARCHART_USERNAME" ] && [ -n "$BARCHART_PASSWORD" ]; then
    echo "$timestamp PING"
else
    echo "$timestamp ERROR Either BARCHART_USERNAME or BARCHART_PASSWORD environment variables are not set or empty."
fi
