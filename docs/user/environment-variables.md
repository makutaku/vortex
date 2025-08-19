# Environment Variables

Vortex supports multiple configuration methods with the following precedence:
**Environment Variables > TOML Configuration > Application Defaults**

## Configuration Recommendation

**RECOMMENDED**: Use TOML configuration files instead of environment variables for better readability and maintainability:

1. Copy the example configuration: `cp config/config.toml.example config/config.toml`
2. Edit `config/config.toml` with your settings
3. Run vortex normally - it will automatically use the TOML configuration

Environment variables are still supported and will override TOML settings when needed.

## Environment Variables Reference

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

## New Environment Variables (v0.1.4)

The following environment variables were added in version 0.1.4 for enhanced functionality:

### Raw Data Storage
| Variable | Description | Default |
|----------|-------------|---------|
| VORTEX_RAW_ENABLED | Enable raw data audit trail | false |
| VORTEX_RAW_RETENTION_DAYS | Days to retain raw files (1-365) | None (unlimited) |
| VORTEX_RAW_BASE_DIRECTORY | Base directory for raw files | ./raw |
| VORTEX_RAW_COMPRESS | Enable gzip compression | true |
| VORTEX_RAW_INCLUDE_METADATA | Include .meta.json files | true |

### Monitoring & Metrics
| Variable | Description | Default |
|----------|-------------|---------|
| VORTEX_METRICS_ENABLED | Enable Prometheus metrics | false |
| VORTEX_METRICS_PORT | Metrics server port | 8000 |
| VORTEX_METRICS_PATH | Metrics endpoint path | /metrics |
| VORTEX_METRICS_AUTH_USERNAME | Basic auth username | None |
| VORTEX_METRICS_AUTH_PASSWORD | Basic auth password | None |

### Enhanced Logging
| Variable | Description | Default |
|----------|-------------|---------|
| VORTEX_LOGGING_FORMAT | Log format (console, json, structured) | console |
| VORTEX_LOGGING_OUTPUT | Output destinations (console,file,syslog) | console |
| VORTEX_LOGGING_FILE_PATH | Log file path | None |
| VORTEX_LOGGING_FILE_ROTATION | Rotation interval (1d, 1w, 1M) | None |
| VORTEX_LOGGING_FILE_RETENTION | Retention period (30d, 1M, 1y) | None |
| VORTEX_LOGGING_FILE_MAX_SIZE | Max file size before rotation | 100MB |

## Configuration Validation

Vortex validates all environment variables at startup. Invalid values will cause the application to exit with a clear error message:

```bash
# Invalid retention days
export VORTEX_RAW_RETENTION_DAYS=400  # Error: Must be 1-365

# Invalid log level
export VORTEX_LOG_LEVEL=TRACE  # Error: Must be DEBUG, INFO, WARNING, ERROR

# Invalid metrics port
export VORTEX_METRICS_PORT=99999  # Error: Port must be 1-65535
```

## Best Practices

### Production Environment
1. **Use TOML configuration** for complex setups
2. **Store secrets separately** using EnvironmentFile in systemd
3. **Enable monitoring** with VORTEX_METRICS_ENABLED=true
4. **Configure raw data retention** based on compliance requirements
5. **Set up log rotation** to prevent disk space issues

### Development Environment
1. **Use .env files** for local development
2. **Enable debug logging** with VORTEX_LOG_LEVEL=DEBUG
3. **Disable raw data storage** to save disk space
4. **Use shorter retention periods** for testing

### Security Considerations
1. **Never log sensitive environment variables**
2. **Use file-based credential storage** for production
3. **Restrict file permissions** on credential files (600)
4. **Rotate credentials regularly**
5. **Monitor access** to configuration files