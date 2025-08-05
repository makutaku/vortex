# Environment Variables

Set these environment variables before running vortex:

## Modern Configuration (VORTEX_* variables)

### General Settings
```bash
export VORTEX_DEFAULT_PROVIDER=yahoo  # Default: yahoo
export VORTEX_OUTPUT_DIR="/path/to/data"  # Default: ./data
export VORTEX_LOG_LEVEL=INFO  # Default: INFO
export VORTEX_BACKUP_ENABLED=true  # Default: false
export VORTEX_DRY_RUN=false  # Default: false
```

### Barchart Provider
```bash
export VORTEX_BARCHART_USERNAME="your_barchart_username"
export VORTEX_BARCHART_PASSWORD="your_barchart_password"
export VORTEX_BARCHART_DAILY_LIMIT=150  # Default: 150
```

### Interactive Brokers Provider  
```bash
export VORTEX_IBKR_HOST="localhost"  # Default: localhost
export VORTEX_IBKR_PORT=7497  # Default: 7497
export VORTEX_IBKR_CLIENT_ID=1  # Default: 1
export VORTEX_IBKR_TIMEOUT=30  # Default: 30
```

### Yahoo Finance Provider
```bash
# Yahoo Finance requires no configuration - works out of the box
export VORTEX_DEFAULT_PROVIDER=yahoo
```

## Docker/Container Configuration
```dockerfile
ENV VORTEX_DEFAULT_PROVIDER=yahoo
ENV VORTEX_OUTPUT_DIR=/data
ENV VORTEX_LOG_LEVEL=INFO
ENV VORTEX_RUN_ON_STARTUP=true
ENV VORTEX_DOWNLOAD_ARGS="--yes"
```

## Docker Compose Example
```yaml
services:
  vortex:
    image: vortex:latest
    environment:
      - VORTEX_DEFAULT_PROVIDER=yahoo
      - VORTEX_OUTPUT_DIR=/data
      - VORTEX_SCHEDULE=0 8 * * *
      - VORTEX_RUN_ON_STARTUP=true
    volumes:
      - ./data:/data
```

## Systemd Service Example
```ini
[Service]
Environment=VORTEX_DEFAULT_PROVIDER=yahoo
Environment=VORTEX_OUTPUT_DIR=/var/lib/vortex/data
EnvironmentFile=-/etc/vortex/credentials
```

## Migration from Legacy BCU_* Variables

The modern Vortex configuration system uses `VORTEX_*` environment variables. Legacy `BCU_*` variables are no longer supported. Here's the mapping:

| Legacy (BCU_*)           | Modern (VORTEX_*)              |
|-------------------------|--------------------------------|
| BCU_USERNAME            | VORTEX_BARCHART_USERNAME       |
| BCU_PASSWORD            | VORTEX_BARCHART_PASSWORD       |
| BCU_OUTPUT_DIR          | VORTEX_OUTPUT_DIR              |
| BCU_DAILY_DOWNLOAD_LIMIT| VORTEX_BARCHART_DAILY_LIMIT    |
| BCU_PROVIDER_HOST       | VORTEX_IBKR_HOST               |
| BCU_PROVIDER_PORT       | VORTEX_IBKR_PORT               |
| BCU_LOGGING_LEVEL       | VORTEX_LOG_LEVEL               |
| BCU_BACKUP_DATA         | VORTEX_BACKUP_ENABLED          |
| BCU_DRY_RUN             | VORTEX_DRY_RUN                 |
| BCU_DOWNLOADER          | VORTEX_DEFAULT_PROVIDER        |