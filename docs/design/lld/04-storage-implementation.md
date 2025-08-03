# Storage Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Storage Architecture](../hld/05-storage-architecture.md)

## 1. Storage Interface Implementation

### 1.1 Core Storage Contract

**Abstract Interface:**
```python
class DataStorage(ABC):
    """Abstract base class for data storage implementations"""
    
    @abstractmethod
    def save(self, data: pd.DataFrame, filepath: str) -> SaveResult:
        """Save DataFrame to storage"""
    
    @abstractmethod
    def load(self, filepath: str) -> pd.DataFrame:
        """Load DataFrame from storage"""
```

**Key Design Decisions:**
- **Path abstraction**: All paths relative to base directory
- **Atomic operations**: Use temporary files for safe writes
- **Metadata tracking**: Automatic file statistics collection

**Source Reference:** `src/vortex/data_storage/data_storage.py`

### 1.2 Atomic Save Pattern

**Algorithm: Safe File Writing**
```
1. Generate temp_path = target_path + '.tmp'
2. Write data to temp_path
3. IF backup_enabled AND target exists:
     Copy target to backup_path
4. Atomically move temp_path → target_path
5. Update metadata store
6. ON ERROR:
     - Remove temp_path if exists
     - Restore from backup if needed
```

**Benefits:**
- No partial writes on failure
- Automatic rollback capability
- Consistent state guarantee

**Source Reference:** `src/vortex/data_storage/file_storage.py`

## 2. Format-Specific Implementations

### 2.1 CSV Storage

**Key Implementation Points:**
```python
# Saving with pandas
df.to_csv(
    path,
    index=False,
    encoding='utf-8',
    float_format='%.6f',
    date_format='%Y-%m-%d %H:%M:%S'
)
```

**CSV-Specific Features:**
- UTF-8 encoding for international symbols
- Configurable decimal precision
- ISO 8601 date formatting
- Header preservation

**Source Reference:** `src/vortex/data_storage/csv_storage.py`

### 2.2 Parquet Storage

**Key Implementation Points:**
```python
# Parquet with compression
df.to_parquet(
    path,
    engine='pyarrow',
    compression='snappy',
    index=False
)
```

**Parquet-Specific Features:**
- Columnar storage for analytics
- Snappy compression by default
- Schema evolution support
- Type preservation

**Performance Characteristics:**
| Operation | CSV | Parquet |
|-----------|-----|---------|
| Write Speed | Fast | Moderate |
| Read Speed | Slow | Fast |
| File Size | Large | Small |
| Query Performance | Poor | Excellent |

**Source Reference:** `src/vortex/data_storage/parquet_storage.py`

## 3. Deduplication Engine

### 3.1 Deduplication Algorithm

**Pseudo-code:**
```
FUNCTION deduplicate_data(data, provider_priority):
    # 1. Create composite key
    key_columns = ['timestamp', 'symbol']
    
    # 2. Sort by priority
    IF 'provider' IN data.columns:
        data['_priority'] = map_provider_priority(data['provider'])
        SORT data BY ['_priority'] + key_columns
    
    # 3. Remove duplicates
    deduplicated = drop_duplicates(data, subset=key_columns, keep='first')
    
    # 4. Clean and return
    RETURN sort(deduplicated, by=key_columns)
```

**Conflict Resolution:**
- Provider priority determines winner
- First occurrence kept (highest priority)
- Timestamp + symbol as unique key

**Source Reference:** `src/vortex/data_storage/deduplicator.py`

### 3.2 Merge Strategy

**Algorithm: Incremental Data Merge**
```
1. Load existing data from storage
2. Append new data to existing
3. Apply deduplication rules
4. Sort by timestamp
5. Save merged result
```

**Optimization:**
- Only load overlapping date ranges
- Streaming merge for large datasets
- In-place deduplication when possible

## 4. Metadata Management

### 4.1 Metadata Structure

**Metadata Schema:**
```json
{
  "files": {
    "path/to/file.csv": {
      "row_count": 1000,
      "file_size_bytes": 52400,
      "last_updated": "2024-01-08T10:30:00Z",
      "checksum": "sha256:abc123..."
    }
  },
  "statistics": {
    "total_files": 42,
    "total_size_bytes": 10485760,
    "last_cleanup": "2024-01-07T00:00:00Z"
  }
}
```

**Update Pattern:**
```python
# Atomic metadata update
def update_file_metadata(self, filepath, stats):
    with self.lock:
        self.metadata["files"][filepath] = stats
        self._recalculate_statistics()
        self._save_metadata()
```

**Source Reference:** `src/vortex/data_storage/metadata_store.py`

## 5. Storage Factory

### 5.1 Factory Pattern Implementation

**Storage Creation:**
```python
def create_storage(storage_type: str, **kwargs) -> DataStorage:
    storage_map = {
        'csv': CsvStorage,
        'parquet': ParquetStorage
    }
    
    storage_class = storage_map.get(storage_type)
    if not storage_class:
        raise ValueError(f"Unknown storage type: {storage_type}")
    
    return storage_class(**kwargs)
```

**Dual Storage Pattern:**
```
Primary (CSV): Human-readable, debugging
Backup (Parquet): Performance, archival
```

**Source Reference:** `src/vortex/data_storage/factory.py`

## 6. Error Handling

### 6.1 Storage-Specific Exceptions

**Exception Hierarchy:**
```
StorageError
├── FileNotFoundError
├── PermissionError
├── DiskFullError
└── CorruptedDataError
```

**Error Recovery Matrix:**
| Error | Recovery Action | User Action |
|-------|----------------|-------------|
| File Not Found | Return empty DataFrame | Check path |
| Permission Denied | Retry with elevated permissions | Fix permissions |
| Disk Full | Clean temp files, retry | Free disk space |
| Corrupted Data | Load from backup | Investigate corruption |

**Source Reference:** `src/vortex/data_storage/exceptions.py`

## 7. Performance Optimizations

### 7.1 Optimization Techniques

**Memory Management:**
```python
# Chunked reading for large files
def read_large_csv(filepath, chunksize=10000):
    chunks = []
    for chunk in pd.read_csv(filepath, chunksize=chunksize):
        processed = process_chunk(chunk)
        chunks.append(processed)
    return pd.concat(chunks, ignore_index=True)
```

**I/O Optimizations:**
- Buffered writes for small files
- Memory-mapped files for large datasets
- Parallel reads for partitioned data

**Source Reference:** `src/vortex/data_storage/optimizations.py`

## 8. Testing Approach

### 8.1 Storage Testing Pattern

**Test Structure:**
```python
class TestStorageOperations:
    def test_save_load_cycle(self):
        # 1. Create test data
        # 2. Save to storage
        # 3. Load from storage
        # 4. Verify data integrity
    
    def test_atomic_operations(self):
        # 1. Simulate failure during save
        # 2. Verify rollback
        # 3. Check file consistency
```

**Test Scenarios:**
- Round-trip data integrity
- Concurrent access handling
- Large file performance
- Error recovery validation

**Source Reference:** `tests/test_storage/`

## 9. Configuration Examples

### 9.1 Storage Configuration

**CSV Storage:**
```json
{
  "storage_type": "csv",
  "base_directory": "/data/market_data",
  "encoding": "utf-8",
  "delimiter": ",",
  "float_precision": 6
}
```

**Parquet Storage:**
```json
{
  "storage_type": "parquet",
  "base_directory": "/data/market_data",
  "compression": "snappy",
  "engine": "pyarrow"
}
```

**Environment Configuration:**
```bash
VORTEX_DEFAULT_PROVIDER=csv
VORTEX_OUTPUT_DIR=/data/market_data
VORTEX_BACKUP_ENABLED=true
```

## Related Documents

- **[Storage Architecture](../hld/05-storage-architecture.md)** - High-level storage design
- **[Component Implementation](01-component-implementation.md)** - Component integration
- **[Data Processing Implementation](02-data-processing-implementation.md)** - Data flow integration

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** Senior Developer, Storage Engineer