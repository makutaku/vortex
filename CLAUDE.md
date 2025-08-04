# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Vortex is a Python automation library for downloading historic futures contract prices from Barchart.com. It automates the manual process of downloading individual contracts and supports multiple data providers including Barchart, Yahoo Finance, and Interactive Brokers.

## Development Commands

### Environment Setup

**🚀 Using uv (Recommended - 10-100x faster than pip):**
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
# or on Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Create virtual environment and install vortex with all dependencies
uv venv .venv
source .venv/bin/activate  # Linux/Mac
# or .venv\Scripts\activate  # Windows

# Install vortex in development mode
uv pip install -e .

# Or install specific dependency groups
uv pip install -e ".[dev]"     # Development dependencies
uv pip install -e ".[test]"    # Testing dependencies
uv pip install -e ".[lint]"    # Linting dependencies
```

**⚠️ IMPORTANT for Local Development:**
Always use the virtual environment setup above for local testing and development. Do NOT rely solely on Docker for testing - use Docker only for deployment testing. The virtual environment provides:
- Faster testing cycles (no Docker build overhead)
- Better debugging with direct access to stack traces
- Proper dependency resolution and imports
- Real development workflow with all Python tooling

**Alternative methods:**
```bash
# Method 2: Traditional pip (slower)
pip install -e .

# Method 3: Install from PyPI (when published)
uv pip install vortex
# or: pip install vortex
```

### Testing

**🚀 Local Testing (Recommended):**
```bash
# First, ensure virtual environment is set up and activated
source .venv/bin/activate

# Test CLI functionality locally
vortex --help
vortex providers --list
vortex config --show

# Run unit tests with uv
uv run pytest src/vortex/tests/
uv run pytest src/vortex/tests/test_downloader.py

# With coverage
uv run pytest --cov=vortex src/vortex/tests/

# Install test dependencies and run
uv pip install -e ".[test]"
uv run pytest
```

**🐳 Docker Testing (For Deployment Validation):**
```bash
# Only use Docker for final deployment testing
./scripts/test-docker-build.sh

# Traditional method (slower, use only if uv unavailable)
pytest src/vortex/tests/
```

### Code Quality
```bash
# Using uv (recommended)
uv pip install -e ".[lint]"
uv run flake8 src/vortex/
uv run black src/vortex/ --check
uv run isort src/vortex/ --check-only

# Format code
uv run black src/vortex/
uv run isort src/vortex/

# Traditional method
flake8 src/vortex/
black src/vortex/
isort src/vortex/
```

### Modern CLI Usage
```bash
# After installation, use the modern CLI interface:

# Get help
vortex --help
vortex download --help

# Configure credentials
vortex config --provider barchart --set-credentials
vortex config --show

# Download data
vortex download --provider barchart --symbol GC --start-date 2024-01-01
vortex download --provider yahoo --symbol AAPL GOOGL MSFT
vortex download --provider ibkr --symbols-file symbols.txt

# Manage providers
vortex providers --list
vortex providers --test barchart
vortex providers --info barchart

# Validate data
vortex validate --path ./data
vortex validate --path ./data/GC.csv --provider barchart
```


## Architecture

### Core Components

**Data Providers** (`vortex/data_providers/`):
- `BarchartDataProvider`: Scrapes data from Barchart.com with authentication
- `YahooDataProvider`: Downloads data from Yahoo Finance API
- `IbkrDataProvider`: Connects to Interactive Brokers TWS/Gateway
- Base `DataProvider` interface for extensibility

**Data Storage** (`vortex/data_storage/`):
- `CsvStorage`: Saves data in CSV format
- `ParquetStorage`: Backup storage in Parquet format
- `FileStorage`: Base file storage abstraction
- `metadata.py`: Handles data metadata tracking

**Downloaders** (`vortex/downloaders/`):
- `UpdatingDownloader`: Main downloader that checks for existing data
- `BackfillDownloader`: Downloads historical data ranges
- `MockDownloader`: For testing without real API calls
- `DownloadJob`: Represents individual download tasks

**Instruments** (`vortex/instruments/`):
- `Instrument`: Base class for tradeable instruments
- `Future`: Futures contracts with expiry cycles
- `Stock`: Stock instruments
- `Forex`: Currency pairs
- `PriceSeries`: Time series data representation

**Configuration** (`vortex/config.py`):
- `VortexConfig`: Main configuration object with Pydantic validation
- `ConfigManager`: Modern configuration management system
- Environment variable support with VORTEX_* naming

**CLI Interface** (`vortex/cli/`):
- `main.py`: Modern CLI entry point with Click framework
- `commands/`: Download, config, providers, validate commands
- `utils/`: Configuration manager and instrument parsing

### Key Files

- `vortex/cli/commands/download.py`: Contains the modern CLI download command with integrated downloader factory logic
- `vortex/cli/main.py`: Modern CLI entry point using Click framework
- `assets/`: Default instrument definitions directory
- `scripts/build.sh`: Build script for creating distribution artifacts

### Configuration Management

The modern CLI supports multiple configuration methods:

**Interactive Configuration (Recommended):**
```bash
vortex config --provider barchart --set-credentials
vortex config --provider ibkr --set-credentials
```


**Configuration File (~/.config/vortex/config.toml):**
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

### Assets Configuration

The `assets/` directory contains default instrument definitions that ship with Vortex. These are example asset lists to get users started:

- `assets/barchart.json` - Default instruments for Barchart.com
- `assets/yahoo.json` - Default instruments for Yahoo Finance  
- `assets/ibkr.json` - Default instruments for Interactive Brokers
- `assets/default.json` - General default instruments

Users can provide their own custom assets file using the `--assets` option:
```bash
# Use your own custom assets file
vortex download --provider yahoo --assets /path/to/my-assets.json

# Or use the defaults by not specifying --assets
vortex download --provider yahoo --symbol AAPL
```

Each assets file defines futures, forex, and stock instruments with metadata like trading cycles, tick dates, and periods. Users can maintain a single assets file for all providers or create provider-specific files based on their needs.

### Data Flow

1. Configuration loaded from `assets/` directory and environment variables
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
- Modern CLI works in containers: `docker run vortex vortex --help`

### Testing Strategy

Tests use pytest with fixture-based setup. The main test file `test_downloader.py` validates credential handling and download functionality with temporary directories.

## 🚨 CRITICAL: Docker Test Protection

**Tests 5 and 12 frequently break during refactoring. Follow these rules to prevent breakage:**

### Test 5: Providers Command (`vortex providers`)

**What it tests:** CLI command functionality and provider plugin loading
**Common breakage patterns:**
- ❌ Moving plugin exception files without updating imports
- ❌ Changing CLI command syntax/options  
- ❌ Breaking dependency injection system
- ❌ Import errors in command modules

**Protection Rules:**
1. **BEFORE moving any exception files:** Check all `__init__.py` files that import them
2. **AFTER refactoring imports:** Always test: `docker run --rm vortex-test:latest vortex providers`
3. **When changing CLI commands:** Update corresponding test scripts immediately
4. **Plugin system changes:** Verify plugin registry can load all 3 providers (BARCHART, YAHOO, IBKR)

**Expected behavior:** Shows table with "Total providers available: 3"

### Test 12: Yahoo Download (`vortex download --symbol AAPL`)

**What it tests:** End-to-end download functionality with real data
**Common breakage patterns:**
- ❌ Docker permission issues (container user vs host user)
- ❌ CLI argument changes not reflected in test environment variables
- ❌ Output directory path assumptions
- ❌ Success detection patterns changed

**Protection Rules:**
1. **Container user consistency:** Always use `--user "1000:1000"` in Docker tests
2. **Permission management:** Ensure test directories are writable by container user
3. **Success detection:** Test looks for "Fetched remote data" and "Download completed successfully"
4. **File validation:** Expects CSV files in `test-data-yahoo/stocks/1d/AAPL.csv`

**Expected behavior:** Downloads AAPL data and creates CSV file

### 🛡️ Refactoring Checklist

**BEFORE any major refactoring:**
```bash
# 1. Run full Docker test to establish baseline
./scripts/test-docker-build.sh

# 2. Note which tests pass
# 3. After refactoring, run again and compare
```

**AFTER refactoring (MANDATORY):**
```bash
# 1. Quick validation script (recommended)
./scripts/validate-critical-tests.sh

# 2. Manual validation (if needed)
docker run --rm vortex-test:latest vortex providers | grep "Total providers available"
docker run --rm vortex-test:latest vortex --help | grep "Commands:"

# 3. If either fails, fix IMMEDIATELY before committing
# 4. Run full test suite to confirm
./scripts/test-docker-build.sh
```

### 🔧 Quick Debug Commands

**Test 5 debugging:**
```bash
# Check if commands are available
docker run --rm vortex-test:latest python3 -c "
from vortex.cli.dependencies import get_availability_summary
print(get_availability_summary())
"

# Test provider imports
docker run --rm vortex-test:latest python3 -c "
from vortex.plugins import get_provider_registry
registry = get_provider_registry()
print(f'Providers: {registry.list_plugins()}')
"
```

**Test 12 debugging:**
```bash
# Check download with verbose logging
docker run --rm --user "1000:1000" -v "$(pwd)/debug:/data" vortex-test:latest \
  vortex download --symbol AAPL --output-dir /data --yes -v
```

### 📋 Import Movement Checklist

**When moving exception/plugin files:**
1. ✅ Update the file being moved
2. ✅ Update all `__init__.py` files that import it
3. ✅ Search codebase for old import paths: `grep -r "from.*old_path"`
4. ✅ Update plugin registrations if applicable
5. ✅ Rebuild Docker image: `docker build -t vortex-test:latest .`
6. ✅ Test both CLI commands: `vortex providers` and `vortex download --help`

### 🎯 Success Criteria

**Test 5 SUCCESS indicators:**
- Providers table displays with 3 providers
- No "requires dependencies" error messages
- All 3 plugins load: barchart, yahoo, ibkr

**Test 12 SUCCESS indicators:**  
- "Fetched remote data: (X, Y), AAPL" in logs
- "Download completed successfully" message
- CSV file created: `find test-data-yahoo -name "*.csv"`
- No permission denied errors

### 🚫 Never Break These Patterns

1. **Plugin Exception Imports:** Always check `vortex/plugins/__init__.py` when moving exception files
2. **CLI Command Registration:** Verify dependency injection system works after import changes
3. **Docker User Permissions:** Always use consistent user ID (1000:1000) in tests
4. **Success Detection:** Don't change log messages that tests depend on for validation

**Remember: Tests 5 and 12 are integration tests that validate the entire system works end-to-end. They catch real user-facing issues that unit tests miss.**

### 🎓 Lessons Learned from Recent Breakages

**Import Simplification (Import Dependencies):**
- ✅ **What worked:** Centralized dependency injection eliminated scattered try/catch blocks
- ❌ **What broke:** Didn't update `plugins/__init__.py` when moving `plugins/exceptions.py` → `exceptions/plugins.py`
- 🛡️ **Prevention:** Always check `__init__.py` files when moving modules

**Error Handling Consolidation:**
- ✅ **What worked:** Standardized templates and consolidated handlers
- ❌ **What broke:** CLI command syntax changes not reflected in test script (`--list` option removed)
- 🛡️ **Prevention:** Update test scripts immediately when changing CLI interfaces

**Docker Permission Issues:**
- ✅ **What worked:** Using consistent container user (1000:1000)  
- ❌ **What broke:** Host/container user ID mismatches causing permission denied
- 🛡️ **Prevention:** Always use `--user "1000:1000"` and proper directory permissions

### 🔄 Refactoring Safety Pattern

**The Safe Refactoring Workflow:**
1. **Baseline:** `./scripts/test-docker-build.sh` (establish what works)
2. **Refactor:** Make your changes
3. **Quick Check:** `./scripts/validate-critical-tests.sh` (catch obvious breaks)
4. **Fix Immediately:** Don't proceed until Tests 5 & 12 pass
5. **Full Validation:** `./scripts/test-docker-build.sh` (ensure nothing else broke)
6. **Commit:** Only after all tests pass

**This pattern prevents the cascade failures where one broken test leads to debugging rabbit holes.**