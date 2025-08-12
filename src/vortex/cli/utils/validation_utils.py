"""
Validation utilities shared across CLI commands.

This module extracts shared validation logic to prevent circular dependencies
between CLI command modules.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from vortex.models.columns import (
    DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, 
    CLOSE_COLUMN, VOLUME_COLUMN, validate_required_columns,
    validate_column_data_types
)
from vortex.exceptions import CLIError
from vortex.constants import BYTES_PER_KB, BYTES_PER_MB


def validate_csv_file(file_path: Path) -> Dict[str, Any]:
    """Validate a CSV file for data integrity.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Dictionary with validation results
        
    Raises:
        CLIError: If file cannot be read
    """
    if not file_path.exists():
        raise CLIError(f"File not found: {file_path}")
    
    if not file_path.suffix.lower() == '.csv':
        raise CLIError(f"Not a CSV file: {file_path}")
    
    try:
        # Read CSV file
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        # Get file info
        file_size = file_path.stat().st_size
        
        # Basic validation results
        result = {
            'file_path': str(file_path),
            'file_size': _format_file_size(file_size),
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': list(df.columns),
            'issues': [],
            'warnings': []
        }
        
        # Validate required columns
        required_columns = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        missing_cols, found_cols = validate_required_columns(df.columns, required_columns)
        
        if missing_cols:
            result['issues'].append(f"Missing required columns: {', '.join(missing_cols)}")
        
        # Validate data types
        if not result['issues']:  # Only if we have the required columns
            is_valid, type_issues = validate_column_data_types(df)
            if not is_valid:
                result['issues'].extend(type_issues)
        
        # Check for data quality issues
        quality_issues = _check_data_quality(df)
        result['warnings'].extend(quality_issues)
        
        # Add date range info if we have a datetime index
        if isinstance(df.index, pd.DatetimeIndex) and len(df) > 0:
            result['date_range'] = {
                'start': df.index[0].strftime('%Y-%m-%d'),
                'end': df.index[-1].strftime('%Y-%m-%d')
            }
        
        result['valid'] = len(result['issues']) == 0
        
        return result
        
    except pd.errors.EmptyDataError:
        raise CLIError(f"CSV file is empty: {file_path}")
    except pd.errors.ParserError as e:
        raise CLIError(f"Error parsing CSV file: {e}")
    except Exception as e:
        raise CLIError(f"Error reading file: {e}")


def validate_provider_specific_format(
    df: pd.DataFrame,
    provider: str
) -> Tuple[bool, List[str]]:
    """Validate provider-specific data format.
    
    Args:
        df: DataFrame to validate
        provider: Provider name
        
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    if provider == "yahoo":
        # Yahoo-specific columns
        from vortex.infrastructure.providers.yahoo.column_mapping import YahooColumnMapping
        mapping = YahooColumnMapping()
        
        # Check for Yahoo-specific columns
        yahoo_columns = [mapping.ADJ_CLOSE_COLUMN, mapping.DIVIDENDS_COLUMN, mapping.STOCK_SPLITS_COLUMN]
        for col in yahoo_columns:
            if col in df.columns:
                # Validate non-negative values
                if (df[col] < 0).any():
                    issues.append(f"Negative values found in {col}")
                    
    elif provider == "barchart":
        # Barchart-specific validation
        from vortex.infrastructure.providers.barchart.column_mapping import BarchartColumnMapping
        mapping = BarchartColumnMapping()
        
        # Check for open interest column (futures)
        if mapping.OPEN_INTEREST_COLUMN in df.columns:
            if df[mapping.OPEN_INTEREST_COLUMN].isna().all():
                issues.append("Open Interest column is completely empty")
                
    elif provider == "ibkr":
        # IBKR-specific validation
        from vortex.infrastructure.providers.ibkr.column_mapping import IbkrColumnMapping
        mapping = IbkrColumnMapping()
        
        # Check for bar count column
        if mapping.BAR_COUNT_COLUMN in df.columns:
            if (df[mapping.BAR_COUNT_COLUMN] <= 0).any():
                issues.append("Invalid bar count values found")
    
    return len(issues) == 0, issues


def _check_data_quality(df: pd.DataFrame) -> List[str]:
    """Check for data quality issues.
    
    Args:
        df: DataFrame to check
        
    Returns:
        List of warning messages
    """
    warnings = []
    
    # Check for duplicate index values
    if df.index.duplicated().any():
        warnings.append("Duplicate index values found")
    
    # Check for gaps in time series
    if isinstance(df.index, pd.DatetimeIndex) and len(df) > 1:
        # Calculate expected frequency
        freq = pd.infer_freq(df.index)
        if freq:
            expected_periods = pd.date_range(
                start=df.index[0], 
                end=df.index[-1], 
                freq=freq
            )
            missing_periods = len(expected_periods) - len(df)
            if missing_periods > 0:
                warnings.append(f"Missing {missing_periods} periods in time series")
    
    # Check for extreme values
    price_columns = [col for col in [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN] 
                     if col in df.columns]
    
    for col in price_columns:
        if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
            # Check for zeros
            if (df[col] == 0).any():
                warnings.append(f"Zero values found in {col}")
            
            # Check for extreme price changes
            if len(df) > 1:
                pct_change = df[col].pct_change().abs()
                extreme_changes = pct_change[pct_change > 0.5]  # 50% change
                if len(extreme_changes) > 0:
                    warnings.append(f"Extreme price changes (>50%) found in {col}")
    
    # Check OHLC relationships
    if all(col in df.columns for col in [HIGH_COLUMN, LOW_COLUMN]):
        invalid_hl = df[HIGH_COLUMN] < df[LOW_COLUMN]
        if invalid_hl.any():
            warnings.append(f"High < Low found in {invalid_hl.sum()} rows")
    
    if all(col in df.columns for col in [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]):
        # Check if Open/Close within High/Low range
        invalid_open = (df[OPEN_COLUMN] > df[HIGH_COLUMN]) | (df[OPEN_COLUMN] < df[LOW_COLUMN])
        invalid_close = (df[CLOSE_COLUMN] > df[HIGH_COLUMN]) | (df[CLOSE_COLUMN] < df[LOW_COLUMN])
        
        if invalid_open.any():
            warnings.append(f"Open price outside High/Low range in {invalid_open.sum()} rows")
        if invalid_close.any():
            warnings.append(f"Close price outside High/Low range in {invalid_close.sum()} rows")
    
    return warnings


def _format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes >= BYTES_PER_MB:
        return f"{size_bytes / BYTES_PER_MB:.2f} MB"
    elif size_bytes >= BYTES_PER_KB:
        return f"{size_bytes / BYTES_PER_KB:.2f} KB"
    else:
        return f"{size_bytes} bytes"


def get_validation_summary(validation_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get summary of validation results.
    
    Args:
        validation_results: List of individual validation results
        
    Returns:
        Summary dictionary
    """
    total_files = len(validation_results)
    valid_files = sum(1 for r in validation_results if r['valid'])
    total_issues = sum(len(r['issues']) for r in validation_results)
    total_warnings = sum(len(r['warnings']) for r in validation_results)
    
    return {
        'total_files': total_files,
        'valid_files': valid_files,
        'invalid_files': total_files - valid_files,
        'total_issues': total_issues,
        'total_warnings': total_warnings,
        'success_rate': f"{(valid_files / total_files * 100):.1f}%" if total_files > 0 else "N/A"
    }