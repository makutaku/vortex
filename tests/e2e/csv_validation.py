"""
Comprehensive CSV validation utilities for E2E tests.

Provides standardized validation for downloaded market data CSV files
to ensure data quality and completeness across all providers.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

from vortex.models.columns import (
    DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, 
    CLOSE_COLUMN, VOLUME_COLUMN
)

logger = logging.getLogger(__name__)


class CSVValidationResult:
    """Results from CSV validation with detailed metrics."""
    
    def __init__(self, file_path: Path, is_valid: bool, row_count: int, 
                 columns: List[str], errors: List[str], warnings: List[str]):
        self.file_path = file_path
        self.is_valid = is_valid
        self.row_count = row_count
        self.columns = columns
        self.errors = errors
        self.warnings = warnings
        self.file_size = file_path.stat().st_size if file_path.exists() else 0
        
    def __str__(self):
        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        return (f"{status}: {self.file_path.name} - {self.row_count} rows, "
                f"{len(self.columns)} columns, {self.file_size} bytes")


def validate_market_data_csv(
    file_path: Path,
    expected_min_rows: int = 1,
    expected_max_rows: Optional[int] = None,
    required_columns: Optional[List[str]] = None,
    date_range: Optional[Tuple[datetime, datetime]] = None,
    provider: str = "unknown"
) -> CSVValidationResult:
    """
    Comprehensive validation of market data CSV files.
    
    Args:
        file_path: Path to CSV file
        expected_min_rows: Minimum expected data rows (excluding header)
        expected_max_rows: Maximum expected data rows (None = no limit)
        required_columns: List of required column names (None = use defaults)
        date_range: Tuple of (start_date, end_date) for date validation
        provider: Provider name for provider-specific validation
        
    Returns:
        CSVValidationResult with validation details
    """
    errors = []
    warnings = []
    row_count = 0
    columns = []
    
    try:
        # File existence check
        if not file_path.exists():
            errors.append(f"CSV file does not exist: {file_path}")
            return CSVValidationResult(file_path, False, 0, [], errors, warnings)
        
        # File size check
        file_size = file_path.stat().st_size
        if file_size < 50:  # Very small files are likely empty or corrupt
            errors.append(f"CSV file too small: {file_size} bytes")
            return CSVValidationResult(file_path, False, 0, [], errors, warnings)
        
        # Read and parse CSV
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            errors.append(f"Failed to parse CSV: {e}")
            return CSVValidationResult(file_path, False, 0, [], errors, warnings)
        
        # Basic structure validation
        row_count = len(df)
        columns = list(df.columns)
        
        if row_count == 0:
            errors.append("CSV file contains no data rows")
            return CSVValidationResult(file_path, False, 0, columns, errors, warnings)
        
        # Row count validation
        if row_count < expected_min_rows:
            errors.append(f"Insufficient data rows: {row_count} < {expected_min_rows}")
        
        if expected_max_rows and row_count > expected_max_rows:
            warnings.append(f"More rows than expected: {row_count} > {expected_max_rows}")
        
        # Column validation
        if required_columns is None:
            # Use standard OHLCV columns for market data
            required_columns = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        
        # Normalize column names for comparison (case-insensitive)
        columns_lower = [col.lower() for col in columns]
        
        # Check for date/datetime column
        date_columns = ['datetime', 'date', 'time', 'timestamp']
        has_date_column = any(col in columns_lower for col in date_columns)
        
        if not has_date_column:
            errors.append(f"Missing date/datetime column. Found columns: {columns}")
        
        # Check for required market data columns
        for required_col in required_columns:
            if required_col.lower() not in columns_lower:
                errors.append(f"Missing required column: {required_col}")
        
        # Data quality validation
        numeric_columns = [col for col in columns 
                          if col.lower() in ['open', 'high', 'low', 'close', 'volume', 'price']]
        
        for col in numeric_columns:
            try:
                # Check if column can be converted to numeric
                pd.to_numeric(df[col].astype(str).str.replace('%', '').str.replace(',', ''), 
                            errors='coerce')
            except Exception:
                warnings.append(f"Column '{col}' may contain non-numeric data")
        
        # Check for null values
        null_counts = df.isnull().sum()
        total_nulls = null_counts.sum()
        if total_nulls > 0:
            null_columns = null_counts[null_counts > 0].to_dict()
            if total_nulls > row_count * 0.1:  # More than 10% nulls is concerning
                errors.append(f"High null value count: {total_nulls} nulls in {null_columns}")
            else:
                warnings.append(f"Some null values found: {null_columns}")
        
        # Date range validation
        if date_range and has_date_column:
            try:
                # Find the date column
                date_col = None
                for col in columns:
                    if col.lower() in ['datetime', 'date', 'time', 'timestamp']:
                        date_col = col
                        break
                
                if date_col:
                    # Try to parse dates
                    dates = pd.to_datetime(df[date_col], errors='coerce')
                    valid_dates = dates.dropna()
                    
                    if len(valid_dates) > 0:
                        min_date = valid_dates.min()
                        max_date = valid_dates.max()
                        
                        start_date, end_date = date_range
                        
                        # Convert to timezone-naive dates for comparison
                        if hasattr(min_date, 'tz') and min_date.tz is not None:
                            min_date = min_date.tz_convert('UTC').replace(tzinfo=None)
                            max_date = max_date.tz_convert('UTC').replace(tzinfo=None)
                        
                        # Convert start/end dates to timezone-naive if needed
                        if hasattr(start_date, 'tz') and start_date.tz is not None:
                            start_date = start_date.replace(tzinfo=None)
                        if hasattr(end_date, 'tz') and end_date.tz is not None:
                            end_date = end_date.replace(tzinfo=None)
                        
                        # Extract just the date part for comparison
                        min_date_only = min_date.date() if hasattr(min_date, 'date') else min_date
                        max_date_only = max_date.date() if hasattr(max_date, 'date') else max_date
                        start_date_only = start_date.date() if hasattr(start_date, 'date') else start_date
                        end_date_only = end_date.date() if hasattr(end_date, 'date') else end_date
                        
                        # Allow some flexibility (data might not be available for exact range)
                        if max_date_only < start_date_only - timedelta(days=30):
                            warnings.append(f"Data range older than expected: {max_date_only} < {start_date_only}")
                        elif min_date_only > end_date_only + timedelta(days=7):
                            warnings.append(f"Data range newer than expected: {min_date_only} > {end_date_only}")
                    else:
                        warnings.append("No valid dates found in date column")
                        
            except Exception as e:
                warnings.append(f"Date range validation failed: {e}")
        
        # Provider-specific validation
        if provider.lower() == 'yahoo':
            # Yahoo-specific validation
            if 'adj close' not in columns_lower:
                warnings.append("Yahoo CSV missing 'Adj Close' column")
                
        elif provider.lower() == 'barchart':
            # Barchart-specific validation  
            if '%chg' not in columns_lower and 'change' not in columns_lower:
                warnings.append("Barchart CSV missing change/percentage columns")
        
        # Price reasonableness check (for major stocks)
        if 'close' in columns_lower:
            try:
                close_col = next(col for col in columns if col.lower() == 'close')
                close_prices = pd.to_numeric(df[close_col].astype(str).str.replace('%', ''), 
                                           errors='coerce')
                valid_prices = close_prices.dropna()
                
                if len(valid_prices) > 0:
                    avg_price = valid_prices.mean()
                    if avg_price < 0.01:
                        errors.append(f"Unreasonably low prices: average ${avg_price:.4f}")
                    elif avg_price > 10000:
                        warnings.append(f"Very high prices detected: average ${avg_price:.2f}")
            except Exception:
                pass  # Price validation is nice-to-have
        
        # Determine if validation passed
        is_valid = len(errors) == 0
        
        return CSVValidationResult(file_path, is_valid, row_count, columns, errors, warnings)
        
    except Exception as e:
        errors.append(f"Validation failed with exception: {e}")
        return CSVValidationResult(file_path, False, row_count, columns, errors, warnings)


def validate_business_day_count(
    start_date: datetime, 
    end_date: datetime, 
    actual_rows: int,
    tolerance: int = 2
) -> Tuple[bool, int, str]:
    """
    Validate that the number of data rows matches expected business days.
    
    Args:
        start_date: Start of date range
        end_date: End of date range  
        actual_rows: Actual number of data rows received
        tolerance: Allowed difference in row count
        
    Returns:
        Tuple of (is_valid, expected_business_days, message)
    """
    # Calculate expected business days
    current_date = start_date.date()
    end_date_date = end_date.date()
    business_days = 0
    
    while current_date <= end_date_date:
        if current_date.weekday() < 5:  # Monday=0, Friday=4
            business_days += 1
        current_date += timedelta(days=1)
    
    # Check if actual rows are within tolerance
    diff = abs(actual_rows - business_days)
    is_valid = diff <= tolerance
    
    if is_valid:
        message = f"Row count reasonable: {actual_rows} rows for ~{business_days} business days"
    else:
        message = f"Row count mismatch: {actual_rows} rows, expected ~{business_days} business days (diff: {diff})"
    
    return is_valid, business_days, message


def validate_multiple_csvs(
    csv_files: List[Path],
    expected_min_rows: int = 1,
    date_range: Optional[Tuple[datetime, datetime]] = None,
    provider: str = "unknown"
) -> Dict[str, CSVValidationResult]:
    """
    Validate multiple CSV files and return results.
    
    Args:
        csv_files: List of CSV file paths
        expected_min_rows: Minimum expected rows per file
        date_range: Expected date range
        provider: Provider name
        
    Returns:
        Dictionary mapping filename to validation result
    """
    results = {}
    
    for csv_file in csv_files:
        result = validate_market_data_csv(
            csv_file, 
            expected_min_rows=expected_min_rows,
            date_range=date_range,
            provider=provider
        )
        results[csv_file.name] = result
    
    return results


def print_validation_summary(results: Dict[str, CSVValidationResult]) -> None:
    """Print a summary of validation results."""
    valid_count = sum(1 for result in results.values() if result.is_valid)
    total_count = len(results)
    
    print(f"\n📊 CSV Validation Summary: {valid_count}/{total_count} files valid")
    
    for filename, result in results.items():
        print(f"  {result}")
        
        if result.errors:
            for error in result.errors:
                print(f"    ❌ {error}")
                
        if result.warnings:
            for warning in result.warnings:
                print(f"    ⚠️ {warning}")
    
    if valid_count == total_count:
        print("✅ All CSV files passed validation!")
    elif valid_count > 0:
        print(f"⚠️ {total_count - valid_count} files failed validation")
    else:
        print("❌ No files passed validation")