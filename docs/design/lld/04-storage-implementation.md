# Storage Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Storage Architecture](../hld/05-storage-architecture.md)

## 1. Storage Interface Implementation

### 1.1 Abstract Storage Base Class
```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
import json
import shutil

class DataStorage(ABC):
    """Abstract base class for data storage implementations"""
    
    def __init__(self, base_directory: str, dry_run: bool = False):
        self.base_directory = Path(base_directory)
        self.dry_run = dry_run
        self.metadata_store = None
        
    @abstractmethod
    def save(self, data: pd.DataFrame, filepath: str, **kwargs) -> 'SaveResult':
        """Save DataFrame to storage with specified path"""
        pass
    
    @abstractmethod
    def load(self, filepath: str, **kwargs) -> pd.DataFrame:
        """Load DataFrame from storage"""
        pass
    
    @abstractmethod
    def exists(self, filepath: str) -> bool:
        """Check if file exists in storage"""
        pass
    
    @abstractmethod
    def delete(self, filepath: str) -> bool:
        """Delete file from storage"""
        pass
    
    @abstractmethod
    def list_files(self, pattern: str = "*") -> List[str]:
        """List files matching pattern"""
        pass
    
    def get_file_info(self, filepath: str) -> 'FileInfo':
        """Get detailed file information"""
        if not self.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        full_path = self.base_directory / filepath
        stat = full_path.stat()
        
        return FileInfo(
            path=filepath,
            size_bytes=stat.st_size,
            created=datetime.fromtimestamp(stat.st_ctime),
            modified=datetime.fromtimestamp(stat.st_mtime),
            format=self._detect_format(filepath)
        )
    
    def get_storage_stats(self) -> 'StorageStats':
        """Get overall storage statistics"""
        files = self.list_files()
        total_size = sum(self.get_file_info(f).size_bytes for f in files)
        
        return StorageStats(
            total_files=len(files),
            total_size_bytes=total_size,
            storage_type=self.__class__.__name__,
            base_directory=str(self.base_directory)
        )
        
    def _detect_format(self, filepath: str) -> str:
        """Detect file format from extension"""
        return Path(filepath).suffix.lower().lstrip('.')
```

### 1.2 File Storage Base Implementation
```python
class FileStorage(DataStorage):
    """Base implementation for file-based storage"""
    
    def __init__(self, base_directory: str, dry_run: bool = False, 
                 create_subdirs: bool = True, backup_enabled: bool = False):
        super().__init__(base_directory, dry_run)
        self.create_subdirs = create_subdirs
        self.backup_enabled = backup_enabled
        self.metadata_store = MetadataStore(self.base_directory / ".metadata")
        
        # Ensure base directory exists
        if not dry_run:
            self.base_directory.mkdir(parents=True, exist_ok=True)
    
    def _prepare_file_path(self, filepath: str) -> Path:
        """Prepare and validate file path"""
        full_path = self.base_directory / filepath
        
        # Create parent directories if needed
        if self.create_subdirs and not self.dry_run:
            full_path.parent.mkdir(parents=True, exist_ok=True)
        
        return full_path
    
    def _atomic_save(self, data: pd.DataFrame, filepath: str, 
                    save_func: callable) -> 'SaveResult':
        """Perform atomic save operation with backup"""
        full_path = self._prepare_file_path(filepath)
        temp_path = full_path.with_suffix(full_path.suffix + '.tmp')
        backup_path = full_path.with_suffix(full_path.suffix + '.backup')
        
        try:
            # Save to temporary file first
            save_func(data, temp_path)
            
            # Create backup if file exists
            if full_path.exists() and self.backup_enabled:
                shutil.copy2(full_path, backup_path)
            
            # Atomic move from temp to final location
            shutil.move(temp_path, full_path)
            
            # Update metadata
            if self.metadata_store:
                self.metadata_store.update_file_metadata(
                    filepath, len(data), data.memory_usage(deep=True).sum()
                )
            
            return SaveResult(
                success=True,
                filepath=str(full_path),
                row_count=len(data),
                file_size_bytes=full_path.stat().st_size
            )
            
        except Exception as e:
            # Cleanup temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            
            # Restore from backup if needed
            if backup_path.exists() and not full_path.exists():
                shutil.move(backup_path, full_path)
            
            raise StorageError(f"Failed to save {filepath}: {e}") from e
        
        finally:
            # Cleanup backup file
            if backup_path.exists():
                backup_path.unlink()
```

## 2. CSV Storage Implementation

### 2.1 CSV Storage Class
```python
class CsvStorage(FileStorage):
    """CSV file storage implementation"""
    
    def __init__(self, base_directory: str, dry_run: bool = False,
                 encoding: str = 'utf-8', delimiter: str = ',',
                 float_precision: int = 6):
        super().__init__(base_directory, dry_run)
        self.encoding = encoding
        self.delimiter = delimiter
        self.float_precision = float_precision
        
    def save(self, data: pd.DataFrame, filepath: str, **kwargs) -> SaveResult:
        """Save DataFrame as CSV file"""
        if self.dry_run:
            return SaveResult(
                success=True,
                filepath=filepath,
                row_count=len(data),
                file_size_bytes=0,
                dry_run=True
            )
        
        def csv_save_func(df: pd.DataFrame, path: Path):
            df.to_csv(
                path,
                index=False,
                encoding=self.encoding,
                sep=self.delimiter,
                float_format=f'%.{self.float_precision}f',
                date_format='%Y-%m-%d %H:%M:%S'
            )
        
        return self._atomic_save(data, filepath, csv_save_func)
    
    def load(self, filepath: str, **kwargs) -> pd.DataFrame:
        """Load DataFrame from CSV file"""
        full_path = self.base_directory / filepath
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        try:
            return pd.read_csv(
                full_path,
                encoding=self.encoding,
                sep=self.delimiter,
                parse_dates=['timestamp'] if 'timestamp' in kwargs.get('columns', []) else False
            )
        except Exception as e:
            raise StorageError(f"Failed to load {filepath}: {e}") from e
    
    def exists(self, filepath: str) -> bool:
        """Check if CSV file exists"""
        return (self.base_directory / filepath).exists()
    
    def delete(self, filepath: str) -> bool:
        """Delete CSV file"""
        full_path = self.base_directory / filepath
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    
    def list_files(self, pattern: str = "*.csv") -> List[str]:
        """List CSV files matching pattern"""
        files = self.base_directory.glob(pattern)
        return [str(f.relative_to(self.base_directory)) for f in files if f.is_file()]
```

## 3. Parquet Storage Implementation

### 3.1 Parquet Storage Class
```python
import pyarrow as pa
import pyarrow.parquet as pq

class ParquetStorage(FileStorage):
    """Parquet file storage implementation"""
    
    def __init__(self, base_directory: str, dry_run: bool = False,
                 compression: str = 'snappy', engine: str = 'pyarrow'):
        super().__init__(base_directory, dry_run)
        self.compression = compression
        self.engine = engine
        
    def save(self, data: pd.DataFrame, filepath: str, **kwargs) -> SaveResult:
        """Save DataFrame as Parquet file"""
        if self.dry_run:
            return SaveResult(
                success=True,
                filepath=filepath,
                row_count=len(data),
                file_size_bytes=0,
                dry_run=True
            )
        
        def parquet_save_func(df: pd.DataFrame, path: Path):
            # Convert timestamp columns to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Save with compression
            df.to_parquet(
                path,
                engine=self.engine,
                compression=self.compression,
                index=False
            )
        
        return self._atomic_save(data, filepath, parquet_save_func)
    
    def load(self, filepath: str, **kwargs) -> pd.DataFrame:
        """Load DataFrame from Parquet file"""
        full_path = self.base_directory / filepath
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        try:
            return pd.read_parquet(full_path, engine=self.engine)
        except Exception as e:
            raise StorageError(f"Failed to load {filepath}: {e}") from e
    
    def exists(self, filepath: str) -> bool:
        """Check if Parquet file exists"""
        return (self.base_directory / filepath).exists()
    
    def delete(self, filepath: str) -> bool:
        """Delete Parquet file"""
        full_path = self.base_directory / filepath
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    
    def list_files(self, pattern: str = "*.parquet") -> List[str]:
        """List Parquet files matching pattern"""
        files = self.base_directory.glob(pattern)
        return [str(f.relative_to(self.base_directory)) for f in files if f.is_file()]
```

## 4. Deduplication Implementation

### 4.1 Data Deduplication Engine
```python
class DataDeduplicator:
    """Handles data deduplication and conflict resolution"""
    
    def __init__(self, provider_priority: List[str] = None):
        self.provider_priority = provider_priority or ['barchart', 'ibkr', 'yahoo']
        
    def deduplicate_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicates and resolve conflicts"""
        if data.empty:
            return data
            
        # Identify composite key columns
        key_columns = ['timestamp', 'symbol']
        if not all(col in data.columns for col in key_columns):
            raise ValueError(f"Data must contain columns: {key_columns}")
        
        # Sort by provider priority for conflict resolution
        if 'provider' in data.columns:
            provider_order = {provider: i for i, provider in enumerate(self.provider_priority)}
            data['_priority'] = data['provider'].map(provider_order).fillna(999)
            data = data.sort_values(['_priority'] + key_columns)
            data = data.drop('_priority', axis=1)
        
        # Remove duplicates keeping first (highest priority)
        deduplicated = data.drop_duplicates(subset=key_columns, keep='first')
        
        return deduplicated.sort_values(key_columns).reset_index(drop=True)
    
    def merge_datasets(self, existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
        """Merge new data with existing data"""
        if existing.empty:
            return self.deduplicate_data(new)
        if new.empty:
            return existing
            
        # Combine datasets
        combined = pd.concat([existing, new], ignore_index=True)
        
        # Deduplicate the combined dataset
        return self.deduplicate_data(combined)
```

## 5. Metadata Management Implementation

### 5.1 Metadata Store
```python
class MetadataStore:
    """Manages storage metadata and statistics"""
    
    def __init__(self, metadata_directory: Path):
        self.metadata_directory = Path(metadata_directory)
        self.metadata_directory.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.metadata_directory / "storage_metadata.json"
        self._load_metadata()
    
    def _load_metadata(self):
        """Load existing metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                self.metadata = json.load(f)
        else:
            self.metadata = {
                "files": {},
                "statistics": {
                    "total_files": 0,
                    "total_size_bytes": 0,
                    "last_updated": None
                }
            }
    
    def _save_metadata(self):
        """Save metadata to disk"""
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2, default=str)
    
    def update_file_metadata(self, filepath: str, row_count: int, 
                           memory_usage: int):
        """Update metadata for a file"""
        self.metadata["files"][filepath] = {
            "row_count": row_count,
            "memory_usage_bytes": memory_usage,
            "last_updated": datetime.utcnow().isoformat(),
            "format": Path(filepath).suffix.lower().lstrip('.')
        }
        
        # Update statistics
        self.metadata["statistics"]["total_files"] = len(self.metadata["files"])
        self.metadata["statistics"]["last_updated"] = datetime.utcnow().isoformat()
        
        self._save_metadata()
    
    def get_file_metadata(self, filepath: str) -> Dict[str, Any]:
        """Get metadata for specific file"""
        return self.metadata["files"].get(filepath, {})
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get overall storage statistics"""
        return self.metadata["statistics"]
```

## 6. Storage Factory Implementation

### 6.1 Storage Factory
```python
class StorageFactory:
    """Factory for creating storage instances"""
    
    _storage_types = {
        'csv': CsvStorage,
        'parquet': ParquetStorage
    }
    
    @classmethod
    def create_storage(cls, storage_type: str, base_directory: str, 
                      **kwargs) -> DataStorage:
        """Create storage instance of specified type"""
        if storage_type not in cls._storage_types:
            raise ValueError(f"Unknown storage type: {storage_type}")
        
        storage_class = cls._storage_types[storage_type]
        return storage_class(base_directory, **kwargs)
    
    @classmethod
    def create_dual_storage(cls, base_directory: str, 
                          primary_format: str = 'csv',
                          backup_format: str = 'parquet') -> Dict[str, DataStorage]:
        """Create primary and backup storage instances"""
        return {
            'primary': cls.create_storage(primary_format, base_directory),
            'backup': cls.create_storage(backup_format, base_directory)
        }
```

## 7. Data Model Classes

### 7.1 Storage Result Classes
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class SaveResult:
    """Result of a save operation"""
    success: bool
    filepath: str
    row_count: int
    file_size_bytes: int
    dry_run: bool = False
    error_message: Optional[str] = None

@dataclass
class FileInfo:
    """File information metadata"""
    path: str
    size_bytes: int
    created: datetime
    modified: datetime
    format: str
    row_count: Optional[int] = None

@dataclass
class StorageStats:
    """Overall storage statistics"""
    total_files: int
    total_size_bytes: int
    storage_type: str
    base_directory: str
    last_updated: Optional[datetime] = None
```

## Related Documents

- **[Storage Architecture](../hld/05-storage-architecture.md)** - High-level storage design
- **[Component Implementation](01-component-implementation.md)** - Component integration details
- **[Data Processing Implementation](02-data-processing-implementation.md)** - Data flow integration

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** Senior Developer, Storage Engineer