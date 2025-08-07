# Docker Deployment Guide

Vortex can be deployed as a Docker container for automated, scheduled downloads of financial data.

## Quick Start (Free Data with Yahoo Finance)

1. **Clone the repository**
   ```bash
   git clone https://github.com/makutaku/vortex.git
   cd vortex
   ```

2. **Run immediately with Yahoo Finance (no setup required)**
   ```bash
   docker compose up -d
   ```

That's it! The container will:
- Use Yahoo Finance (free, no credentials needed)
- Download data to `./data` directory
- Run daily at 8 AM automatically

## Premium Data Setup (Barchart)

**Option 1 (RECOMMENDED): TOML Configuration**
1. **Create TOML configuration**
   ```bash
   cp config/config.toml.example config/config.toml
   # Edit config/config.toml and set:
   ```
   ```toml
   [general]
   default_provider = "barchart"
   
   [providers.barchart]
   username = "your_email@example.com"
   password = "your_password"
   daily_limit = 150
   ```

2. **Run with Barchart**
   ```bash
   docker compose up -d
   ```

**Option 2: Environment Variables**
1. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and set:
   # VORTEX_DEFAULT_PROVIDER=barchart
   # VORTEX_BARCHART_USERNAME=your_email@example.com
   # VORTEX_BARCHART_PASSWORD=your_password
   ```

2. **Uncomment environment variables in docker-compose.yml**
   ```bash
   # Edit docker/docker-compose.yml and uncomment the Barchart environment variables
   ```

3. **Run with Barchart**
   ```bash
   docker compose up -d
   ```

## Configuration

Vortex supports two configuration methods with the following precedence: **Environment Variables > TOML Configuration > Application Defaults**

### Option 1: TOML Configuration (RECOMMENDED)

Create `config/config.toml` with your settings:

```toml
[general]
default_provider = "yahoo"    # yahoo, barchart, or ibkr
backup_enabled = false
dry_run = false

[general.logging]
level = "INFO"               # DEBUG, INFO, WARNING, ERROR
format = "console"           # console, json, rich
output = ["console"]         # console, file, or both

[providers.barchart]
username = "your_email@example.com"
password = "your_password"
daily_limit = 150

[providers.ibkr]
host = "localhost"
port = 7497
client_id = 1
```

See `config/config.toml.example` for complete configuration options.

### Option 2: Environment Variables

If you prefer environment variables, uncomment the relevant sections in `docker/docker-compose.yml`:

**Container-specific variables (always set):**
| Variable | Default | Description |
|----------|---------|-------------|
| `VORTEX_OUTPUT_DIR` | `/data` | Container data directory |
| `VORTEX_SCHEDULE` | `0 8 * * *` | Cron schedule for downloads |
| `VORTEX_RUN_ON_STARTUP` | `true` | Run download when container starts |
| `VORTEX_DOWNLOAD_ARGS` | `--yes` | Additional arguments for download command |
| `DATA_DIR` | `./data` | Host directory for downloaded data |
| `CONFIG_DIR` | `./config` | Host directory for configuration |

**Application variables (optional - use TOML instead):**
| Variable | Default | Description |
|----------|---------|-------------|
| `VORTEX_DEFAULT_PROVIDER` | `yahoo` | Default data provider |
| `VORTEX_LOGGING_LEVEL` | `INFO` | Logging level |
| `VORTEX_LOGGING_FORMAT` | `console` | Log format |
| `VORTEX_BACKUP_ENABLED` | `false` | Enable Parquet backup files |
| `VORTEX_BARCHART_USERNAME` | - | Barchart.com username (email) |
| `VORTEX_BARCHART_PASSWORD` | - | Barchart.com password |
| `VORTEX_BARCHART_DAILY_LIMIT` | `150` | Daily download limit |
| `VORTEX_IBKR_HOST` | `localhost` | Interactive Brokers TWS/Gateway host |
| `VORTEX_IBKR_PORT` | `7497` | Interactive Brokers port |
| `VORTEX_IBKR_CLIENT_ID` | `1` | Interactive Brokers client ID |

### Provider-Specific Setup

#### Yahoo Finance (Default - Free)
No setup required! Yahoo Finance is the default provider and works immediately:
```bash
# Just run - no configuration needed
docker compose up -d
```

#### Barchart (Premium)
Set credentials via environment variables in `.env`:
```bash
VORTEX_DEFAULT_PROVIDER=barchart
VORTEX_BARCHART_USERNAME=your_email@example.com
VORTEX_BARCHART_PASSWORD=your_password
VORTEX_BARCHART_DAILY_LIMIT=150
```

Or in `config/config.toml`:
```toml
[general]
default_provider = "barchart"

[providers.barchart]
username = "your_email@example.com"
password = "your_password"
daily_limit = 150
```

#### Interactive Brokers (Professional)
Requires TWS/Gateway running. Set in `.env`:
```bash
VORTEX_DEFAULT_PROVIDER=ibkr
VORTEX_IBKR_HOST=host.docker.internal  # To connect to TWS on host
VORTEX_IBKR_PORT=7497
VORTEX_IBKR_CLIENT_ID=1
```

Or in `config/config.toml`:
```toml
[general]
default_provider = "ibkr"

[providers.ibkr]
host = "host.docker.internal"
port = 7497
client_id = 1
```

## Volume Mounts

The container uses two main volumes:

- `/data` - Downloaded data files (CSV/Parquet)
- `/home/vortex/.config/vortex` - Vortex configuration directory (config.toml)

The `CONFIG_DIR` environment variable maps your local `./config` directory to `/home/vortex/.config/vortex` in the container. The container runs as the `vortex` user (UID 1000) for security, following best practices for non-root containers.

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
The container runs `vortex config --show` to verify the CLI is working properly. Check health status with:
```bash
docker compose ps
```

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
      VORTEX_DEFAULT_PROVIDER: yahoo
      VORTEX_SCHEDULE: "0 9 * * *"
    volumes:
      - ./data/yahoo:/data
      - ./config/yahoo:/root/.config/vortex

  vortex-barchart:
    build:
      context: .
      dockerfile: Dockerfile.simple
    container_name: vortex-barchart
    environment:
      VORTEX_DEFAULT_PROVIDER: barchart
      VORTEX_BARCHART_USERNAME: ${BARCHART_USERNAME}
      VORTEX_BARCHART_PASSWORD: ${BARCHART_PASSWORD}
      VORTEX_SCHEDULE: "0 10 * * *"
    volumes:
      - ./data/barchart:/data
      - ./config/barchart:/root/.config/vortex
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