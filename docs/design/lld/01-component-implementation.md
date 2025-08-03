# Component Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Component Architecture](../hld/02-component-architecture.md)

## 1. Download Manager Implementation

### 1.1 Core Workflow Pattern

**Algorithm: Incremental Download Workflow**
```
1. CREATE download job from configuration
2. CHECK for existing data → IF exists, incremental update
3. FETCH raw data from provider
4. VALIDATE data quality → IF invalid, reject
5. STORE data with deduplication
6. UPDATE metadata tracking
7. HANDLE errors with retry strategies
```

**Error Recovery Strategy:**
- **Rate Limit Error**: Wait specified period, retry
- **Authentication Error**: Re-authenticate once, retry
- **Connection Error**: Exponential backoff (max 3 retries)
- **Unknown Error**: Log and fail gracefully

**Source Reference:** `src/bcutils/downloaders/updating_downloader.py`

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