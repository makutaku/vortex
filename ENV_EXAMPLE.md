# Environment Variables

Set these environment variables before running vortex:

## Barchart Data Provider
```bash
export BCU_DOWNLOADER=create_barchart_downloader
export BCU_USERNAME="your_barchart_username"
export BCU_PASSWORD="your_barchart_password"
export BCU_OUTPUT_DIR="/path/to/data/barchart"
export BCU_DAILY_DOWNLOAD_LIMIT=240
```

## Interactive Brokers Data Provider  
```bash
export BCU_DOWNLOADER=create_ibkr_downloader
export BCU_PROVIDER_HOST="192.168.1.13"
export BCU_PROVIDER_PORT="8888"
export BCU_OUTPUT_DIR="/path/to/data/ibkr"
```

## Yahoo Finance Data Provider
```bash
export BCU_DOWNLOADER=create_yahoo_downloader
export BCU_OUTPUT_DIR="/path/to/data/yahoo"
```

## Common Settings
```bash
export BCU_BACKUP_DATA=True
export BCU_DRY_RUN=False
export BCU_LOGGING_LEVEL=DEBUG
export BCU_START_YEAR=2024
export BCU_REPO_DIR=/vortex
export BCU_CONFIG_FILE="/path/to/config.json"
```

## Container/Docker Example
```dockerfile
ENV BCU_DOWNLOADER=create_barchart_downloader
ENV BCU_OUTPUT_DIR=/data/barchart
ENV BCU_LOGGING_LEVEL=INFO
```

## Systemd Service Example
```ini
[Service]
Environment=BCU_DOWNLOADER=create_barchart_downloader
Environment=BCU_OUTPUT_DIR=/var/lib/vortex/data
EnvironmentFile=-/etc/vortex/credentials
```