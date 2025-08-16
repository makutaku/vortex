# Storage Implementation Details

**Version:** 2.0  
**Date:** 2025-08-16  
**Related:** [Storage Architecture](../hld/05-storage-architecture.md)

## 1. Dual Storage Architecture Implementation

### 1.1 Storage Interface Protocol

Vortex implements a dual storage system with CSV primary storage and Parquet backup storage, following Clean Architecture principles with atomic operations and correlation tracking.

**Storage Protocol Interface (From `src/vortex/infrastructure/storage/data_storage.py`):**
```python
class DataStorageProtocol(Protocol):
    """Protocol for data storage implementations"""
    
    def persist(self, data: pd.DataFrame, instrument: 'Instrument', 
               correlation_id: Optional[str] = None) -> StorageResult:
        """Persist DataFrame with correlation tracking"""
        ...
    
    def load(self, instrument: 'Instrument', 
            correlation_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Load DataFrame with correlation tracking"""
        ...
    
    def exists(self, instrument: 'Instrument') -> bool:
        """Check if data exists for instrument"""
        ...
    
    def get_file_info(self, instrument: 'Instrument') -> Optional[FileInfo]:
        """Get file metadata information"""
        ...

class StorageResult:
    """Result object for storage operations"""
    
    def __init__(self, success: bool, file_path: Optional[str] = None, 
                 error: Optional[str] = None, row_count: int = 0):
        self.success = success
        self.file_path = file_path
        self.error = error
        self.row_count = row_count
        self.timestamp = datetime.now()
```

**Key Design Principles:**
- **Atomic operations**: Temporary file pattern with atomic rename
- **Dual format storage**: CSV (primary) + Parquet (backup) for redundancy
- **Correlation tracking**: Request tracing throughout storage operations
- **Path standardization**: Organized directory structure per instrument type

**Source Reference:** `src/vortex/infrastructure/storage/data_storage.py`

### 1.2 Atomic File Operations Implementation

**File Storage Base Class (From `src/vortex/infrastructure/storage/file_storage.py`):**
```python
class FileStorage:
    """Base storage implementation with atomic operations and correlation"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.correlation_manager = get_correlation_manager()
    
    def persist(self, data: pd.DataFrame, instrument: 'Instrument', 
               correlation_id: Optional[str] = None) -> StorageResult:
        """Persist data with atomic write operations"""
        correlation_id = correlation_id or self.correlation_manager.get_current_id()
        
        try:
            # Generate file paths
            target_path = self._get_file_path(instrument)
            temp_path = target_path.with_suffix(target_path.suffix + '.tmp')
            
            # Ensure directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Atomic write operation
            with self.correlation_manager.correlation_context(
                correlation_id=correlation_id,
                operation="storage_persist",
                file_path=str(target_path)
            ):
                # Write to temporary file
                self._write_dataframe(data, temp_path, instrument)
                
                # Create backup if target exists
                backup_created = self._create_backup_if_exists(target_path)
                
                # Atomic move to final location
                temp_path.rename(target_path)
                
                # Update metadata
                self._update_file_metadata(target_path, data, instrument)
                
                logger.info(f"Data persisted successfully",
                          extra={
                              'correlation_id': correlation_id,
                              'file_path': str(target_path),
                              'row_count': len(data),
                              'backup_created': backup_created
                          })
                
                return StorageResult(
                    success=True,
                    file_path=str(target_path),
                    row_count=len(data)
                )
                
        except Exception as e:
            # Cleanup temporary file on failure
            if temp_path.exists():
                temp_path.unlink()
            
            logger.error(f"Storage persist failed",
                        extra={'correlation_id': correlation_id, 'error': str(e)})
            
            return StorageResult(
                success=False,
                error=str(e)
            )
    
    def _create_backup_if_exists(self, target_path: Path) -> bool:
        """Create backup of existing file before overwrite"""
        if target_path.exists():
            backup_path = target_path.with_suffix(target_path.suffix + '.backup')
            shutil.copy2(target_path, backup_path)
            return True
        return False
    
    def _update_file_metadata(self, file_path: Path, data: pd.DataFrame, 
                            instrument: 'Instrument'):
        """Update file metadata for tracking"""
        metadata = {
            'file_path': str(file_path),
            'instrument_symbol': instrument.symbol,
            'instrument_type': instrument.__class__.__name__.lower(),
            'row_count': len(data),
            'file_size': file_path.stat().st_size,
            'last_updated': datetime.now().isoformat(),
            'columns': list(data.columns)
        }
        
        # Store metadata in companion .meta file
        meta_path = file_path.with_suffix('.meta')
        with open(meta_path, 'w') as f:
            json.dump(metadata, f, indent=2)
```

**Source Reference:** `src/vortex/infrastructure/storage/file_storage.py`

## 2. CSV Storage Implementation

### 2.1 Primary CSV Storage

**CSV Storage Implementation (From `src/vortex/infrastructure/storage/csv_storage.py`):**
```python
class CsvStorage(FileStorage):
    """CSV storage implementation with intelligent deduplication"""
    
    def __init__(self, output_dir: str):
        super().__init__(output_dir)
        self.format = "csv"
    
    def _write_dataframe(self, data: pd.DataFrame, file_path: Path, 
                        instrument: 'Instrument'):
        """Write DataFrame to CSV with proper formatting"""
        
        # Ensure timestamp index for proper CSV format
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'timestamp' in data.columns:
                data = data.set_index('timestamp')
        
        # Write CSV with standard formatting
        data.to_csv(
            file_path,
            index=True,
            index_label='timestamp',
            float_format='%.6f',
            date_format='%Y-%m-%d %H:%M:%S'
        )
    
    def load(self, instrument: 'Instrument', 
            correlation_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Load CSV data with correlation tracking"""
        correlation_id = correlation_id or self.correlation_manager.get_current_id()
        
        file_path = self._get_file_path(instrument)
        
        if not file_path.exists():
            return None
        
        try:
            with self.correlation_manager.correlation_context(
                correlation_id=correlation_id,
                operation="storage_load",
                file_path=str(file_path)
            ):
                # Load CSV with proper parsing
                df = pd.read_csv(
                    file_path,
                    index_col='timestamp',
                    parse_dates=True,
                    date_parser=pd.to_datetime
                )
                
                logger.info(f"Data loaded successfully",
                          extra={
                              'correlation_id': correlation_id,
                              'file_path': str(file_path),
                              'row_count': len(df)
                          })
                
                return df
                
        except Exception as e:
            logger.error(f"Storage load failed",
                        extra={'correlation_id': correlation_id, 'error': str(e)})
            return None
    
    def _get_file_path(self, instrument: 'Instrument') -> Path:
        """Generate standardized file path for instrument"""
        instrument_type = instrument.__class__.__name__.lower()
        period = getattr(instrument, 'periods', '1d')
        
        # Organized directory structure: {base_dir}/{type}s/{period}/{symbol}.csv
        return self.base_dir / f"{instrument_type}s" / period / f"{instrument.symbol}.csv"
```

### 2.2 Intelligent Deduplication

**Deduplication Algorithm (From `src/vortex/infrastructure/storage/csv_storage.py`):**
```python
def merge_with_existing(self, new_data: pd.DataFrame, 
                       existing_data: pd.DataFrame,
                       correlation_id: Optional[str] = None) -> pd.DataFrame:
    """Merge new data with existing data, handling overlaps intelligently"""
    
    if existing_data.empty:
        return new_data
    
    if new_data.empty:
        return existing_data
    
    try:
        # Ensure both DataFrames have datetime index
        if not isinstance(existing_data.index, pd.DatetimeIndex):
            existing_data.index = pd.to_datetime(existing_data.index)
        if not isinstance(new_data.index, pd.DatetimeIndex):
            new_data.index = pd.to_datetime(new_data.index)
        
        # Combine and remove duplicates (keep new data for overlaps)
        combined = pd.concat([existing_data, new_data])
        
        # Remove duplicate timestamps, keeping the new data (last occurrence)
        deduplicated = combined[~combined.index.duplicated(keep='last')]
        
        # Sort by timestamp
        result = deduplicated.sort_index()
        
        logger.info(f"Data merge completed",
                   extra={
                       'correlation_id': correlation_id,
                       'existing_rows': len(existing_data),
                       'new_rows': len(new_data),
                       'result_rows': len(result),
                       'duplicates_removed': len(combined) - len(result)
                   })
        
        return result
        
    except Exception as e:
        logger.error(f"Data merge failed: {e}",
                    extra={'correlation_id': correlation_id})
        
        # Fallback: return new data only
        return new_data
```

**Source Reference:** `src/vortex/infrastructure/storage/csv_storage.py`

## 3. Parquet Storage Implementation

### 3.1 Backup Parquet Storage

**Parquet Storage Implementation (From `src/vortex/infrastructure/storage/parquet_storage.py`):**
```python
class ParquetStorage(FileStorage):
    """Parquet storage implementation for backup and analytics"""
    
    def __init__(self, output_dir: str):
        super().__init__(output_dir)
        self.format = "parquet"
    
    def _write_dataframe(self, data: pd.DataFrame, file_path: Path, 
                        instrument: 'Instrument'):
        """Write DataFrame to Parquet with optimized settings"""
        
        # Ensure timestamp is properly formatted for Parquet
        if isinstance(data.index, pd.DatetimeIndex):
            # Reset index to column for Parquet compatibility
            data_to_save = data.reset_index()
        else:
            data_to_save = data.copy()
        
        # Write Parquet with compression and metadata
        data_to_save.to_parquet(
            file_path,
            engine='pyarrow',
            compression='snappy',
            index=False,
            metadata={
                'vortex_version': '1.0.0',
                'instrument_symbol': instrument.symbol,
                'instrument_type': instrument.__class__.__name__,
                'created_at': datetime.now().isoformat()
            }
        )
    
    def load(self, instrument: 'Instrument', 
            correlation_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Load Parquet data with timestamp index restoration"""
        correlation_id = correlation_id or self.correlation_manager.get_current_id()
        
        file_path = self._get_file_path(instrument)
        
        if not file_path.exists():
            return None
        
        try:
            with self.correlation_manager.correlation_context(
                correlation_id=correlation_id,
                operation="parquet_load"
            ):
                # Load Parquet file
                df = pd.read_parquet(file_path, engine='pyarrow')
                
                # Restore timestamp index if it exists
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df.set_index('timestamp', inplace=True)
                
                logger.info(f"Parquet data loaded successfully",
                          extra={'correlation_id': correlation_id, 'row_count': len(df)})
                
                return df
                
        except Exception as e:
            logger.error(f"Parquet load failed: {e}",
                        extra={'correlation_id': correlation_id})
            return None
    
    def _get_file_path(self, instrument: 'Instrument') -> Path:
        """Generate Parquet file path"""
        instrument_type = instrument.__class__.__name__.lower()
        period = getattr(instrument, 'periods', '1d')
        
        return self.base_dir / f"{instrument_type}s" / period / f"{instrument.symbol}.parquet"
```

**Source Reference:** `src/vortex/infrastructure/storage/parquet_storage.py`

### 3.2 Storage Orchestration

**Dual Storage Manager (From `src/vortex/infrastructure/storage/data_storage.py`):**
```python
class DualStorageManager:
    """Orchestrates CSV and Parquet storage operations"""
    
    def __init__(self, output_dir: str, backup_enabled: bool = True):
        self.csv_storage = CsvStorage(output_dir)
        self.parquet_storage = ParquetStorage(output_dir) if backup_enabled else None
        self.backup_enabled = backup_enabled
    
    def persist_with_backup(self, data: pd.DataFrame, instrument: 'Instrument',
                          correlation_id: Optional[str] = None) -> StorageResult:
        """Persist data to both CSV and Parquet storage"""
        correlation_id = correlation_id or get_correlation_manager().get_current_id()
        
        results = []
        
        # Primary CSV storage
        csv_result = self.csv_storage.persist(data, instrument, correlation_id)
        results.append(('CSV', csv_result))
        
        # Backup Parquet storage (if enabled)
        if self.backup_enabled and self.parquet_storage:
            parquet_result = self.parquet_storage.persist(data, instrument, correlation_id)
            results.append(('Parquet', parquet_result))
        
        # Log storage summary
        successful_stores = [fmt for fmt, result in results if result.success]
        failed_stores = [fmt for fmt, result in results if not result.success]
        
        logger.info(f"Storage operation completed",
                   extra={
                       'correlation_id': correlation_id,
                       'successful_formats': successful_stores,
                       'failed_formats': failed_stores,
                       'primary_file': csv_result.file_path if csv_result.success else None
                   })
        
        # Return primary (CSV) result
        return csv_result
    
    def load_with_fallback(self, instrument: 'Instrument',
                          correlation_id: Optional[str] = None) -> Optional[pd.DataFrame]:
        """Load data with Parquet fallback if CSV fails"""
        correlation_id = correlation_id or get_correlation_manager().get_current_id()
        
        # Try CSV first (primary)
        data = self.csv_storage.load(instrument, correlation_id)
        if data is not None:
            return data
        
        # Fallback to Parquet if enabled
        if self.backup_enabled and self.parquet_storage:
            logger.info(f"CSV load failed, trying Parquet fallback",
                       extra={'correlation_id': correlation_id})
            return self.parquet_storage.load(instrument, correlation_id)
        
        return None
```

**Source Reference:** `src/vortex/infrastructure/storage/data_storage.py`

## 4. Metadata Management Implementation

### 4.1 File Metadata Tracking

**Metadata Storage (From `src/vortex/infrastructure/storage/metadata.py`):**
```python
class FileMetadata:
    """File metadata management for storage tracking"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.metadata_file = self.base_dir / '.vortex_metadata.json'
        self._metadata_cache = {}
        self._lock = threading.RLock()
    
    def update_file_metadata(self, file_path: str, data: pd.DataFrame, 
                           instrument: 'Instrument'):
        """Update metadata for a stored file"""
        with self._lock:
            file_key = str(Path(file_path).relative_to(self.base_dir))
            
            metadata_entry = {
                'file_path': file_key,
                'instrument_symbol': instrument.symbol,
                'instrument_type': instrument.__class__.__name__.lower(),
                'row_count': len(data),
                'columns': list(data.columns),
                'date_range': {
                    'start': data.index.min().isoformat() if not data.empty else None,
                    'end': data.index.max().isoformat() if not data.empty else None
                },
                'file_size': Path(file_path).stat().st_size,
                'last_updated': datetime.now().isoformat(),
                'checksum': self._calculate_checksum(file_path)
            }
            
            # Update cache
            self._metadata_cache[file_key] = metadata_entry
            
            # Persist metadata
            self._save_metadata()
    
    def get_file_metadata(self, instrument: 'Instrument') -> Optional[Dict[str, Any]]:
        """Get metadata for instrument file"""
        file_path = self._get_relative_file_path(instrument)
        return self._metadata_cache.get(str(file_path))
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate file checksum for integrity validation"""
        import hashlib
        
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _save_metadata(self):
        """Persist metadata cache to disk"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self._metadata_cache, f, indent=2)
```

**Source Reference:** `src/vortex/infrastructure/storage/metadata.py`

## 5. Storage Path Organization

### 5.1 Directory Structure Implementation

**Path Generation Algorithm:**
```python
def _get_file_path(self, instrument: 'Instrument') -> Path:
    """Generate organized file path for instrument"""
    
    # Extract instrument characteristics
    instrument_type = instrument.__class__.__name__.lower()  # stock, future, forex
    symbol = instrument.symbol
    period = getattr(instrument, 'periods', '1d')
    
    # Generate organized path: {base}/{type}s/{period}/{symbol}.{ext}
    # Examples:
    # - stocks/1d/AAPL.csv
    # - futures/1h/GC.csv  
    # - forex/5m/EURUSD.csv
    
    return self.base_dir / f"{instrument_type}s" / period / f"{symbol}.{self.format}"

def _ensure_directory_structure(self, instrument: 'Instrument'):
    """Create directory structure if it doesn't exist"""
    file_path = self._get_file_path(instrument)
    file_path.parent.mkdir(parents=True, exist_ok=True)
```

**Directory Structure Examples:**
```
data/
├── stocks/
│   ├── 1d/          # Daily stock data
│   │   ├── AAPL.csv
│   │   ├── AAPL.parquet
│   │   └── GOOGL.csv
│   ├── 1h/          # Hourly stock data
│   └── 5m/          # 5-minute stock data
├── futures/
│   ├── 1d/          # Daily futures data
│   │   ├── GC.csv   # Gold futures
│   │   └── CL.csv   # Crude oil futures
│   └── 1h/
└── forex/
    ├── 1d/
    └── 4h/
```

## 6. Storage Error Handling and Recovery

### 6.1 Error Recovery Strategies

**Storage Error Handling (From `src/vortex/infrastructure/storage/file_storage.py`):**
```python
class StorageRecoveryManager:
    """Handles storage errors and recovery scenarios"""
    
    def recover_from_corruption(self, instrument: 'Instrument') -> bool:
        """Recover from file corruption using backup"""
        try:
            csv_path = self.csv_storage._get_file_path(instrument)
            backup_path = csv_path.with_suffix(csv_path.suffix + '.backup')
            
            if backup_path.exists():
                # Restore from backup
                shutil.copy2(backup_path, csv_path)
                logger.info(f"Recovered from backup: {csv_path}")
                return True
            
            # Try Parquet fallback
            if self.parquet_storage:
                parquet_data = self.parquet_storage.load(instrument)
                if parquet_data is not None:
                    # Restore CSV from Parquet
                    result = self.csv_storage.persist(parquet_data, instrument)
                    if result.success:
                        logger.info(f"Recovered CSV from Parquet: {csv_path}")
                        return True
            
            logger.error(f"Could not recover file: {csv_path}")
            return False
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            return False
    
    def validate_file_integrity(self, instrument: 'Instrument') -> bool:
        """Validate file integrity using metadata checksums"""
        try:
            file_path = self.csv_storage._get_file_path(instrument)
            if not file_path.exists():
                return True  # Non-existent files are valid
            
            # Get stored metadata
            metadata = self.metadata_manager.get_file_metadata(instrument)
            if not metadata:
                return True  # No metadata to validate against
            
            # Calculate current checksum
            current_checksum = self.metadata_manager._calculate_checksum(str(file_path))
            stored_checksum = metadata.get('checksum')
            
            if current_checksum != stored_checksum:
                logger.warning(f"File integrity check failed: {file_path}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Integrity validation failed: {e}")
            return False
```

### 6.2 Storage Monitoring and Health

**Storage Health Monitoring:**
```python
class StorageHealthMonitor:
    """Monitor storage system health and performance"""
    
    def __init__(self, storage_manager: DualStorageManager):
        self.storage_manager = storage_manager
        self.metrics = {}
    
    def check_storage_health(self) -> Dict[str, Any]:
        """Comprehensive storage health check"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'issues': []
        }
        
        try:
            # Check disk space
            disk_usage = self._check_disk_space()
            if disk_usage['available_gb'] < 1.0:  # Less than 1GB available
                health_status['issues'].append("Low disk space")
                health_status['overall_status'] = 'warning'
            
            # Check file system permissions
            if not self._check_write_permissions():
                health_status['issues'].append("Write permission denied")
                health_status['overall_status'] = 'error'
            
            # Check storage consistency
            consistency_issues = self._check_storage_consistency()
            if consistency_issues:
                health_status['issues'].extend(consistency_issues)
                health_status['overall_status'] = 'warning'
            
            health_status.update({
                'disk_usage': disk_usage,
                'total_files': self._count_data_files(),
                'backup_status': 'enabled' if self.storage_manager.backup_enabled else 'disabled'
            })
            
        except Exception as e:
            health_status['overall_status'] = 'error'
            health_status['issues'].append(f"Health check failed: {e}")
        
        return health_status
    
    def _check_disk_space(self) -> Dict[str, float]:
        """Check available disk space"""
        import shutil
        
        total, used, free = shutil.disk_usage(self.storage_manager.csv_storage.base_dir)
        
        return {
            'total_gb': total / (1024**3),
            'used_gb': used / (1024**3),
            'available_gb': free / (1024**3),
            'usage_percentage': (used / total) * 100
        }
    
    def _check_storage_consistency(self) -> List[str]:
        """Check consistency between CSV and Parquet storage"""
        issues = []
        
        if not self.storage_manager.backup_enabled:
            return issues
        
        # Find all CSV files
        csv_files = list(self.storage_manager.csv_storage.base_dir.glob('**/*.csv'))
        
        for csv_file in csv_files:
            # Check if corresponding Parquet exists
            relative_path = csv_file.relative_to(self.storage_manager.csv_storage.base_dir)
            parquet_path = self.storage_manager.parquet_storage.base_dir / relative_path.with_suffix('.parquet')
            
            if not parquet_path.exists():
                issues.append(f"Missing Parquet backup for {relative_path}")
        
        return issues
```

## 7. Storage Configuration and Management

### 7.1 Storage Configuration

**Storage Configuration Models:**
```python
class StorageConfig(BaseModel):
    """Storage system configuration"""
    
    output_directory: str = Field(default="./data", description="Base output directory")
    backup_enabled: bool = Field(default=True, description="Enable Parquet backup storage")
    compression: str = Field(default="snappy", description="Parquet compression algorithm")
    max_file_size_mb: int = Field(default=100, description="Maximum file size in MB")
    cleanup_enabled: bool = Field(default=False, description="Enable automatic cleanup")
    retention_days: int = Field(default=365, description="Data retention period in days")
    
    @validator('output_directory')
    def validate_output_directory(cls, v):
        path = Path(v)
        if not path.is_absolute():
            # Convert to absolute path
            v = str(path.resolve())
        return v
    
    @validator('max_file_size_mb')
    def validate_max_file_size(cls, v):
        if v <= 0 or v > 1000:  # Reasonable limits
            raise ValueError("Max file size must be between 1 and 1000 MB")
        return v
```

### 7.2 Storage Factory Pattern

**Storage Factory Implementation:**
```python
class StorageFactory:
    """Factory for creating storage backends"""
    
    @staticmethod
    def create_storage(config: StorageConfig) -> DualStorageManager:
        """Create configured storage manager"""
        
        # Ensure output directory exists
        output_dir = Path(config.output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create storage manager
        storage_manager = DualStorageManager(
            output_dir=str(output_dir),
            backup_enabled=config.backup_enabled
        )
        
        # Configure Parquet compression if backup enabled
        if config.backup_enabled and storage_manager.parquet_storage:
            storage_manager.parquet_storage.compression = config.compression
        
        return storage_manager
    
    @staticmethod
    def create_csv_only_storage(output_dir: str) -> CsvStorage:
        """Create CSV-only storage for simple use cases"""
        return CsvStorage(output_dir)
    
    @staticmethod
    def create_parquet_only_storage(output_dir: str) -> ParquetStorage:
        """Create Parquet-only storage for analytics use cases"""
        return ParquetStorage(output_dir)
```

## 8. Testing Storage Implementation

### 8.1 Storage Unit Testing

**Storage Testing Patterns:**
```python
class TestCsvStorage:
    """Unit tests for CSV storage implementation"""
    
    @pytest.fixture
    def csv_storage(self, tmp_path):
        """CSV storage fixture"""
        return CsvStorage(str(tmp_path))
    
    @pytest.fixture
    def sample_data(self):
        """Sample OHLCV data for testing"""
        return FinancialDataFactory.create_ohlcv_data("AAPL", days=5)
    
    def test_persist_new_file(self, csv_storage, sample_data):
        """Test persisting data to new file"""
        instrument = Stock(symbol="AAPL", periods="1d")
        
        result = csv_storage.persist(sample_data, instrument)
        
        assert result.success is True
        assert result.file_path is not None
        assert result.row_count == len(sample_data)
        
        # Verify file exists
        assert Path(result.file_path).exists()
    
    def test_persist_with_merge(self, csv_storage, sample_data):
        """Test data merging with existing file"""
        instrument = Stock(symbol="AAPL", periods="1d")
        
        # Save initial data
        initial_result = csv_storage.persist(sample_data, instrument)
        assert initial_result.success is True
        
        # Create overlapping data
        new_dates = pd.date_range('2024-01-03', periods=5, freq='D')
        new_data = FinancialDataFactory.create_ohlcv_data("AAPL", days=5)
        new_data.index = new_dates
        
        # Save overlapping data (should merge)
        merge_result = csv_storage.persist(new_data, instrument)
        
        assert merge_result.success is True
        
        # Load and verify merged data
        loaded_data = csv_storage.load(instrument)
        assert loaded_data is not None
        assert len(loaded_data) > len(sample_data)  # Should have more data after merge
    
    def test_load_nonexistent_file(self, csv_storage):
        """Test loading non-existent file"""
        instrument = Stock(symbol="NONEXISTENT", periods="1d")
        
        result = csv_storage.load(instrument)
        
        assert result is None
```

### 8.2 Storage Integration Testing

**Dual Storage Integration Tests:**
```python
class TestDualStorageIntegration:
    """Integration tests for dual storage system"""
    
    def test_csv_parquet_consistency(self, tmp_path):
        """Test consistency between CSV and Parquet storage"""
        storage_manager = DualStorageManager(str(tmp_path), backup_enabled=True)
        
        # Create test data
        data = FinancialDataFactory.create_ohlcv_data("AAPL", days=10)
        instrument = Stock(symbol="AAPL", periods="1d")
        
        # Persist to both formats
        result = storage_manager.persist_with_backup(data, instrument)
        assert result.success is True
        
        # Load from both storages
        csv_data = storage_manager.csv_storage.load(instrument)
        parquet_data = storage_manager.parquet_storage.load(instrument)
        
        # Verify consistency
        assert csv_data is not None
        assert parquet_data is not None
        pd.testing.assert_frame_equal(csv_data, parquet_data)
    
    def test_storage_fallback_mechanism(self, tmp_path):
        """Test Parquet fallback when CSV is corrupted"""
        storage_manager = DualStorageManager(str(tmp_path), backup_enabled=True)
        
        # Save data
        data = FinancialDataFactory.create_ohlcv_data("AAPL", days=5)
        instrument = Stock(symbol="AAPL", periods="1d")
        
        storage_manager.persist_with_backup(data, instrument)
        
        # Corrupt CSV file
        csv_path = storage_manager.csv_storage._get_file_path(instrument)
        with open(csv_path, 'w') as f:
            f.write("corrupted,data,here")
        
        # Load with fallback (should use Parquet)
        recovered_data = storage_manager.load_with_fallback(instrument)
        
        assert recovered_data is not None
        assert len(recovered_data) == len(data)
```

## 9. Storage Implementation Summary

### 9.1 Architecture Achievements

**✅ Dual Storage Implementation:**
- CSV primary storage with standardized OHLCV format
- Parquet backup storage with compression and metadata
- Atomic write operations with temporary file pattern
- Intelligent deduplication and data merging

**✅ Correlation Integration:**
- Request tracking throughout storage operations
- Structured logging with correlation IDs
- Performance metrics and operation timing

**✅ Error Handling and Recovery:**
- Backup and restoration mechanisms
- File integrity validation with checksums
- Graceful fallback between storage formats

**✅ Metadata Management:**
- Comprehensive file metadata tracking
- Storage health monitoring and validation
- Organized directory structure by instrument type and period

### 9.2 Storage Patterns Summary

| Pattern | Purpose | Implementation | Benefits |
|---------|---------|---------------|----------|
| **Atomic Operations** | Data consistency | Temporary file + rename | Prevents corruption |
| **Dual Storage** | Redundancy | CSV + Parquet | Data durability |
| **Intelligent Merge** | Deduplication | Timestamp-based merge | Handles overlapping data |
| **Correlation Tracking** | Observability | Context managers | Request tracing |
| **Metadata Management** | File tracking | JSON metadata files | Integrity validation |
| **Recovery Mechanisms** | Fault tolerance | Backup restoration | Data protection |

The current storage implementation provides production-ready data persistence with comprehensive error handling, correlation tracking, and dual-format redundancy.

## Related Documents

- **[Storage Architecture](../hld/05-storage-architecture.md)** - High-level storage design
- **[Component Implementation](01-component-implementation.md)** - Overall component implementation
- **[Data Flow Design](../hld/03-data-flow-design.md)** - Data processing flow
- **[Security Design](../hld/06-security-design.md)** - Storage security implementation

---

**Next Review:** 2026-02-16  
**Reviewers:** Senior Developer, Storage Engineer, QA Lead