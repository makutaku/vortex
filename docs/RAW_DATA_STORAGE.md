# Raw Data Storage & Compliance Guide

This guide covers Vortex's raw data storage system for compliance, auditing, and debugging purposes.

## 🎯 Overview

Vortex automatically maintains audit trails of all provider responses by storing untampered raw data exactly as received. This system provides:

- **Regulatory Compliance**: Meet audit trail requirements for financial data
- **Debugging Support**: Trace issues back to original provider responses
- **Data Lineage**: Complete chain of custody for all downloaded data
- **Quality Assurance**: Verify data processing accuracy against raw responses

## 🏗️ Architecture

### Storage Structure

```
./raw/
├── 2025/
│   ├── 08/
│   │   ├── stocks/
│   │   │   ├── AAPL_20250818_143022_abc123.csv.gz
│   │   │   ├── AAPL_20250818_143022_abc123.meta.json
│   │   │   ├── GOOGL_20250818_143045_def456.csv.gz
│   │   │   └── GOOGL_20250818_143045_def456.meta.json
│   │   ├── futures/
│   │   │   ├── GC_20250818_144001_ghi789.csv.gz
│   │   │   └── GC_20250818_144001_ghi789.meta.json
│   │   └── forex/
│   │       ├── EURUSD_20250818_144030_jkl012.csv.gz
│   │       └── EURUSD_20250818_144030_jkl012.meta.json
└── retention_info.json
```

### File Naming Convention

```
{symbol}_{YYYYMMDD}_{HHMMSS}_{correlation_id}.csv.gz
{symbol}_{YYYYMMDD}_{HHMMSS}_{correlation_id}.meta.json
```

**Components:**
- `symbol`: Trading symbol (AAPL, GC, EURUSD)
- `YYYYMMDD`: Date of request (20250818)
- `HHMMSS`: Time of request (143022)
- `correlation_id`: Unique request identifier (abc123)

## ⚙️ Configuration

### TOML Configuration

```toml
[general.raw]
enabled = true                    # Enable raw data storage
retention_days = 30              # Days to retain (1-365, None for unlimited)
compress = true                  # Gzip compression
include_metadata = true          # Include .meta.json files
base_directory = "./raw"         # Base storage directory
```

### Environment Variables

```bash
# Core settings
export VORTEX_RAW_ENABLED=true
export VORTEX_RAW_RETENTION_DAYS=30
export VORTEX_RAW_BASE_DIRECTORY=./raw

# Storage options
export VORTEX_RAW_COMPRESS=true
export VORTEX_RAW_INCLUDE_METADATA=true

# Advanced settings
export VORTEX_RAW_MAX_FILE_SIZE=10485760  # 10MB limit
export VORTEX_RAW_CLEANUP_INTERVAL=86400  # 24 hours
```

### Configuration Validation

```python
# Retention days validation
retention_days: Optional[int] = Field(
    None,
    ge=1,
    le=365,
    description="Days to retain raw files (1-365, None for unlimited)"
)
```

## 📁 Raw Data Files

### CSV Data Files

**Content:** Exact provider response data
**Format:** Compressed CSV with gzip
**Encoding:** UTF-8
**Size:** Typically 1-50KB compressed

**Example:**
```csv
Date,Open,High,Low,Close,Volume
2025-08-18,150.25,151.50,149.80,151.20,25678900
2025-08-17,149.50,150.75,149.25,150.25,22445600
```

### Metadata Files

**Content:** Request context and processing information
**Format:** JSON with structured metadata
**Purpose:** Audit trail and debugging support

**Structure:**
```json
{
  "correlation_id": "abc123",
  "timestamp": "2025-08-18T14:30:22.123456Z",
  "vortex_version": "0.1.4",
  "provider": "yahoo",
  "request": {
    "symbol": "AAPL",
    "start_date": "2025-08-01",
    "end_date": "2025-08-18",
    "period": "1d",
    "params": {
      "interval": "1d",
      "includePrePost": false
    }
  },
  "response": {
    "status_code": 200,
    "content_type": "text/csv",
    "content_length": 1247,
    "headers": {
      "content-encoding": "gzip",
      "cache-control": "max-age=3600"
    }
  },
  "data_quality": {
    "row_count": 12,
    "column_count": 6,
    "has_header": true,
    "date_range": {
      "start": "2025-08-01",
      "end": "2025-08-18"
    }
  },
  "storage": {
    "compression": "gzip",
    "original_size": 2847,
    "compressed_size": 1247,
    "compression_ratio": 0.44
  }
}
```

## 🔄 Data Lifecycle

### 1. Data Capture

```python
# Automatic capture during downloads
async def fetch_data(self, symbol: str, start_date: date, end_date: date):
    # Generate correlation ID
    correlation_id = self.correlation_manager.get_id()
    
    # Make provider request
    response = await self.http_client.get(url, params=params)
    
    # Store raw response automatically
    if self.raw_storage.enabled:
        await self.raw_storage.store_raw_data(
            symbol=symbol,
            data=response.text,
            metadata={
                "correlation_id": correlation_id,
                "provider": self.provider_name,
                "request": request_info,
                "response": response_info
            }
        )
```

### 2. Storage Operations

**Thread-Safe Storage:**
```python
async def store_raw_data(self, symbol: str, data: str, metadata: Dict[str, Any]):
    """Store raw provider data with metadata."""
    timestamp = datetime.utcnow()
    correlation_id = metadata.get("correlation_id", "unknown")
    
    # Generate file paths
    csv_path = self._generate_file_path(symbol, timestamp, correlation_id, "csv.gz")
    meta_path = self._generate_file_path(symbol, timestamp, correlation_id, "meta.json")
    
    # Store compressed CSV
    await self._write_compressed_csv(csv_path, data)
    
    # Store metadata
    if self.include_metadata:
        await self._write_metadata(meta_path, metadata)
```

### 3. Retention Management

**Automatic Cleanup:**
```python
async def cleanup_expired_files(self):
    """Remove files older than retention period."""
    if not self.retention_days:
        return  # Unlimited retention
    
    cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)
    
    for file_path in self._find_expired_files(cutoff_date):
        try:
            file_path.unlink()  # Remove file
            logger.info(f"Removed expired raw data file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to remove expired file {file_path}: {e}")
```

## 🛡️ Compliance Features

### Regulatory Requirements

**Financial Industry Standards:**
- **MiFID II**: Transaction reporting and best execution
- **GDPR**: Data lineage and right to explanation
- **SOX**: Internal controls and audit trails
- **CFTC**: Swap data repository requirements

**Audit Trail Components:**
- Original provider responses (untampered)
- Request parameters and timestamps
- Processing metadata and correlation IDs
- Data quality validation results
- System version and configuration info

### Data Integrity

**Hash Verification:**
```python
import hashlib

def verify_data_integrity(csv_path: Path, meta_path: Path) -> bool:
    """Verify raw data file integrity."""
    # Read metadata
    with open(meta_path) as f:
        metadata = json.load(f)
    
    # Calculate current hash
    with open(csv_path, 'rb') as f:
        current_hash = hashlib.sha256(f.read()).hexdigest()
    
    # Compare with stored hash
    stored_hash = metadata.get('data_quality', {}).get('file_hash')
    return current_hash == stored_hash
```

**Immutability Guarantees:**
- Files written once, never modified
- Correlation IDs ensure unique identification
- Metadata includes original request context
- Compression maintains data integrity

### Chain of Custody

**Request Tracking:**
```
1. User Request → CLI Command
2. CLI Command → Download Job
3. Download Job → Provider Request
4. Provider Response → Raw Storage
5. Raw Data → Processing Pipeline
6. Processed Data → CSV/Parquet Storage
```

**Correlation Example:**
```
Correlation ID: abc123-def456-ghi789

Files:
- raw/2025/08/stocks/AAPL_20250818_143022_abc123.csv.gz
- raw/2025/08/stocks/AAPL_20250818_143022_abc123.meta.json
- data/stocks/1d/AAPL.csv
- data/stocks/1d/AAPL.csv.json

Logs:
[2025-08-18T14:30:22Z] INFO [abc123] Starting download for AAPL
[2025-08-18T14:30:23Z] INFO [abc123] Fetching from Yahoo Finance
[2025-08-18T14:30:24Z] INFO [abc123] Stored raw data: 1247 bytes
[2025-08-18T14:30:25Z] INFO [abc123] Processed 12 rows
[2025-08-18T14:30:26Z] INFO [abc123] Download completed successfully
```

## 📊 Monitoring & Analytics

### Storage Metrics

**Prometheus Metrics:**
```
# Raw storage operations
vortex_raw_storage_files_total{provider="yahoo",symbol="AAPL"} 1

# Storage size tracking
vortex_raw_storage_size_bytes{provider="yahoo"} 15728640

# Compression efficiency
vortex_raw_storage_compression_ratio{provider="yahoo"} 0.44

# Retention compliance
vortex_raw_storage_expired_files_total 23
```

### CLI Analytics

```bash
# Check raw storage status
vortex raw status

# Show storage statistics
vortex raw stats

# Verify data integrity
vortex raw verify --symbol AAPL --date 2025-08-18

# List stored files
vortex raw list --provider yahoo --limit 10

# Cleanup expired files manually
vortex raw cleanup --dry-run
```

## 🔍 Debugging & Analysis

### Trace Request Issues

**Find Raw Data by Correlation ID:**
```bash
# Search for specific request
find ./raw -name "*abc123*" -type f

# Expected output:
# ./raw/2025/08/stocks/AAPL_20250818_143022_abc123.csv.gz
# ./raw/2025/08/stocks/AAPL_20250818_143022_abc123.meta.json
```

**Analyze Provider Response:**
```bash
# Decompress and examine raw data
gunzip -c ./raw/2025/08/stocks/AAPL_20250818_143022_abc123.csv.gz | head -10

# Check metadata
cat ./raw/2025/08/stocks/AAPL_20250818_143022_abc123.meta.json | jq .
```

### Compare Processed vs Raw Data

```python
import pandas as pd
import gzip
import json

def compare_processed_vs_raw(symbol: str, date: str):
    """Compare processed CSV with raw provider data."""
    
    # Load processed data
    processed_df = pd.read_csv(f"data/stocks/1d/{symbol}.csv")
    
    # Find and load raw data
    raw_files = find_raw_files(symbol, date)
    raw_df = pd.read_csv(gzip.open(raw_files[0], 'rt'))
    
    # Compare row counts
    print(f"Processed rows: {len(processed_df)}")
    print(f"Raw rows: {len(raw_df)}")
    
    # Compare specific values
    diff = processed_df.compare(raw_df)
    if not diff.empty:
        print("Differences found:")
        print(diff)
    else:
        print("Data matches perfectly")
```

## 🚨 Troubleshooting

### Common Issues

**Storage Not Working:**
```bash
# Check configuration
vortex config show | grep raw

# Verify directory permissions
ls -la ./raw/

# Check logs for errors
tail -f logs/vortex.log | grep raw
```

**Large Storage Usage:**
```bash
# Check storage size
du -h ./raw/

# Analyze file sizes by provider
find ./raw -name "*.csv.gz" -exec ls -lh {} \; | \
  awk '{provider=$9; gsub(/.*\//, "", provider); gsub(/_.*/, "", provider); size+=$5} END {print provider, size}'

# Check compression ratios
grep compression_ratio ./raw/*/*/*.meta.json | \
  jq -r '.storage.compression_ratio' | \
  awk '{sum+=$1; count++} END {print "Average compression:", sum/count}'
```

**Performance Impact:**
- Raw storage adds ~10-20ms per request
- Disk I/O is asynchronous, minimal blocking
- Compression reduces storage by 40-60%
- Memory usage increase: ~2-5MB per provider

### Best Practices

**Production Configuration:**
```toml
[general.raw]
enabled = true
retention_days = 90              # 3 months for compliance
compress = true                  # Essential for storage efficiency
include_metadata = true          # Required for audit trails
base_directory = "/var/lib/vortex/raw"  # Dedicated partition
```

**Monitoring Setup:**
- Set up alerts for storage usage >80%
- Monitor retention compliance
- Track compression ratios for efficiency
- Alert on storage operation failures

**Security Considerations:**
- Ensure raw directory has proper permissions (750)
- Regular backup of compliance data
- Encrypt storage at rest for sensitive data
- Implement access logging for audit access

This raw data storage system ensures Vortex meets enterprise compliance requirements while providing powerful debugging and analysis capabilities.