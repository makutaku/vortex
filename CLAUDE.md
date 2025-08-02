# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

bc-utils is a Python automation library for downloading historic futures contract prices from Barchart.com. It automates the manual process of downloading individual contracts and supports multiple data providers including Barchart, Yahoo Finance, and Interactive Brokers.

## Development Commands

### Environment Setup
```bash
# Using uv (recommended - faster and more reliable)
# Install uv if not already installed: curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv bcutils_env
source bcutils_env/bin/activate  # Linux/Mac
# or bcutils_env\Scripts\activate  # Windows
uv pip install -r requirements.txt

# Alternative: use uv sync if pyproject.toml has dependencies defined
# uv sync
```

### Testing
```bash
# Run tests using pytest
pytest bcutils/tests/

# Run specific test
pytest bcutils/tests/test_downloader.py
```

### Code Quality
```bash
# Lint with flake8 (defined in pyproject.toml dev dependencies)
flake8 bcutils/

# Type checking (if available)
# No specific type checker configured, but code uses type hints
```

### Building and Deployment
```bash
# Build the project (creates build/ directory with processed files)
./build.sh

# Run the main application
./run_bc_utils.sh

# Container entrypoint
./entrypoint.sh
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

### Key Files

- `bcutils/bc_utils.py`: Main entry point with downloader factory functions
- `config.json`: Comprehensive instrument definitions (futures, forex, stocks)
- `build.sh`: Build script that processes env files and copies artifacts
- `run_bc_utils.sh`: Runtime script that activates environment and runs main module

### Environment Configuration

The application uses environment files in `env_files/` for different data providers:
- `barchart.env`: Barchart.com credentials
- `yahoo.env`: Yahoo Finance settings
- `ibkr.env`: Interactive Brokers connection details

Environment variables are interpolated during build using `scripts/interpolate_vars.sh`.

### Data Flow

1. Configuration loaded from `config.json` and environment variables
2. Appropriate downloader created based on data provider
3. Instrument definitions processed to generate download jobs
4. Data downloaded and stored in both CSV (primary) and Parquet (backup) formats
5. Existing data checked to avoid duplicate downloads

### Container Support

The project includes Docker support:
- `entrypoint.sh`: Container initialization with permission checks and cron scheduling
- `cronfile`: Scheduled execution configuration
- `ping.sh`: Health check utility

### Testing Strategy

Tests use pytest with fixture-based setup. The main test file `test_downloader.py` validates credential handling and download functionality with temporary directories.