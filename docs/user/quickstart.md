# Vortex Quickstart Guide

Quick guide to get started with Vortex financial data automation.

## Installation

See [installation.md](installation.md) for detailed installation instructions.

## Configuration (Choose One Method)

### Option 1: TOML Configuration (RECOMMENDED)

```bash
# Copy example configuration
cp config/config.toml.example config/config.toml

# Edit config/config.toml with your settings
# For free Yahoo Finance data (no credentials needed):
[general]
default_provider = "yahoo"

# For premium Barchart data:
[general] 
default_provider = "barchart"

[providers.barchart]
username = "your_email@example.com"
password = "your_password"
```

### Option 2: Interactive Configuration

```bash
# Configure credentials interactively
vortex config --provider barchart --set-credentials

# Or set environment variables
export VORTEX_DEFAULT_PROVIDER=yahoo
export VORTEX_BARCHART_USERNAME="your_email@example.com"
```

## Basic Usage

```bash
# Get help
vortex --help

# Download data (uses configuration from config.toml or environment)
vortex download --symbol AAPL

# Download with specific provider
vortex download --provider yahoo --symbol AAPL MSFT GOOGL

# Download for date range
vortex download --provider barchart --symbol GC --start-date 2024-01-01
```

## Docker Deployment

```bash
# Clone repository
git clone https://github.com/makutaku/vortex.git
cd vortex

# Create configuration
cp config/config.toml.example config/config.toml
# Edit config/config.toml with your settings

# Run with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f
```

## Configuration Precedence

Vortex uses this precedence order for configuration:
1. **Environment Variables** (highest priority)
2. **TOML Configuration** (`config/config.toml`)
3. **Application Defaults** (lowest priority)

## Next Steps

- Review [environment-variables.md](environment-variables.md) for environment variable reference
- See [Docker Guide](../DOCKER.md) for container deployment
- Check the main [README.md](../../README.md) for comprehensive documentation