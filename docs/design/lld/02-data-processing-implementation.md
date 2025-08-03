# Data Processing Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Data Flow Design](../hld/03-data-flow-design.md)

## 1. Data Fetching Implementation

### 1.1 Data Fetching Algorithm

**Core Fetching Workflow:**
```
1. CHECK rate limits → IF limited, wait
2. BUILD request parameters from job
3. EXECUTE request with provider
4. VALIDATE response format
5. RECORD request for rate limiting
6. RETURN structured response
```

**Error Recovery Strategy:**
| Error Type | Recovery Action | Retry Logic |
|------------|-----------------|-------------|
| Rate Limit | Wait specified time | Immediate retry |
| Authentication | Re-authenticate once | Single retry |
| Connection | Exponential backoff | Max 3 retries |
| Unknown | Log and fail | No retry |

**Source Reference:** `src/vortex/data_processing/fetcher.py`

### 1.2 Rate Limiting Algorithm

**Multi-Window Rate Limiting:**
```
MAINTAIN sliding windows:
- daily_window (24 hours)
- hourly_window (60 minutes)
- minute_window (60 seconds)
- burst_window (10 seconds)

FOR each request:
1. CLEAN expired entries from all windows
2. CHECK if request count < limit for ALL windows
3. IF allowed: record timestamp, return TRUE
4. IF blocked: calculate wait time, return FALSE
```

**Wait Time Calculation (Priority Order):**
1. Minute limit (60 seconds)
2. Burst limit (10 seconds) 
3. Hourly limit (3600 seconds)
4. Daily limit (86400 seconds)

**Thread Safety:**
- Thread-safe with locking mechanism
- Automatic cleanup of expired requests
- Supports configurable limits per time window

**Source Reference:** `src/vortex/data_processing/rate_limiter.py`

## 2. Data Validation Implementation

### 2.1 Multi-Layer Validation Pipeline

**Validation Workflow:**
```
1. SCHEMA validation (required columns, data types)
2. BUSINESS RULES validation (OHLC relationships, volume)
3. STATISTICAL validation (volatility, outliers)
4. TEMPORAL validation (timestamps, ordering)
5. QUALITY SCORE calculation (0.0 to 1.0)
```

**Validation Categories:**

| Category | Validation Rules | Error/Warning |
|----------|------------------|---------------|
| **Schema** | Required columns present | Error |
| | Numeric data types | Error |
| | Datetime timestamps | Warning |
| **Business** | High ≥ max(Open, Close) | Error |
| | Low ≤ min(Open, Close) | Error |
| | Volume ≥ 0 | Error |
| | Price gaps < 5% | Warning |
| **Statistical** | Volatility bounds | Warning |
| | Outlier detection (IQR) | Warning |
| **Temporal** | No duplicate timestamps | Error |
| | Chronological ordering | Warning |

**Quality Score Algorithm:**
```
start_score = 1.0
score -= errors * 0.2
score -= warnings * 0.05
score *= data_completeness_factor
final_score = clamp(score, 0.0, 1.0)
```

**Source Reference:** `src/vortex/data_processing/validator.py`

## 3. Data Transformation Implementation

### 3.1 Provider-to-Standard Transformation

**Transformation Pipeline:**
```
1. APPLY provider-specific column mapping
2. STANDARDIZE timestamps to UTC
3. CONVERT data types (float64, int64, string)
4. APPLY unit conversions if needed
5. ADD metadata columns (symbol, provider)
6. SORT by timestamp
7. SELECT standard columns only
```

**Provider Column Mappings:**

| Provider | Source Column | Standard Column |
|----------|---------------|----------------|
| **Barchart** | Time, Open, High, Low, Last, Volume | timestamp, open, high, low, close, volume |
| **Yahoo** | Lowercase names (already standard) | No mapping needed |
| **IBKR** | date, open, high, low, close, volume | timestamp, open, high, low, close, volume |

**Timestamp Standardization:**
- **Barchart**: EST/EDT → UTC conversion
- **Yahoo**: Unix timestamps → UTC
- **IBKR**: Multiple formats → UTC
- **Generic**: Auto-detect and convert to UTC

**Data Type Conversions:**
```
Prices (OHLC) → float64
Volume → int64 (NaN filled with 0)
Symbol/Provider → string
Timestamp → datetime64[ns, UTC]
```

**Source Reference:** `src/vortex/data_processing/transformer.py`

## 4. Storage Operation Implementation

### 4.1 Intelligent Deduplication Algorithm

**Deduplication Process:**
```
1. COMBINE existing and new data
2. IDENTIFY duplicates based on strategy
3. GROUP duplicates by key columns
4. RESOLVE conflicts using preference rules
5. MERGE unique + resolved data
6. SORT by timestamp
7. GENERATE deduplication report
```

**Deduplication Strategies:**
- **timestamp_symbol**: Duplicates share same timestamp + symbol
- **timestamp_only**: Duplicates share same timestamp
- **all_columns**: Exact row matches

**Conflict Resolution Methods:**

| Method | Selection Criteria | Use Case |
|--------|-------------------|----------|
| **provider_preference** | IBKR > Barchart > Yahoo | Data quality hierarchy |
| **latest_timestamp** | Most recent processing | Freshness priority |
| **highest_volume** | Maximum volume value | Volume reliability |
| **default** | Last occurrence | Fallback option |

**Performance Monitoring:**
- Duplicate percentage tracking
- Warning threshold (10%)
- Conflict resolution statistics

**Source Reference:** `src/vortex/data_processing/deduplicator.py`

### 4.2 Atomic Storage Pattern

**Atomic Save Algorithm:**
```
1. VALIDATE input data (non-empty)
2. IF file exists: LOAD existing + DEDUPLICATE
3. SORT by timestamp
4. VALIDATE final data (meets threshold)
5. SAVE to temporary file
6. VERIFY saved data integrity
7. ATOMIC rename temp → final
8. UPDATE metadata tracking
9. ON ERROR: cleanup temporary file
```

**ACID Properties:**
- **Atomicity**: Temp file + atomic rename
- **Consistency**: Data validation before save
- **Isolation**: Unique temp file names
- **Durability**: Verification after write

**Error Recovery:**
- Automatic temp file cleanup
- Original file preservation
- Detailed error reporting
- Processing time tracking

**Metadata Tracking:**
- Row/column counts
- File size and checksum
- Date range coverage
- Processing duration

**Source Reference:** `src/vortex/data_processing/atomic_storage.py`

## 5. Performance Optimization Implementation

### 5.1 LRU Cache with TTL

**Cache Management Algorithm:**
```
ON cache_get(key):
1. CHECK if key exists and is fresh
2. IF fresh: update access time, return data
3. IF stale: remove from cache
4. RECORD hit/miss statistics

ON cache_put(key, data, ttl):
1. CALCULATE memory usage of new data
2. WHILE insufficient space: evict LRU item
3. STORE data with timestamp and TTL
4. UPDATE memory usage tracking
```

**Eviction Strategy:**
- **Size-based**: LRU eviction when memory limit exceeded
- **Time-based**: TTL expiration removes stale data
- **Memory estimation**: DataFrame memory usage calculation

**Cache Performance Metrics:**
- Hit/miss rates
- Memory utilization
- Cache size tracking
- Access pattern analysis

**Key Features:**
- Thread-safe operations
- Configurable TTL (default 1 hour)
- Memory-bounded (default 512MB)
- Performance statistics

**Source Reference:** `src/vortex/data_processing/cache.py`

## Related Documents

- **[Data Flow Design](../hld/03-data-flow-design.md)** - High-level data processing architecture
- **[Component Implementation](01-component-implementation.md)** - Component implementation details
- **[Provider Implementation](03-provider-implementation.md)** - Provider-specific details
- **[Storage Implementation](04-storage-implementation.md)** - Storage layer implementation

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** Senior Developer, Data Engineer