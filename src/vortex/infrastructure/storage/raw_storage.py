"""
Raw data storage for compliance and debugging.

This module provides storage for untampered raw data exactly as received
from providers, compressed as gzipped CSV files for raw data trail purposes.
"""

import gzip
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from vortex.core.correlation import get_correlation_manager
from vortex.models.instrument import Instrument
import logging

logger = logging.getLogger(__name__)


class RawDataStorage:
    """Storage for raw provider data in gzipped CSV format for raw data trail."""
    
    def __init__(self, 
                 base_dir: str, 
                 enabled: bool = True,
                 retention_days: Optional[int] = None,
                 compress: bool = True,
                 include_metadata: bool = True):
        """Initialize raw data storage.
        
        Args:
            base_dir: Base directory for raw data files
            enabled: Whether raw data storage is enabled
            retention_days: Number of days to retain raw data files (None for unlimited)
            compress: Whether to compress raw data files with gzip
            include_metadata: Whether to include request metadata with raw data files
        """
        self.base_dir = Path(base_dir)
        self.enabled = enabled
        self.retention_days = retention_days
        self.compress = compress
        self.include_metadata = include_metadata
        self.correlation_manager = get_correlation_manager()
        
        # Always define raw_dir property for consistent interface
        self.raw_dir = self.base_dir / "raw"
        
        if self.enabled:
            # Create raw data directory structure only when enabled
            self.raw_dir.mkdir(parents=True, exist_ok=True)
    
    def save_raw_response(self, 
                         provider: str,
                         instrument: Instrument,
                         raw_data: str,
                         request_metadata: Optional[Dict[str, Any]] = None,
                         correlation_id: Optional[str] = None) -> Optional[str]:
        """Save raw provider response as gzipped CSV with metadata.
        
        Args:
            provider: Provider name (e.g., 'barchart', 'yahoo', 'ibkr')
            instrument: Instrument that was requested
            raw_data: Raw response data as string
            request_metadata: Optional metadata about the request
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            Path to saved raw data file, or None if disabled
        """
        if not self.enabled:
            return None
            
        correlation_id = correlation_id or self.correlation_manager.get_current_id()
        
        try:
            # Generate raw data file path
            raw_file_path = self._generate_raw_file_path(provider, instrument)
            
            # Ensure directory exists
            raw_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare metadata if enabled
            metadata = None
            if self.include_metadata:
                metadata = self._create_raw_metadata(
                    provider, instrument, raw_data, request_metadata, correlation_id
                )
            
            # Save raw data (compressed or uncompressed based on config)
            if self.compress:
                with gzip.open(raw_file_path, 'wt', encoding='utf-8') as f:
                    f.write(raw_data)
            else:
                # Save as plain text file if compression disabled
                plain_file_path = raw_file_path.with_suffix('.csv')
                with open(plain_file_path, 'w', encoding='utf-8') as f:
                    f.write(raw_data)
                raw_file_path = plain_file_path
            
            # Save metadata companion file if enabled
            if self.include_metadata and metadata:
                metadata_path = raw_file_path.with_suffix('.meta.json')
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)
            
            logger.info(
                f"Raw data saved for {provider}",
                extra={
                    'correlation_id': correlation_id,
                    'provider': provider,
                    'symbol': getattr(instrument, 'symbol', str(instrument)),
                    'raw_file': str(raw_file_path),
                    'raw_data_size': len(raw_data)
                }
            )
            
            return str(raw_file_path)
            
        except Exception as e:
            logger.error(
                f"Failed to save raw data for {provider}",
                extra={
                    'correlation_id': correlation_id,
                    'provider': provider,
                    'error': str(e)
                }
            )
            # Don't fail the entire operation due to raw data storage issues
            return None
    
    def _generate_raw_file_path(self, provider: str, instrument: Instrument) -> Path:
        """Generate standardized raw data file path.
        
        Format: raw/{provider}/{year}/{month}/{instrument_type}/{symbol}_{timestamp}.csv.gz
        
        Args:
            provider: Provider name
            instrument: Instrument object
            
        Returns:
            Path object for the raw data file
        """
        now = datetime.now()
        symbol = getattr(instrument, 'symbol', str(instrument))
        instrument_type = instrument.__class__.__name__.lower()
        
        # Create timestamp for unique filename
        timestamp = now.strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
        
        # Choose file extension based on compression setting
        file_extension = ".csv.gz" if self.compress else ".csv"
        
        # Organize by provider/year/month/instrument_type for easy browsing
        return (self.raw_dir / 
                provider.lower() / 
                str(now.year) / 
                f"{now.month:02d}" / 
                instrument_type / 
                f"{symbol}_{timestamp}{file_extension}")
    
    def _create_raw_metadata(self, 
                            provider: str,
                            instrument: Instrument,
                            raw_data: str,
                            request_metadata: Optional[Dict[str, Any]],
                            correlation_id: str) -> Dict[str, Any]:
        """Create comprehensive raw data metadata.
        
        Args:
            provider: Provider name
            instrument: Instrument object
            raw_data: Raw response data
            request_metadata: Request metadata
            correlation_id: Correlation ID
            
        Returns:
            Dictionary with raw data metadata
        """
        return {
            'raw_info': {
                'created_at': datetime.now().isoformat(),
                'correlation_id': correlation_id,
                'vortex_version': '2.0.0'  # Should be dynamic in production
            },
            'provider_info': {
                'name': provider,
                'data_source': 'external_api'
            },
            'instrument_info': {
                'symbol': getattr(instrument, 'symbol', str(instrument)),
                'type': instrument.__class__.__name__.lower(),
                'period': getattr(instrument, 'period', None),
                'periods': getattr(instrument, 'periods', None)
            },
            'request_info': request_metadata or {},
            'data_info': {
                'raw_size_bytes': len(raw_data.encode('utf-8')),
                'raw_lines': len(raw_data.splitlines()),
                'is_csv': self._is_csv_format(raw_data),
                'encoding': 'utf-8'
            }
        }
    
    def _is_csv_format(self, data: str) -> bool:
        """Check if data appears to be CSV format.
        
        Args:
            data: Raw data string
            
        Returns:
            True if data appears to be CSV
        """
        if not data.strip():
            return False
            
        lines = data.strip().split('\n')
        if len(lines) < 2:
            return False
            
        # Check if first line has comma-separated headers
        first_line = lines[0]
        return ',' in first_line and len(first_line.split(',')) > 1
    
    def get_raw_files_for_instrument(self, 
                                      provider: str, 
                                      instrument: Instrument,
                                      start_date: Optional[datetime] = None,
                                      end_date: Optional[datetime] = None) -> list[Path]:
        """Get list of raw data files for a specific instrument.
        
        Args:
            provider: Provider name
            instrument: Instrument object
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of raw data file paths
        """
        if not self.enabled:
            return []
            
        symbol = getattr(instrument, 'symbol', str(instrument))
        instrument_type = instrument.__class__.__name__.lower()
        
        # Search pattern
        search_pattern = (self.raw_dir / 
                         provider.lower() / 
                         "**" / 
                         instrument_type / 
                         f"{symbol}_*.csv.gz")
        
        raw_files = list(search_pattern.parent.glob(search_pattern.name))
        
        # Filter by date if provided
        if start_date or end_date:
            filtered_files = []
            for file_path in raw_files:
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if start_date and file_time < start_date:
                    continue
                if end_date and file_time > end_date:
                    continue
                filtered_files.append(file_path)
            return filtered_files
            
        return raw_files
    
    def cleanup_old_raw_files(self, retention_days: int = 90) -> int:
        """Clean up raw data files older than retention period.
        
        Args:
            retention_days: Number of days to retain raw data files
            
        Returns:
            Number of files deleted
        """
        if not self.enabled:
            return 0
            
        cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 3600)
        deleted_count = 0
        
        try:
            for raw_file in self.raw_dir.rglob("*.csv.gz"):
                if raw_file.stat().st_mtime < cutoff_time:
                    # Also remove metadata file if it exists
                    meta_file = raw_file.with_suffix('.meta.json')
                    if meta_file.exists():
                        meta_file.unlink()
                    
                    raw_file.unlink()
                    deleted_count += 1
                    
            logger.info(f"Cleaned up {deleted_count} old raw data files (retention: {retention_days} days)")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup raw data files: {e}")
            return 0