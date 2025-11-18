# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# 🚨 CRITICAL WARNING: NO COMMITS WITHOUT PASSING TESTS
**BEFORE doing ANYTHING else in this repository, understand this absolute rule:**
- ⛔ **NEVER commit code unless ALL tests pass**
- ✅ **ALWAYS run `./run-all-tests.sh --skip-docker` before ANY commit**  
- 🛑 **If ANY test fails, fix it FIRST before committing**

See the "🚨 CRITICAL: Commit Requirements" section below for complete details.

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

**🎯 Comprehensive Testing (Recommended):**
```bash
# Run all tests (Python + Docker) - complete validation
./run-all-tests.sh

# Run all tests with verbose output
./run-all-tests.sh -v

# Development workflow - skip slow Docker tests
./run-all-tests.sh --python-only

# Deployment validation - Docker tests only
./run-all-tests.sh --docker-only
```

**🚀 Individual Test Suites:**
```bash
# First, ensure virtual environment is set up and activated
source .venv/bin/activate

# Run specific test categories
uv run pytest tests/unit/        # Unit tests (fast, isolated)
uv run pytest tests/integration/ # Integration tests (multi-component)
uv run pytest tests/e2e/         # End-to-end workflow tests

# With coverage
uv run pytest --cov=vortex tests/

# Test CLI functionality locally
vortex --help
vortex providers --list
vortex config --show
```

**🐳 Docker Testing (For Deployment Validation):**
```bash
# Full Docker test suite (deployment validation)
./tests/docker/test-docker-build.sh

# Quick Docker validation (specific tests)
./tests/docker/test-docker-build.sh 5 12 --quiet
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

### 🚨 CRITICAL: Commit Requirements

# ⛔ ABSOLUTE REQUIREMENT: NO COMMITS WITHOUT PASSING TESTS

**🚫 NEVER, EVER commit code unless ALL tests pass:**

## MANDATORY Pre-Commit Checklist

Before ANY commit, you MUST:

1. **✅ Run the full test suite:**
```bash
# MANDATORY: Run this command before EVERY commit (recommended)
./run-all-tests.sh --fast

# Alternative comprehensive workflow (includes slow E2E tests)  
./run-all-tests.sh --skip-docker
```

2. **✅ Verify ALL test categories pass:**
   - Unit tests (1338+ tests) - **MUST be 100% PASSING**
   - Integration tests (24+ tests) - **MUST be 100% PASSING** 
   - End-to-end tests (15+ tests) - **MUST be 100% PASSING**

3. **✅ Check test output shows:**
   - "✅ Unit Tests PASSED" 
   - "✅ Integration Tests PASSED"
   - "✅ E2E Tests PASSED"

## ⛔ Commit Prohibition Rules

**ABSOLUTELY FORBIDDEN to commit if:**
- ❌ ANY test fails (even 1 test out of 1000+)
- ❌ Test suite shows "FAILED" status
- ❌ You see error messages or stack traces
- ❌ Tests timeout or are interrupted
- ❌ You haven't run the test suite at all

**If ANY test fails:**
- 🛑 **STOP IMMEDIATELY** - Do not proceed with commit
- 🔧 **Fix ALL failing tests first** - No exceptions, no shortcuts
- 🔍 **Debug thoroughly** - Use verbose output (`-v`) to understand failures
- ✅ **Re-run tests** - Ensure 100% pass rate before proceeding
- 📝 **Only commit** when test suite is completely green

## ✅ Correct Commit Workflow

**ALWAYS follow this exact sequence:**

```bash
# 1. Make your changes to the codebase
# 2. Run the mandatory test suite (fast, recommended)
./run-all-tests.sh --fast

# 3. VERIFY all tests pass - look for these exact messages:
#    "✅ Unit Tests PASSED"
#    "✅ Integration Tests PASSED" 
#    "✅ E2E Tests PASSED"

# 4. If ANY test fails - STOP and fix them first
# 5. Re-run tests until 100% pass rate achieved
./run-all-tests.sh --fast

# 6. ONLY AFTER all tests pass - commit your changes
git add .
git commit -m "Your commit message"
```

## 🚫 What NOT to Do

**These actions are STRICTLY PROHIBITED:**

```bash
# ❌ NEVER do this - committing without testing
git add .
git commit -m "Quick fix"  # FORBIDDEN!

# ❌ NEVER do this - committing with known failures  
./run-all-tests.sh --fast  # Shows 1 FAILED test
git commit -m "Will fix later"    # ABSOLUTELY FORBIDDEN!

# ❌ NEVER do this - partial testing
pytest tests/unit/  # Only unit tests
git commit -m "Unit tests pass"   # FORBIDDEN - must run ALL tests!
```

**Docker tests are optional during development** but required for deployment validation. Use `--fast` to focus on essential Python test suite during active development, or `--skip-docker` for comprehensive testing without Docker overhead. ALL enabled Python tests must still pass.

### Building and Packaging

**🚀 Modern Python Packaging (Recommended):**
```bash
# Build distribution packages using modern Python standards
python -m build              # Creates wheel and source distribution
# or with uv (faster)
uv build                     # Uses pyproject.toml configuration

# Install from built wheel
pip install dist/*.whl

# Verify package contents
unzip -l dist/*.whl
```

**📦 Development Installation:**
```bash
# Editable installation (recommended for development)
uv pip install -e .          # Links to source code
uv pip install -e ".[dev]"   # Include development dependencies
```

### Production Docker Build and Publishing

**🐳 Docker Hub Publishing:**
```bash
# Build and publish to Docker Hub
./scripts/build-production.sh

# The script builds for multiple architectures and pushes to makutaku/vortex
# Tags: latest (dev), v1.0.0 (production), v1.0.0-build.123 (specific builds)
```

**🚀 Production Deployment:**
```bash
# Use versioned tags for production stability
docker compose -f docker-compose.prod.yml up -d

# Development environments use latest
docker compose -f docker-compose.dev.yml up -d

# Modern docker compose command (not deprecated docker-compose)
docker compose up -d
docker compose down
docker compose logs -f
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
vortex validate --path ./data --detailed  # Show detailed validation results
vortex validate --path ./data --format json  # Output as JSON format

# Monitoring and metrics (NEW)
vortex metrics status        # Check metrics system status
vortex metrics endpoint      # Show metrics URL
vortex metrics test          # Generate test metrics
vortex metrics summary       # Show metrics activity summary
vortex metrics dashboard     # Show dashboard URLs

# System resilience (NEW)
vortex resilience status     # Circuit breaker status
vortex resilience reset      # Reset all circuit breakers
vortex resilience recovery   # Error recovery statistics
vortex resilience health     # Overall system health
```


## Architecture

Vortex follows **Clean Architecture** principles with distinct separation of concerns across layers:

### Clean Architecture Layers

**Domain Layer** (`vortex/models/`):
- `Instrument`: Base class for tradeable instruments (Future, Stock, Forex)
- `PriceSeries`: Time series data representation with validation
- `Period`: Time intervals with frequency attributes
- Core business entities independent of external systems

**Application Layer** (`vortex/services/`):
- `UpdatingDownloader`: Main downloader with incremental update logic
- `BackfillDownloader`: Historical data range downloads
- `MockDownloader`: Testing with synthetic data
- Business use cases and orchestration logic

**Infrastructure Layer** (`vortex/infrastructure/`):
- **Providers** (`providers/`): External data source integrations with dependency injection
  - `BarchartDataProvider`: Premium web scraping with HTTP client abstraction
  - `YahooDataProvider`: Free Yahoo Finance API with cache and data fetcher injection
  - `IbkrDataProvider`: Interactive Brokers TWS/Gateway with connection manager injection
  - `interfaces.py`: Dependency injection protocols and default implementations
  - `factory.py`: Provider factory with dependency injection support
- **Storage** (`storage/`): Data persistence implementations
  - `CsvStorage`: Primary CSV format storage
  - `ParquetStorage`: Backup Parquet format storage
  - `RawDataStorage`: Compliance audit trail with gzipped raw data storage
- **Metrics** (`metrics/`): Production monitoring and observability
  - `VortexMetrics`: Prometheus metrics collection for all operations
  - Circuit breaker monitoring and provider performance tracking
- **Resilience** (`resilience/`): Failure handling and recovery
  - Circuit breaker patterns, retry logic, error recovery

**Interface Layer** (`vortex/cli/`):
- `main.py`: Modern CLI entry point with Click framework
- `commands/`: Download, config, providers, validate commands
- Professional user interface with rich terminal output

### Core Systems

**Configuration Management** (`vortex/core/config/`):
- `VortexConfig`: Pydantic-based configuration models with validation
- `ConfigManager`: Modern configuration management with TOML support
- Environment variable support with VORTEX_* naming convention
- Interactive configuration wizard for guided setup

**Correlation & Observability** (`vortex/core/correlation/`):
- `CorrelationIdManager`: Thread-local request tracking across operations
- `RequestTracker`: Performance metrics and operation tracing
- Decorators for automatic correlation ID injection and operation tracking

**Exception Management** (`vortex/exceptions/`):
- Comprehensive exception hierarchy with actionable error messages
- Context-aware error formatting with resolution suggestions
- Plugin-specific exceptions with proper error context

### Key Files

- `vortex/cli/commands/download.py`: Modern CLI download command with integrated downloader factory logic
- `vortex/cli/commands/metrics.py`: Monitoring and metrics management commands
- `vortex/cli/commands/resilience.py`: System resilience and circuit breaker commands
- `vortex/cli/main.py`: Modern CLI entry point using Click framework
- `vortex/core/config/`: Consolidated configuration management system
- `vortex/core/correlation/`: Unified correlation and request tracking system
- `vortex/infrastructure/providers/interfaces.py`: Dependency injection protocols and default implementations
- `vortex/infrastructure/providers/factory.py`: Provider factory with dependency injection support
- `vortex/infrastructure/storage/raw_storage.py`: Raw data audit trail storage
- `vortex/infrastructure/metrics/prometheus_metrics.py`: Comprehensive metrics collection
- `vortex/infrastructure/`: External integrations (providers, storage, resilience)
- `config/assets/`: Default instrument definitions directory
- `docker/docker-compose.monitoring.yml`: Complete monitoring stack deployment

### Configuration Management

The modern CLI supports multiple configuration methods with precedence: **Environment Variables > TOML Configuration > Application Defaults**

**TOML Configuration (Recommended):**
```bash
# Copy example and customize
cp config/config.toml.example config/config.toml
```

```toml
[general]
default_provider = "yahoo"    # yahoo (free), barchart (premium), ibkr (professional)
output_directory = "./data"
backup_enabled = true

[general.logging]
level = "INFO"
format = "console"
output = ["console"]

# Raw data storage configuration (NEW)
[general.raw]
enabled = true                    # Enable raw data storage
retention_days = 30              # Days to retain (1-365, None for unlimited)
compress = true                  # Gzip compression
include_metadata = true          # Include .meta.json files

# Monitoring and metrics configuration (NEW)
[general.metrics]
enabled = true                   # Enable Prometheus metrics
port = 8000                     # Metrics server port
path = "/metrics"                # Metrics endpoint path

[providers.barchart]
username = "your_username"
password = "your_password"
daily_limit = 150

[providers.ibkr]
host = "localhost"
port = 7497
client_id = 1

[date_range]
start_year = 2020
end_year = 2025
```

**Interactive Configuration:**
```bash
vortex config --provider barchart --set-credentials
vortex config --provider ibkr --set-credentials
```

**Environment Variables (Override TOML):**
```bash
# Core configuration
export VORTEX_DEFAULT_PROVIDER=yahoo
export VORTEX_BARCHART_USERNAME="your_username"
export VORTEX_LOGGING_LEVEL=DEBUG

# Raw data storage (NEW)
export VORTEX_RAW_ENABLED=true
export VORTEX_RAW_RETENTION_DAYS=30
export VORTEX_RAW_BASE_DIRECTORY=./raw
export VORTEX_RAW_COMPRESS=true
export VORTEX_RAW_INCLUDE_METADATA=true

# Monitoring and metrics (NEW)
export VORTEX_METRICS_ENABLED=true
export VORTEX_METRICS_PORT=8000
export VORTEX_METRICS_PATH="/metrics"
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

#### Assets File Format

**⚠️ IMPORTANT**: Assets files must use the correct Vortex format with nested objects (not arrays):

```json
{
  "stock": {
    "AAPL": {
      "code": "AAPL",
      "tick_date": "1980-12-12",
      "start_date": "1980-12-12",
      "periods": "1d"
    },
    "GOOGL": {
      "code": "GOOGL",
      "tick_date": "2004-08-19",
      "start_date": "2004-08-19",
      "periods": "1d"
    }
  },
  "future": {
    "GC": {
      "code": "GC=F",
      "tick_date": "2008-05-04",
      "start_date": "2008-05-04",
      "periods": "1d"
    }
  },
  "forex": {
    "EURUSD": {
      "code": "EURUSD=X",
      "tick_date": "2000-01-01",
      "start_date": "2000-01-01",
      "periods": "1d"
    }
  }
}
```

**Key Format Requirements:**
- Use **objects** `{}` not **arrays** `[]`
- Use **singular** asset class names: `"stock"`, `"future"`, `"forex"` (not plural)
- **Instrument name as key**: The instrument name becomes the JSON key
- **Required field**: Only `code` is mandatory; other fields are optional
- **Provider-specific fields**:
  - **Barchart**: `cycle` (futures contract cycle)
  - **IBKR**: `conId`, `localSymbol`, `multiplier`, `baseCurrency`, `quoteCurrency`

Each assets file defines futures, forex, and stock instruments with metadata like trading cycles, tick dates, and periods. Users can maintain a single assets file for all providers or create provider-specific files based on their needs.

### Data Flow

1. Configuration loaded from `assets/` directory and environment variables
2. Correlation ID generated for end-to-end request tracking
3. Appropriate downloader created based on data provider with dependency injection
4. Instrument definitions processed to generate download jobs
5. Data downloaded with metrics collection and circuit breaker protection
6. Raw provider responses stored in compressed audit trail (if enabled)
7. Data processed and stored in both CSV (primary) and Parquet (backup) formats
8. Existing data checked to avoid duplicate downloads
9. Metrics exported to Prometheus for monitoring and alerting

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

### Production Environment Deployment

**🏗️ Environment Structure:**
Vortex supports organized deployment environments with provider-specific configurations:

```
vortex-share/environments/
├── dev/       # Development environments (latest image)
├── test/      # Testing environments (latest image)  
└── prod/      # Production environments (versioned image)
    ├── yahoo/     # Yahoo Finance provider
    ├── barchart/  # Barchart.com provider
    └── ibkr/      # Interactive Brokers provider
```

**🚀 Environment Deployment:**
```bash
# Deploy development environment
cd ~/vortex-share/environments/dev/yahoo
docker compose up -d

# Deploy production environment (versioned image)
cd ~/vortex-share/environments/prod/yahoo
docker compose up -d

# Check logs
docker compose logs -f

# Deploy all providers in an environment
for provider in yahoo barchart ibkr; do
  cd ~/vortex-share/environments/prod/$provider
  docker compose up -d
done
```

**📁 Volume Mapping:**
Each environment maps essential directories:
- `./assets:/app/assets` - Provider-specific instrument definitions
- `./config:/app/config` - TOML configuration files
- `./data:/app/data` - Downloaded CSV and Parquet files
- `./logs:/app/logs` - Application logs with rotation

**⚙️ Environment Variables:**
- **Production**: Uses versioned Docker images (`makutaku/vortex:v1.0.0`)
- **Dev/Test**: Uses latest images (`makutaku/vortex:latest`) 
- **Logging**: Comprehensive file and console output with configurable levels
- **Scheduling**: Provider-specific cron schedules to avoid conflicts

### Recent Architectural Improvements

**Dependency Injection Implementation (2025-08-14)**:
- ✅ **Protocol-Based DI**: Created comprehensive dependency injection infrastructure with interfaces.py
- ✅ **Constructor Refactoring**: Eliminated tight coupling in Yahoo, IBKR, and Barchart provider constructors
- ✅ **Explicit Lifecycle Management**: Separated object construction from initialization (login/cache setup)
- ✅ **Factory Enhancement**: Updated provider factory to support dependency injection with explicit initialization

**Static Method Elimination (2025-08-14)**:
- ✅ **Business Logic Refactoring**: Converted static methods to instance methods for better testability
- ✅ **Configurable Parameters**: Enhanced methods to support instance-level configuration overrides
- ✅ **Provider Improvements**: Refactored Barchart Client (4 methods), IBKR Provider (2 methods), Barchart Parser (1 method)
- ✅ **Test Modernization**: Updated test suite to use instance methods and fixtures
- ✅ **DI Compliance**: Eliminated violations of dependency injection principles

**Key Improvements**:
- **Yahoo Provider**: Removed `set_yf_tz_cache()` constructor call, added cache and data fetcher injection
- **IBKR Provider**: Removed auto-login in constructor, added connection manager injection  
- **Barchart Provider**: Removed auto-login, added HTTP client abstraction
- **Provider Factory**: Enhanced to support dependency injection and explicit initialization
- **Barchart Client**: Converted 4 static request builders to configurable instance methods
- **IBKR Provider**: Converted 2 static period mappers to configurable instance methods
- **Barchart Parser**: Converted CSV parser from class method to configurable instance method

**Structural Refactoring (2025-08-05)**:
- ✅ **Clean Architecture Implementation**: Reorganized codebase into distinct layers (domain, application, infrastructure, interface)
- ✅ **Module Consolidation**: Eliminated duplicate implementations by creating unified `core/correlation/` and `core/config/` systems
- ✅ **Infrastructure Layer**: Moved providers, storage, and resilience components to proper infrastructure layer
- ✅ **Import Path Simplification**: Standardized import paths following architectural boundaries
- ✅ **Test Compatibility**: Maintained 100% unit test pass rate (109 passed, 2 skipped) after structural changes

**Benefits Achieved**:
- Eliminated tight coupling and missing dependency injection violations
- Improved testability and flexibility through instance method patterns
- Enhanced configurability with parameter injection support
- Reduced code duplication and improved maintainability
- Clear separation of concerns following Clean Architecture principles  
- Simplified dependency injection and plugin system
- Enhanced correlation tracking and observability
- Consolidated configuration management with better validation
- Better separation of construction and initialization concerns

### Testing Strategy

Tests use pytest with fixture-based setup organized into distinct categories:
- **Unit Tests** (`tests/unit/`): Isolated component testing with mocks (1038 tests)
- **Integration Tests** (`tests/integration/`): Multi-component interaction testing (24 tests)  
- **End-to-End Tests** (`tests/e2e/`): Complete workflow validation (8 tests)
  - Includes real Yahoo Finance download tests with actual market data
  - Tests complete CLI user workflows from command to file output
  - Validates JSON assets file processing with multiple symbols
  - Comprehensive time period testing (daily, hourly, weekly, monthly, intraday)
- Test markers for network-dependent and credential-dependent tests
- Comprehensive test coverage across all architectural layers

**E2E Test Categories:**
- **CLI Workflow Tests**: Help, providers, config, download commands
- **Real Data Download**: Single-symbol Yahoo Finance integration with network calls
- **Assets File Processing**: Multi-symbol batch downloads using JSON asset files
- **Time Period Validation**: All Yahoo Finance supported periods (1m, 5m, 15m, 30m, 1h, 1d, 1W, 1M)
- **Error Handling**: Invalid command and edge case scenarios

**Running E2E Tests:**
```bash
# Run all E2E tests (including network tests)
uv run pytest tests/e2e/ -v

# Skip network-dependent tests
uv run pytest tests/e2e/ -v -m "not network"

# Run only the real data download test
uv run pytest tests/e2e/ -v -m "network and e2e"
```

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
./tests/docker/test-docker-build.sh

# 2. Note which tests pass
# 3. After refactoring, run again and compare
```

**AFTER refactoring (MANDATORY):**
```bash
# 1. Quick validation script (recommended)
./tests/docker/test-docker-build.sh 5 12 --quiet

# 2. Manual validation (if needed)
docker run --rm vortex-test:latest vortex providers | grep "Total providers available"
docker run --rm vortex-test:latest vortex --help | grep "Commands:"

# 3. If either fails, fix IMMEDIATELY before committing
# 4. Run full test suite to confirm
./tests/docker/test-docker-build.sh
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
1. **Baseline:** `./tests/docker/test-docker-build.sh` (establish what works)
2. **Refactor:** Make your changes
3. **Quick Check:** `./tests/docker/test-docker-build.sh 5 12 --quiet` (catch obvious breaks)
4. **Fix Immediately:** Don't proceed until Tests 5 & 12 pass
5. **Full Validation:** `./tests/docker/test-docker-build.sh` (ensure nothing else broke)
6. **Commit:** Only after all tests pass

**This pattern prevents the cascade failures where one broken test leads to debugging rabbit holes.**