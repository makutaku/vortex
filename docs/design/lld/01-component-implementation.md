# Component Implementation Details

**Version:** 2.0  
**Date:** 2025-08-03  
**Related:** [Component Architecture](../hld/02-component-architecture.md)

## 1. CLI Implementation

### 1.1 Click Framework Architecture

**Command Structure:**
```python
@click.group()
@click.version_option()
@click.option('-c', '--config', type=click.Path(exists=True))
@click.option('-v', '--verbose', count=True)
@click.option('--dry-run', is_flag=True)
def cli():
    """BC-Utils: Financial data download automation tool."""
```

**Rich Terminal Integration:**
- Progress bars for download operations
- Colored output for status messages  
- Interactive tables for configuration display
- Confirmation prompts for destructive operations

**Source Reference:** `src/bcutils/cli/main.py`

### 1.2 Configuration Management

**TOML Configuration Pattern:**
```python
class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        with open(self.config_path, 'rb') as f:
            return tomllib.load(f)
```

**Interactive Setup:**
- Provider credential configuration with secure prompts
- Automatic TOML file generation
- Validation of configuration values

**Source Reference:** `src/bcutils/cli/utils/config_manager.py`

## 2. Download Orchestration Implementation

### 2.1 Core Workflow Pattern

**Algorithm: Incremental Download Workflow**
```
1. PARSE symbols and date ranges from CLI arguments
2. LOAD instrument configurations from assets JSON
3. CREATE DownloadJob objects for each instrument/period
4. SCHEDULE jobs with round-robin across instruments
5. FETCH raw data from provider (with retry logic)
6. MERGE with existing data (intelligent deduplication)
7. PERSIST to CSV storage with Parquet backup
8. UPDATE metadata with coverage information
```

**Error Recovery Strategy:**
- **Rate Limit**: Random sleep intervals (2-5 seconds)
- **Authentication**: Provider-specific re-authentication
- **Network Errors**: Exponential backoff with `@retry` decorator
- **Data Quality**: Validation with PriceSeries container

**Source Reference:** `src/bcutils/downloaders/updating_downloader.py`

### 2.2 Single Dispatch Pattern Implementation

**Provider Strategy with Type Dispatch:**
```python
from functools import singledispatchmethod

class DataProvider:
    @singledispatchmethod
    def _fetch_historical_data(self, instrument, period, start_date, end_date):
        raise NotImplementedError
    
    @_fetch_historical_data.register
    def _(self, instrument: Future, period, start_date, end_date):
        # Future-specific implementation
        return self._fetch_futures_data(...)
    
    @_fetch_historical_data.register  
    def _(self, instrument: Stock, period, start_date, end_date):
        # Stock-specific implementation
        return self._fetch_stock_data(...)
```

**Source Reference:** `src/bcutils/data_providers/data_provider.py`

## 3. Storage Architecture Implementation

### 3.1 Bridge Pattern for Dual Storage

**Storage Bridge Implementation:**
```python
class FileStorage(DataStorage):
    @singledispatchmethod
    def _get_file_path(self, instrument, period):
        raise NotImplementedError
    
    @_get_file_path.register
    def _(self, instrument: Future, period):
        return Path(f"futures/{period}/{instrument.symbol}.csv")
    
    @_get_file_path.register
    def _(self, instrument: Stock, period):
        return Path(f"stocks/{period}/{instrument.symbol}.csv")
```

**Dual Format Persistence:**
- Primary: CSV for human readability and compatibility
- Backup: Parquet for performance and compression
- Metadata: JSON sidecar files for tracking coverage

**Source Reference:** `src/bcutils/data_storage/file_storage.py`

### 1.2 Job Management Architecture

**Job State Machine:**
```
PENDING → IN_PROGRESS → COMPLETED
    ↓         ↓              ↓
  FAILED ←─ RETRY ←─────── FAILED
```

**Path Generation Pattern:**
```
{base_dir}/{instrument_type}/{symbol}_1D_{start}_{end}.csv

Examples:
- futures/GCM25_1D_20250101_20250201.csv
- stocks/AAPL_1D_20250101_20250201.csv
- forex/EUR_USD_1D_20250101_20250201.csv
```

**Key Features:**
- Unique job IDs for tracking
- State lifecycle management
- Automatic retry configuration
- Duration tracking

**Source Reference:** `src/bcutils/downloaders/download_job.py`

## 2. Instrument Model Implementation

### 2.1 Future Contract Architecture

**Contract Generation Algorithm:**
```
FOR each month in cycle (e.g., GJMQVZ):
  FOR each year in range:
    CREATE contract symbol (e.g., GCM25)
    CALCULATE expiry date by exchange rules
    CHECK if active during requested period
    ADD to active contracts list
SORT contracts by expiry date
```

**Exchange Expiry Rules:**
| Exchange | Instruments | Expiry Rule |
|----------|-------------|-------------|
| COMEX | Gold, Silver | 3rd-to-last business day |
| CBOT | Corn, Wheat | Business day before 15th |
| CME | S&P, Currencies | 3rd Friday of month |

**Contract Specifications:**
- **Symbol Format**: `{code}{month}{year}` (e.g., GCM25)
- **Active Period**: First notice day to expiry
- **Contract Size**: Varies by instrument (100 oz for Gold)
- **Tick Value**: Minimum price movement

**Source Reference:** `src/bcutils/instruments/future.py`

### 2.2 Stock Architecture

**Corporate Action Pattern:**
```
1. RECORD corporate action with metadata
2. ADJUST historical prices retroactively
3. MAINTAIN action audit trail
4. APPLY adjustments on data retrieval
```

**Split Adjustment Algorithm:**
```
FOR prices before split date:
  adjusted_price = original_price / split_ratio
  adjusted_volume = original_volume * split_ratio
```

**Key Features:**
- Multi-currency support
- Sector/industry classification
- Corporate action tracking
- Automatic price adjustments

**Source Reference:** `src/bcutils/instruments/stock.py`

## 3. Configuration Implementation

### 3.1 Configuration Architecture

**Configuration Sources (Priority Order):**
1. Environment variables
2. Configuration file
3. Default values

**Validation Rules:**
- **Provider-specific**: Barchart requires credentials, IBKR requires host/port
- **Date ranges**: start_year ≤ end_year ≤ current_year + 1
- **Directory access**: Write permissions validation
- **Numeric limits**: Positive values for limits and concurrency

**Key Configuration Groups:**
```
├── Provider Settings (type, credentials, limits)
├── Download Settings (directory, date range, chunking)
├── Operational Settings (dry_run, concurrency, logging)
└── Retry Settings (max_retries, delays)
```

**Source Reference:** `src/bcutils/initialization/session_config.py`

### 3.2 Component Factory Architecture

**Factory Pattern Implementation:**
```
1. PARSE configuration object
2. CREATE storage components (primary + backup)
3. CREATE data provider with credentials
4. CREATE validator with quality rules
5. CREATE metadata store
6. WIRE components together
7. RETURN configured downloader
```

**Component Dependencies:**
```
Downloader
├── Primary Storage (CSV)
├── Backup Storage (Parquet, optional)
├── Data Provider (Barchart/Yahoo/IBKR)
├── Data Validator (business + statistical rules)
└── Metadata Store (tracking)
```

**Provider-Specific Configurations:**
- **Barchart**: Session-based auth, 150/day limit
- **Yahoo**: No auth required, public API
- **IBKR**: TWS/Gateway connection, real-time data

**Source Reference:** `src/bcutils/initialization/component_factory.py`

## Related Documents

- **[Component Architecture](../hld/02-component-architecture.md)** - High-level component design
- **[Provider Implementation](03-provider-implementation.md)** - Data provider details
- **[Storage Implementation](04-storage-implementation.md)** - Storage layer details
- **[Testing Implementation](06-testing-implementation.md)** - Testing strategies

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** Senior Developer, Lead Engineer