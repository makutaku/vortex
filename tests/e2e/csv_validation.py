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
    DATETIME_COLUMN_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, 
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
        
        # Row count validation - for Barchart, count only valid datetime rows
        effective_row_count = row_count
        if provider.lower() == 'barchart':
            # Find datetime column and count non-null rows
            for col in columns:
                if col.lower() in ['datetime', 'date', 'time', 'timestamp']:
                    non_null_datetime_count = df[col].notna().sum()
                    effective_row_count = non_null_datetime_count
                    break
        
        if effective_row_count < expected_min_rows:
            if provider.lower() == 'barchart' and effective_row_count != row_count:
                warnings.append(f"Insufficient valid data rows: {effective_row_count} valid (out of {row_count} total) < {expected_min_rows}")
            else:
                errors.append(f"Insufficient data rows: {effective_row_count} < {expected_min_rows}")
        
        if expected_max_rows and effective_row_count > expected_max_rows:
            warnings.append(f"More rows than expected: {effective_row_count} > {expected_max_rows}")
        
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
        
        # Enhanced validation for hourly data - check that datetime column exists and contains proper hourly data
        if has_date_column and 'hourly' in str(file_path).lower() or '1h' in str(file_path).lower():
            date_col = None
            for col in columns:
                if col.lower() in date_columns:
                    date_col = col
                    break
            
            if date_col:
                try:
                    # Parse dates and check for hourly patterns
                    dates = pd.to_datetime(df[date_col], errors='coerce')
                    valid_dates = dates.dropna()
                    
                    if len(valid_dates) > 1:
                        # Check if timestamps have minute precision (hourly data should be on the hour)
                        time_diffs = valid_dates.diff().dropna()
                        if len(time_diffs) > 0:
                            # Check if most intervals are around 1 hour (3600 seconds)
                            hourly_intervals = time_diffs[
                                (time_diffs >= pd.Timedelta(minutes=50)) & 
                                (time_diffs <= pd.Timedelta(minutes=70))
                            ]
                            hourly_ratio = len(hourly_intervals) / len(time_diffs)
                            
                            if hourly_ratio < 0.5:  # Less than 50% hourly intervals
                                warnings.append(f"Hourly data validation: Only {hourly_ratio:.1%} of intervals appear to be hourly")
                            else:
                                # Success case - log for debugging
                                logger.debug(f"Hourly validation passed: {hourly_ratio:.1%} of {len(time_diffs)} intervals are hourly")
                    
                    # Check that we have actual datetime values, not just empty/null
                    valid_datetime_count = len(valid_dates)
                    if valid_datetime_count == 0:
                        errors.append("Hourly data file contains no valid datetime values")
                    elif valid_datetime_count < effective_row_count * 0.8:
                        warnings.append(f"Many datetime values missing in hourly data: {valid_datetime_count}/{effective_row_count} valid")
                        
                except Exception as e:
                    warnings.append(f"Hourly data datetime validation failed: {e}")
        
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
        
        # Check for null values with provider-specific tolerance
        null_counts = df.isnull().sum()
        total_nulls = null_counts.sum()
        if total_nulls > 0:
            null_columns = null_counts[null_counts > 0].to_dict()
            
            # Special handling for datetime column nulls in Barchart data
            datetime_null_count = 0
            datetime_col_name = None
            for col in columns:
                if col.lower() in ['datetime', 'date', 'time', 'timestamp']:
                    datetime_col_name = col
                    datetime_null_count = null_counts.get(col, 0)
                    break
            
            # Adjust null tolerance based on provider and data characteristics
            if provider.lower() == 'barchart':
                # Special handling for intraday data: %Chg column often has many nulls
                if 'hourly' in str(file_path).lower() or '1h' in str(file_path).lower():
                    # For intraday/hourly Barchart data, exclude %Chg nulls from strict validation
                    chg_columns = [col for col in columns if '%chg' in col.lower() or 'chg' in col.lower()]
                    if chg_columns:
                        chg_nulls = sum(null_counts.get(col, 0) for col in chg_columns)
                        non_chg_nulls = total_nulls - chg_nulls - datetime_null_count
                        
                        if chg_nulls > row_count * 0.8:  # Most %Chg values are null - this is normal for intraday
                            warnings.append(f"Many null %Chg values in intraday data: {chg_nulls}/{row_count} (normal for minute-level data)")
                            # Use non-%Chg nulls for validation
                            if non_chg_nulls > row_count * 0.1:  # 10% tolerance for non-%Chg columns
                                errors.append(f"High null values in non-%Chg columns: {non_chg_nulls} nulls")
                            elif non_chg_nulls > 0:
                                warnings.append(f"Some null values in non-%Chg columns: {non_chg_nulls} nulls")
                        else:
                            # Normal validation if %Chg isn't mostly null
                            if total_nulls > row_count * 0.1:
                                errors.append(f"High null value count: {total_nulls} nulls in {null_columns}")
                            else:
                                warnings.append(f"Some null values found: {null_columns}")
                elif datetime_null_count > 0:
                    # For Barchart, if most nulls are in datetime column, this might be trailing empty rows
                    if datetime_null_count > row_count * 0.8:  # More than 80% of rows have null datetime
                        warnings.append(f"Many null datetime values (possibly trailing empty rows): {datetime_null_count}/{row_count} in {datetime_col_name}")
                    elif datetime_null_count > row_count * 0.3:  # 30-80% null datetimes
                        warnings.append(f"Moderate null datetime values: {datetime_null_count}/{row_count} in {datetime_col_name}")
                    else:
                        warnings.append(f"Some null datetime values: {datetime_null_count}/{row_count} in {datetime_col_name}")
                    
                    # Calculate expected nulls in other columns if they align with datetime nulls (trailing empty rows)
                    # Count nulls in data columns that correspond to rows with null datetimes
                    datetime_null_mask = df[datetime_col_name].isna()
                    aligned_nulls = 0
                    for col in columns:
                        if col.lower() not in ['datetime', 'date', 'time', 'timestamp']:
                            # Count nulls in this column that align with datetime nulls
                            col_nulls_in_datetime_null_rows = (df[col].isna() & datetime_null_mask).sum()
                            aligned_nulls += col_nulls_in_datetime_null_rows
                    
                    # Calculate non-aligned nulls (nulls in data columns where datetime is not null)
                    non_aligned_nulls = total_nulls - datetime_null_count - aligned_nulls
                    
                    if non_aligned_nulls > effective_row_count * 0.1:  # 10% tolerance for actual data rows
                        errors.append(f"High null values in data rows: {non_aligned_nulls} nulls in non-empty rows")
                    elif aligned_nulls > 0:
                        warnings.append(f"Null values in trailing empty rows: {aligned_nulls} nulls aligned with datetime nulls")
                else:
                    # No datetime nulls, so apply standard null tolerance to all columns
                    if total_nulls > row_count * 0.1:  # 10% tolerance for Barchart data rows
                        errors.append(f"High null value count: {total_nulls} nulls in {null_columns}")
                    else:
                        warnings.append(f"Some null values found: {null_columns}")
            else:
                # Default behavior for other providers
                null_tolerance = 0.1  # Default 10%
                if total_nulls > row_count * null_tolerance:
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
        
        # Return effective row count for better reporting
        reported_row_count = effective_row_count if provider.lower() == 'barchart' and 'effective_row_count' in locals() else row_count
        
        return CSVValidationResult(file_path, is_valid, reported_row_count, columns, errors, warnings)
        
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


def validate_hourly_datetime_structure(file_path: Path) -> Tuple[bool, List[str], List[str]]:
    """
    Specifically validate that hourly data has proper datetime structure.
    
    Args:
        file_path: Path to hourly CSV file
        
    Returns:
        Tuple of (is_valid, errors, info_messages)
    """
    errors = []
    info_messages = []
    
    try:
        if not file_path.exists():
            errors.append(f"File does not exist: {file_path}")
            return False, errors, info_messages
        
        # Read CSV
        df = pd.read_csv(file_path)
        
        if df.empty:
            errors.append("CSV file is empty")
            return False, errors, info_messages
        
        columns = list(df.columns)
        columns_lower = [col.lower() for col in columns]
        
        # Check for datetime column
        date_columns = ['datetime', 'date', 'time', 'timestamp']
        datetime_col = None
        for col in columns:
            if col.lower() in date_columns:
                datetime_col = col
                break
        
        if not datetime_col:
            errors.append(f"No datetime column found. Columns: {columns}")
            return False, errors, info_messages
        
        info_messages.append(f"Found datetime column: '{datetime_col}'")
        
        # Check if datetime column has actual values
        datetime_values = df[datetime_col]
        non_null_count = datetime_values.notna().sum()
        total_count = len(datetime_values)
        
        if non_null_count == 0:
            errors.append("Datetime column contains no valid values")
            return False, errors, info_messages
        
        if non_null_count < total_count:
            info_messages.append(f"Datetime column: {non_null_count}/{total_count} non-null values")
        else:
            info_messages.append(f"Datetime column: All {total_count} values are non-null")
        
        # Parse datetime values
        try:
            parsed_datetimes = pd.to_datetime(datetime_values, errors='coerce')
            valid_datetimes = parsed_datetimes.dropna()
            
            if len(valid_datetimes) == 0:
                errors.append("No parseable datetime values found")
                return False, errors, info_messages
            
            info_messages.append(f"Parsed {len(valid_datetimes)} valid datetime values")
            info_messages.append(f"Date range: {valid_datetimes.min()} to {valid_datetimes.max()}")
            
            # Check for hourly patterns if we have multiple values
            if len(valid_datetimes) > 1:
                time_diffs = valid_datetimes.diff().dropna()
                
                # Count intervals that are approximately 1 hour
                hourly_intervals = time_diffs[
                    (time_diffs >= pd.Timedelta(minutes=50)) & 
                    (time_diffs <= pd.Timedelta(minutes=70))
                ]
                minute_intervals = time_diffs[
                    (time_diffs >= pd.Timedelta(seconds=50)) & 
                    (time_diffs <= pd.Timedelta(seconds=70))
                ]
                
                total_intervals = len(time_diffs)
                hourly_count = len(hourly_intervals)
                minute_count = len(minute_intervals)
                
                info_messages.append(f"Time intervals: {hourly_count}/{total_intervals} appear hourly, {minute_count}/{total_intervals} appear minute-level")
                
                if minute_count > hourly_count:
                    errors.append(f"Data appears to be minute-level ({minute_count} minute intervals) rather than hourly ({hourly_count} hourly intervals)")
                    return False, errors, info_messages
                elif hourly_count > 0:
                    info_messages.append(f"✅ Data appears to be properly hourly: {hourly_count}/{total_intervals} intervals are ~1 hour")
                else:
                    info_messages.append("⚠️ No clear hourly pattern detected in time intervals")
            
        except Exception as e:
            errors.append(f"Failed to parse datetime values: {e}")
            return False, errors, info_messages
        
        return True, errors, info_messages
        
    except Exception as e:
        errors.append(f"Validation failed: {e}")
        return False, errors, info_messages


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