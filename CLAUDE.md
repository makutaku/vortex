# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

bc-utils is a Python automation library for downloading historic futures contract prices from Barchart.com. It automates the manual process of downloading individual contracts and supports multiple data providers including Barchart, Yahoo Finance, and Interactive Brokers.

## Development Commands

### Environment Setup

**🚀 Using uv (Recommended - 10-100x faster than pip):**
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
# or on Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Create virtual environment and install bc-utils with all dependencies
uv venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install bc-utils in development mode
uv pip install -e .

# Or install specific dependency groups
uv pip install -e ".[dev]"     # Development dependencies
uv pip install -e ".[test]"    # Testing dependencies
uv pip install -e ".[lint]"    # Linting dependencies
```

**Alternative methods:**
```bash
# Method 2: Traditional pip (slower)
pip install -e .

# Method 3: Install from PyPI (when published)
uv pip install bc-utils
# or: pip install bc-utils
```

### Testing
```bash
# Using uv (recommended)
uv run pytest src/bcutils/tests/
uv run pytest src/bcutils/tests/test_downloader.py

# With coverage
uv run pytest --cov=bcutils src/bcutils/tests/

# Install test dependencies and run
uv pip install -e ".[test]"
uv run pytest

# Traditional method
pytest src/bcutils/tests/
```

### Code Quality
```bash
# Using uv (recommended)
uv pip install -e ".[lint]"
uv run flake8 src/bcutils/
uv run black src/bcutils/ --check
uv run isort src/bcutils/ --check-only

# Format code
uv run black src/bcutils/
uv run isort src/bcutils/

# Traditional method
flake8 src/bcutils/
black src/bcutils/
isort src/bcutils/
```

### Modern CLI Usage
```bash
# After installation, use the modern CLI interface:

# Get help
bcutils --help
bcutils download --help

# Configure credentials
bcutils config --provider barchart --set-credentials
bcutils config --show

# Download data
bcutils download --provider barchart --symbol GC --start-date 2024-01-01
bcutils download --provider yahoo --symbol AAPL GOOGL MSFT
bcutils download --provider ibkr --symbols-file symbols.txt

# Manage providers
bcutils providers --list
bcutils providers --test barchart
bcutils providers --info barchart

# Validate data
bcutils validate --path ./data
bcutils validate --path ./data/GC.csv --provider barchart
```

### Legacy Shell Script Usage (Deprecated)
```bash
# Legacy method - use CLI instead
./build.sh
export BCU_USERNAME="your_username"
export BCU_PASSWORD="your_password"
export BCU_OUTPUT_DIR="/path/to/data"
./run_bc_utils.sh
```

## Architecture

### Core Components

**Data Providers** (`bcutils/data_providers/`):
- `BarchartDataProvider`: Scrapes data from Barchart.com with authentication
- `YahooDataProvider`: Downloads data from Yahoo Finance API
- `IbkrDataProvider`: Connects to Interactive Brokers TWS/Gateway
- Base `DataProvider` interface for extensibility

**Data Storage** (`bcutils/data_storage/`):
- `CsvStorage`: Saves data in CSV format
- `ParquetStorage`: Backup storage in Parquet format
- `FileStorage`: Base file storage abstraction
- `metadata.py`: Handles data metadata tracking

**Downloaders** (`bcutils/downloaders/`):
- `UpdatingDownloader`: Main downloader that checks for existing data
- `BackfillDownloader`: Downloads historical data ranges
- `MockDownloader`: For testing without real API calls
- `DownloadJob`: Represents individual download tasks

**Instruments** (`bcutils/instruments/`):
- `Instrument`: Base class for tradeable instruments
- `Future`: Futures contracts with expiry cycles
- `Stock`: Stock instruments
- `Forex`: Currency pairs
- `PriceSeries`: Time series data representation

**Configuration** (`bcutils/initialization/`):
- `SessionConfig`: Main configuration object
- `OsEnvironSessionConfig`: Environment variable-based config
- `config_utils.py`: Configuration utilities

**CLI Interface** (`bcutils/cli/`):
- `main.py`: Modern CLI entry point with Click framework
- `commands/`: Download, config, providers, validate commands
- `utils/`: Configuration manager and instrument parsing

### Key Files

- `bcutils/bc_utils.py`: Main entry point with downloader factory functions
- `markets.json`: Comprehensive instrument definitions (futures, forex, stocks)
- `build.sh`: Build script that processes env files and copies artifacts
- `run_bc_utils.sh`: Runtime script that activates environment and runs main module

### Configuration Management

The modern CLI supports multiple configuration methods:

**Interactive Configuration (Recommended):**
```bash
bcutils config --provider barchart --set-credentials
bcutils config --provider ibkr --set-credentials
```

**Environment Variables:**
```bash
export BCU_BARCHART_USERNAME="your_username"
export BCU_BARCHART_PASSWORD="your_password"
export BCU_IBKR_HOST="localhost"
export BCU_IBKR_PORT="7497"
export BCU_OUTPUT_DIR="/path/to/data"
```

**Configuration File (~/.config/bcutils/config.toml):**
```toml
output_directory = "./data"
backup_enabled = true

[providers.barchart]
username = "your_username"
password = "your_password"
daily_limit = 150

[providers.ibkr]
host = "localhost"
port = 7497
client_id = 1
```

### Data Flow

1. Configuration loaded from `markets.json` and environment variables
2. Appropriate downloader created based on data provider
3. Instrument definitions processed to generate download jobs
4. Data downloaded and stored in both CSV (primary) and Parquet (backup) formats
5. Existing data checked to avoid duplicate downloads

### CLI Features

**Modern Python CLI with:**
- Professional command structure using Click framework
- Rich terminal output with colors and progress bars
- Interactive configuration management
- Multiple output formats (table, JSON, CSV)
- Comprehensive help system
- Data validation and integrity checks
- Provider testing and management

**Container Support:**
- Docker support with `entrypoint.sh`
- Cron scheduling with `cronfile`
- Health checks with `ping.sh`
- Modern CLI works in containers: `docker run bc-utils bcutils --help`

### Testing Strategy

Tests use pytest with fixture-based setup. The main test file `test_downloader.py` validates credential handling and download functionality with temporary directories.