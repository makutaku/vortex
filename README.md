# Vortex

**Professional financial data download automation with modern CLI interface**

[Barchart.com](https://www.barchart.com) allows registered users to download historic futures contract prices in CSV format. Individual contracts must be downloaded separately, which is laborious and slow. Vortex automates this process with support for multiple data providers including Barchart, Yahoo Finance, and Interactive Brokers.

## 🚀 Quick Start

### Option 1: CLI Installation (uv recommended - 10x faster)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install Vortex
uv pip install -e .

# Configure and run
vortex config --provider barchart --set-credentials
vortex download --provider barchart --symbol GC --start-date 2024-01-01
```

### Option 2: Docker Deployment (Automated Downloads)

```bash
# Clone repository
git clone https://github.com/makutaku/vortex.git
cd vortex

# Configuration Option 1 (RECOMMENDED): TOML Configuration
cp config/config.toml.example config/config.toml
# Edit config/config.toml with your settings

# Configuration Option 2: Environment Variables
cp .env.example .env
# Edit .env with your provider and schedule
# Then uncomment environment variables in docker/docker-compose.yml

# Run with Docker Compose
docker compose up -d

# Check logs
docker compose logs -f
```

See [Docker Guide](docs/DOCKER.md) for detailed setup.

## 📚 Legacy Python API

```
from vortex import get_barchart_downloads, create_bc_session

CONTRACTS={
    "AUD":{"code":"A6","cycle":"HMUZ","tick_date":"2009-11-24"},
    "GOLD": {"code": "GC", "cycle": "GJMQVZ", "tick_date": "2008-05-04"}
}

session = create_bc_session(config_obj=dict(
    barchart_username="user@domain.com",
    barchart_password = "s3cr3t_321")
)

get_barchart_downloads(
    session,
    contract_map=CONTRACTS,
    save_directory='/home/user/contract_data',
    start_year=2020,
    end_year=2021
)
```

The code above would: 
* for the CME Australian Dollar future, get hourly OHLCV data for the Mar, Jun, Sep and Dec 2020 contracts
* download in CSV format
* save with filenames AUD_20200300.csv, AUD_20200600.csv, AUD_20200900.csv, AUD_20201200.csv into the specified directory
* for COMEX Gold, get Feb, Apr, Jun, Aug, Oct, and Dec data, with filenames like GOLD_20200200.csv etc

## ✨ Features

**Modern CLI Interface:**
- Professional command-line interface with Click framework
- Rich terminal output with colors and progress bars
- Interactive configuration management
- Multiple output formats (table, JSON, CSV)
- Comprehensive help system

**Multiple Data Providers:**
- **Barchart**: Professional futures and options data
- **Yahoo Finance**: Free stock and ETF data
- **Interactive Brokers**: Real-time data via TWS/Gateway

**Smart Data Management:**
- Automatic duplicate detection and handling
- Incremental downloads (skip existing data)
- Data validation and integrity checks
- CSV and Parquet storage formats
- **Raw data audit trail** with compressed storage for compliance
- Configurable date ranges and chunking
- **Correlation tracking** for end-to-end request monitoring

**Production Monitoring:**
- **Complete Prometheus + Grafana monitoring stack**
- Real-time provider performance and success rate tracking
- **17+ pre-configured alert rules** for system health
- Circuit breaker monitoring and automatic recovery
- **Professional Grafana dashboards** with business metrics
- Docker monitoring stack with Node Exporter
- **Correlation ID tracking** across all operations

**Configuration Options:**
- Interactive credential setup with guided wizards
- **Enhanced TOML configuration** with validation
- **Complete environment variable override** support
- Multiple configuration precedence (ENV > TOML > Defaults)
- **Raw data storage configuration** for audit trails
- **Metrics and monitoring configuration**

## 📊 Production Monitoring

Vortex includes enterprise-grade monitoring capabilities for production deployments:

### Quick Setup
```bash
# Start complete monitoring stack
docker compose -f docker/docker-compose.monitoring.yml up -d

# Enable metrics in Vortex  
export VORTEX_METRICS_ENABLED=true
# or set in config.toml: [general.metrics] enabled = true

# Access dashboards
open http://localhost:3000  # Grafana (admin/admin123)
open http://localhost:9090  # Prometheus  
open http://localhost:8000/metrics  # Vortex metrics endpoint
```

### Available Metrics
- **Provider Performance**: Request duration, success rates, error tracking by provider
- **Download Metrics**: Row counts, download volumes, completion rates per symbol
- **Circuit Breaker Status**: Real-time state monitoring and failure tracking  
- **System Health**: Active operations, memory/CPU usage, storage performance
- **Business Logic**: Authentication failures, quota exceeded alerts, raw data storage
- **Correlation Tracking**: End-to-end request monitoring with unique correlation IDs
- **Raw Data Audit**: Storage metrics, compression ratios, retention compliance

### CLI Monitoring Commands
```bash
# Metrics Management
vortex metrics status          # Check metrics system status
vortex metrics endpoint        # Show metrics URL  
vortex metrics test            # Generate test metrics
vortex metrics summary         # Show metrics activity summary
vortex metrics dashboard       # Show dashboard URLs

# System Resilience
vortex resilience status       # Circuit breaker status
vortex resilience reset        # Reset all circuit breakers
vortex resilience recovery     # Error recovery statistics
vortex resilience health       # Overall system health

# Enhanced Validation
vortex validate --enhanced     # Advanced validation with new formats
vortex validate --summary      # Validation summary display
```

## 📖 Documentation

- [Installation Guide](docs/user/installation.md) - Comprehensive setup instructions
- [CLI Reference](CLAUDE.md#modern-cli-usage) - Command examples and usage  
- [Configuration Guide](CLAUDE.md#configuration-management) - Setup and credentials
- [Development Guide](CLAUDE.md#development-commands) - Contributing and development
- [Monitoring Guide](docs/DOCKER.md#monitoring) - Production monitoring setup
- [Docker Guide](docs/DOCKER.md) - Container deployment and troubleshooting
- [Security Guide](docs/security/CREDENTIAL-MANAGEMENT.md) - Credential management

## 🗂️ Raw Data Storage & Compliance

Vortex automatically maintains audit trails of all provider responses:

### Features
- **Compliance Ready**: Untampered raw data storage for regulatory requirements
- **Compressed Storage**: Automatic gzip compression for efficient storage
- **Rich Metadata**: Correlation IDs, request parameters, timestamps
- **Configurable Retention**: Set retention periods from 1-365 days or unlimited
- **Structured Organization**: `raw/{year}/{month}/{instrument_type}/{symbol}_{timestamp}.csv.gz`

### Configuration
```toml
[general.raw]
enabled = true                    # Enable raw data storage
retention_days = 30              # Days to retain (1-365, None for unlimited)
compress = true                  # Gzip compression  
include_metadata = true          # Include .meta.json files
```

```bash
# Environment variables
export VORTEX_RAW_ENABLED=true
export VORTEX_RAW_RETENTION_DAYS=30
export VORTEX_RAW_BASE_DIRECTORY=./raw
```

## 🔧 Alternative Installation Methods

```bash
# Traditional pip (create venv first)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Development installation with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev,test,lint]"

# From PyPI (when published)
uv pip install vortex
```

## 🏗️ Requirements

- **Python 3.9+** (updated from 3.8+)
- Valid credentials for chosen data provider(s)
- For Barchart: Paid subscribers get 150 downloads/day, free users get 5
- For IBKR: Active account and TWS/Gateway running
- **Optional**: Docker for containerized deployment and monitoring
- **Optional**: 1GB+ storage for raw data audit trails (with retention)

