# Docker Deployment Guide

Vortex can be deployed as a Docker container for automated, scheduled downloads of financial data.

## Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/makutaku/vortex.git
   cd vortex
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Set up credentials** (for Barchart)
   ```bash
   mkdir -p config
   cat > config/config.toml << EOF
   [providers.barchart]
   username = "your_email@example.com"
   password = "your_password"
   EOF
   ```

4. **Run with Docker Compose**
   ```bash
   docker compose up -d
   ```

## Configuration

### Environment Variables

The following environment variables control the container behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `VORTEX_PROVIDER` | `barchart` | Data provider: `barchart`, `yahoo`, or `ibkr` |
| `VORTEX_SCHEDULE` | `0 8 * * *` | Cron schedule for downloads |
| `VORTEX_RUN_ON_STARTUP` | `True` | Run download when container starts |
| `VORTEX_DOWNLOAD_ARGS` | `--yes` | Additional arguments for download command |
| `VORTEX_ASSETS_FILE` | `/config/assets.json` | Path to custom assets file |
| `VORTEX_LOG_LEVEL` | `INFO` | Logging level |
| `DATA_DIR` | `./data` | Host directory for downloaded data (maps to `/data` in container) |
| `CONFIG_DIR` | `./config` | Host directory for configuration (maps to `/config` in container) |

### Provider-Specific Setup

#### Barchart
Requires credentials in `config/config.toml`:
```toml
[providers.barchart]
username = "your_email@example.com"
password = "your_password"
daily_limit = 150
```

#### Yahoo Finance
No credentials required. Just set:
```bash
VORTEX_PROVIDER=yahoo
```

#### Interactive Brokers
Requires TWS/Gateway running. Configure in `config/config.toml`:
```toml
[providers.ibkr]
host = "host.docker.internal"  # To connect to TWS on host
port = 7497
client_id = 1
```

## Volume Mounts

The container uses two volumes:

- `/data` - Downloaded data files (CSV/Parquet)
- `/config` - Configuration files (config.toml, custom assets.json)

## Custom Assets

To use a custom list of instruments:

1. Create your assets file:
   ```bash
   cp assets/default.json config/my-assets.json
   # Edit config/my-assets.json
   ```

2. Update `.env`:
   ```bash
   VORTEX_ASSETS_FILE=/config/my-assets.json
   ```

## Scheduling

The default schedule runs daily at 8 AM. Common schedules:

- `0 8 * * *` - Daily at 8 AM
- `0 */6 * * *` - Every 6 hours
- `0 8 * * 1-5` - Weekdays only at 8 AM
- `0 16 * * *` - Daily at 4 PM (after market close)

## Monitoring

### Logs
```bash
# View container logs
docker compose logs -f vortex

# View download logs
tail -f data/vortex.log
```

### Health Check
The container creates `data/health.check` hourly. Monitor this file to ensure the container is running.

### Status
```bash
# Check container status
docker compose ps

# View cron jobs
docker compose exec vortex crontab -l
```

## Advanced Usage

### Multiple Providers

Run multiple containers for different providers:

```yaml
services:
  vortex-yahoo:
    build:
      context: .
      dockerfile: Dockerfile.simple
    container_name: vortex-yahoo
    environment:
      VORTEX_PROVIDER: yahoo
      VORTEX_SCHEDULE: "0 9 * * *"
    volumes:
      - ./data/yahoo:/data
      - ./config:/config

  vortex-barchart:
    build:
      context: .
      dockerfile: Dockerfile.simple
    container_name: vortex-barchart
    environment:
      VORTEX_PROVIDER: barchart
      VORTEX_SCHEDULE: "0 10 * * *"
    volumes:
      - ./data/barchart:/data
      - ./config:/config
```

### Date Range Control

To download specific date ranges:

```bash
VORTEX_DOWNLOAD_ARGS="--yes --start-date 2024-01-01 --end-date 2024-12-31"
```

### Specific Symbols

To download only specific symbols:

```bash
VORTEX_DOWNLOAD_ARGS="--yes --symbol AAPL MSFT GOOGL"
```

### Force Re-download

To re-download existing data:

```bash
VORTEX_DOWNLOAD_ARGS="--yes --force"
```

## Troubleshooting

### Permission Issues
Ensure the host directories are writable:
```bash
mkdir -p data config
chmod 755 data config
```

### Connection Issues (IBKR)
If connecting to TWS on the host machine:
- Use `host.docker.internal` as the host
- Ensure TWS API is enabled
- Check firewall settings

### Memory Issues
Adjust resource limits in `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      memory: 2G
```

## Security Considerations

1. **Credentials**: Store credentials in `config/config.toml`, not in environment variables
2. **File Permissions**: Ensure config files are readable only by the container user
3. **Network**: Use internal networks if running with other services
4. **Updates**: Regularly rebuild the image to get security updates

## Building Custom Image

### Dockerfile Options

Two Dockerfiles are available:

- **`Dockerfile`** - Multi-stage build with uv (smaller final image, faster builds)
- **`Dockerfile.simple`** - Single-stage build with pip (more reliable, slower)

The docker-compose.yml uses `Dockerfile.simple` by default for reliability.

### Custom Build

To build with specific Python version or dependencies:

```dockerfile
# Custom Dockerfile
FROM python:3.12-slim AS builder
# ... rest of Dockerfile
```

```bash
docker build -t my-vortex:latest .
```

Update `docker-compose.yml`:
```yaml
services:
  vortex:
    image: my-vortex:latest
    # ... rest of config
```