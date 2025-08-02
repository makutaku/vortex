# BC-Utils Data Requirements

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Product Requirements](product-requirements.md) | [Feature Specifications](feature-specifications.md)

## 1. Data Sources

### 1.1 Primary Sources
| Provider | Data Types | Coverage | Update Frequency | Cost Model |
|----------|------------|----------|------------------|------------|
| **Barchart.com** | Futures, Options, Stocks | Global | Real-time + EOD | Subscription ($) |
| **Yahoo Finance** | Stocks, ETFs, Forex | Global | 15-min delay + EOD | Free |
| **Interactive Brokers** | Multi-asset | Global | Real-time | Trading account |

### 1.2 Data Provider Requirements
- **DR-001:** Each provider must implement standardized interface
- **DR-002:** Provider failures must not crash entire system
- **DR-003:** Multiple providers can supply same instrument type
- **DR-004:** Provider-specific metadata must be preserved
- **DR-005:** Authentication credentials stored securely per provider

## 2. Instrument Coverage

### 2.1 Futures Contracts
**Supported Exchanges:** CME, CBOT, NYMEX, COMEX, ICE, Eurex
```json
{
  "GOLD": {
    "code": "GC",
    "exchange": "COMEX", 
    "cycle": "GJMQVZ",
    "tick_date": "2008-05-04",
    "contract_size": 100,
    "currency": "USD"
  }
}
```

**Requirements:**
- **DR-006:** Support 500+ major futures contracts
- **DR-007:** Handle contract rollover logic automatically
- **DR-008:** Track contract specifications (size, currency, etc.)
- **DR-009:** Support both front-month and specific contract months

### 2.2 Stock Data
**Coverage:** Major global exchanges (NYSE, NASDAQ, LSE, TSE, etc.)
```json
{
  "AAPL": {
    "symbol": "AAPL",
    "exchange": "NASDAQ",
    "currency": "USD",
    "sector": "Technology"
  }
}
```

**Requirements:**
- **DR-010:** Support 1000+ major stock symbols
- **DR-011:** Handle stock splits and dividend adjustments
- **DR-012:** Track corporate actions and symbol changes
- **DR-013:** Support ADRs and international listings

### 2.3 Forex Data  
**Coverage:** Major and minor currency pairs
```json
{
  "EURUSD": {
    "base": "EUR",
    "quote": "USD", 
    "pip_value": 0.0001,
    "market_hours": "24/5"
  }
}
```

**Requirements:**
- **DR-014:** Support 50+ major currency pairs
- **DR-015:** Handle weekend gaps in forex data
- **DR-016:** Track central bank intervention periods
- **DR-017:** Support both spot and forward rates

## 3. Data Formats and Schema

### 3.1 Standard OHLCV Schema
```python
{
  "timestamp": "2024-01-15T14:30:00Z",  # ISO 8601 UTC
  "open": 1850.25,                      # float64
  "high": 1852.75,                      # float64  
  "low": 1849.50,                       # float64
  "close": 1851.00,                     # float64
  "volume": 12500,                      # int64
  "symbol": "GC_202406",               # string
  "provider": "barchart"               # string
}
```

**Schema Requirements:**
- **DR-018:** Consistent column names across all providers
- **DR-019:** Standardized data types (float64 for prices, int64 for volume)
- **DR-020:** UTC timestamps in ISO 8601 format
- **DR-021:** Provider attribution for audit trail
- **DR-022:** Optional metadata fields for provider-specific data

### 3.2 File Formats

#### Primary Format: CSV
```csv
timestamp,open,high,low,close,volume,symbol,provider
2024-01-15T14:30:00Z,1850.25,1852.75,1849.50,1851.00,12500,GC_202406,barchart
```

**CSV Requirements:**
- **DR-023:** UTF-8 encoding with BOM for Excel compatibility
- **DR-024:** RFC 4180 compliant CSV format
- **DR-025:** Header row with standard column names
- **DR-026:** Consistent decimal precision (2 places for most instruments)

#### Secondary Format: Parquet
**Parquet Requirements:**
- **DR-027:** Columnar storage for analytical workloads
- **DR-028:** Snappy compression for size optimization
- **DR-029:** Schema evolution support for format changes
- **DR-030:** Partition by symbol and date for query performance

### 3.3 Naming Conventions
```
# File naming pattern
{symbol}_{frequency}_{date_range}.{extension}

# Examples
GOLD_1D_20240101_20240131.csv
AAPL_1H_20240315_20240315.parquet
EURUSD_5M_20240201_20240229.csv
```

**Naming Requirements:**
- **DR-031:** Consistent file naming across all instruments
- **DR-032:** Sortable alphanumeric format
- **DR-033:** Include frequency and date range in filename
- **DR-034:** Special characters escaped or replaced

## 4. Data Quality Standards

### 4.1 Validation Rules

#### Price Data Validation
- **DR-035:** Open, High, Low, Close must be positive numbers
- **DR-036:** High >= max(Open, Close) and Low <= min(Open, Close)
- **DR-037:** Price changes > 20% flagged for review
- **DR-038:** Volume must be non-negative integer

#### Temporal Validation  
- **DR-039:** Timestamps must be monotonically increasing
- **DR-040:** No duplicate timestamps per symbol
- **DR-041:** Trading hours validation per instrument
- **DR-042:** Weekend/holiday data flagged appropriately

#### Completeness Validation
- **DR-043:** Missing data periods identified and logged
- **DR-044:** Data gaps > 10% of expected points flagged
- **DR-045:** Minimum data threshold before file creation
- **DR-046:** Data age validation (no stale data acceptance)

### 4.2 Data Quality Metrics
```python
{
  "symbol": "GC_202406",
  "date_range": "2024-01-01 to 2024-01-31", 
  "total_points": 8760,
  "missing_points": 12,
  "completeness": 0.9986,
  "outliers_detected": 3,
  "quality_score": 0.995
}
```

**Quality Requirements:**
- **DR-047:** Quality score calculation for each dataset
- **DR-048:** Quality reports generated automatically
- **DR-049:** Quality thresholds configurable per instrument
- **DR-050:** Poor quality data quarantined, not deleted

## 5. Performance Requirements

### 5.1 Data Volume Specifications
- **DR-051:** Support datasets up to 10GB per instrument
- **DR-052:** Handle 1M+ data points per download session
- **DR-053:** Concurrent downloads limited by provider rate limits
- **DR-054:** Memory usage < 1GB for typical operations

### 5.2 Processing Speed
- **DR-055:** Data validation < 10 seconds per 100K points
- **DR-056:** File writing < 5 seconds per 1M points
- **DR-057:** Duplicate detection < 30 seconds per dataset
- **DR-058:** Metadata updates < 1 second per operation

## 6. Storage Requirements

### 6.1 Local Storage
- **DR-059:** Configurable storage directory structure
- **DR-060:** Automatic cleanup of old temporary files
- **DR-061:** Storage space monitoring and alerting
- **DR-062:** Atomic file operations to prevent corruption

### 6.2 Backup and Retention
- **DR-063:** Optional automatic backup to secondary format
- **DR-064:** Configurable data retention policies
- **DR-065:** Backup verification and integrity checking
- **DR-066:** Support for cloud storage backends (S3, GCS, Azure)

## 7. Security and Compliance

### 7.1 Data Protection
- **DR-067:** No sensitive data in log files
- **DR-068:** Data access audit logging
- **DR-069:** Encryption for data at rest (optional)
- **DR-070:** Secure transmission of credentials

### 7.2 Regulatory Compliance
- **DR-071:** Support for data retention regulations
- **DR-072:** Data lineage tracking for compliance audits
- **DR-073:** Support for GDPR data deletion requests
- **DR-074:** Market data redistribution license compliance

## 8. Integration Requirements

### 8.1 Data Export
- **DR-075:** Export to popular analysis frameworks (pandas, R)
- **DR-076:** API for programmatic data access
- **DR-077:** Bulk export utilities for migration
- **DR-078:** Real-time data streaming (future requirement)

### 8.2 Metadata Management
- **DR-079:** Instrument metadata database
- **DR-080:** Download history tracking
- **DR-081:** Data lineage and provenance tracking
- **DR-082:** Configuration change auditing

## 9. Error Handling

### 9.1 Data Provider Errors
- **DR-083:** Graceful handling of provider downtime
- **DR-084:** Retry logic for transient failures
- **DR-085:** Fallback to alternative providers when available
- **DR-086:** Error classification and appropriate responses

### 9.2 Data Quality Errors
- **DR-087:** Configurable actions for quality failures
- **DR-088:** Data quarantine for manual review
- **DR-089:** Automatic correction for known issues
- **DR-090:** Alert notifications for quality problems

## 10. Testing and Validation

### 10.1 Test Data Requirements
- **DR-091:** Synthetic test datasets for development
- **DR-092:** Known-good reference datasets for validation
- **DR-093:** Edge case datasets (holidays, gaps, outliers)
- **DR-094:** Performance test datasets at scale

### 10.2 Validation Framework
- **DR-095:** Automated data quality testing
- **DR-096:** Provider comparison and reconciliation
- **DR-097:** Historical data accuracy verification
- **DR-098:** End-to-end pipeline testing

---

**Data Requirements Summary:**
- **Total Requirements:** 98 detailed specifications
- **Critical Path:** Schema standardization, quality validation, provider integration
- **Success Metrics:** >99% data quality score, <1% failed downloads
- **Compliance:** Market data licensing, data protection regulations

**Next Review:** 2025-02-08 (monthly review cycle)