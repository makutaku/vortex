#!/usr/bin/env python3
"""
CSV Column Validation Helper for Docker Tests

This script provides column validation functionality for Docker test scripts,
using the centralized column constants from the main codebase.
"""

import sys
import csv
import argparse
from pathlib import Path

# Add the src directory to Python path to import vortex modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

try:
    from vortex.models.columns import (
        DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, 
        CLOSE_COLUMN, VOLUME_COLUMN, REQUIRED_PRICE_COLUMNS
    )
except ImportError as e:
    print(f"Error importing vortex modules: {e}")
    print("This script must be run from the project root or with proper PYTHONPATH")
    sys.exit(1)


def validate_csv_columns(csv_file_path, check_data_rows=True):
    """
    Validate that a CSV file contains the required OHLCV columns.
    
    Args:
        csv_file_path: Path to the CSV file to validate
        check_data_rows: Whether to check for actual data rows (default: True)
    
    Returns:
        tuple: (is_valid: bool, message: str, data_row_count: int)
    """
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as f:
            # Read the header
            csv_reader = csv.reader(f)
            try:
                header = next(csv_reader)
            except StopIteration:
                return False, "CSV file is empty", 0
            
            # Convert header to lowercase for case-insensitive matching
            header_lower = [col.lower().strip() for col in header]
            
            # Check for required columns (case-insensitive)
            required_columns = [
                DATE_TIME_COLUMN.lower(),
                OPEN_COLUMN.lower(), 
                HIGH_COLUMN.lower(),
                LOW_COLUMN.lower(),
                CLOSE_COLUMN.lower(),
                VOLUME_COLUMN.lower()
            ]
            
            # Also accept 'date' as it's common in CSV output
            date_found = any(col in header_lower for col in ['datetime', 'date'])
            ohlcv_found = all(col in header_lower for col in required_columns[1:])  # Skip datetime, check separately
            
            if not date_found:
                return False, "Missing date/datetime column", 0
                
            if not ohlcv_found:
                missing_cols = [col for col in required_columns[1:] if col not in header_lower]
                return False, f"Missing required columns: {missing_cols}", 0
            
            # Count data rows if requested
            data_row_count = 0
            if check_data_rows:
                for _ in csv_reader:
                    data_row_count += 1
            
            return True, f"Valid CSV with required columns ({data_row_count} data rows)", data_row_count
            
    except FileNotFoundError:
        return False, f"CSV file not found: {csv_file_path}", 0
    except Exception as e:
        return False, f"Error reading CSV file: {e}", 0


def main():
    """Main entry point for command-line usage."""
    parser = argparse.ArgumentParser(
        description="Validate CSV files have required OHLCV columns using centralized constants"
    )
    parser.add_argument('csv_file', help='Path to CSV file to validate')
    parser.add_argument('--no-data-check', action='store_true', 
                        help='Skip checking for data rows (only validate header)')
    parser.add_argument('--quiet', action='store_true', 
                        help='Only output result (true/false), no descriptive messages')
    
    args = parser.parse_args()
    
    is_valid, message, data_row_count = validate_csv_columns(
        args.csv_file, 
        check_data_rows=not args.no_data_check
    )
    
    if args.quiet:
        print("true" if is_valid else "false")
    else:
        print(f"{'VALID' if is_valid else 'INVALID'}: {message}")
    
    # Return appropriate exit code
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()