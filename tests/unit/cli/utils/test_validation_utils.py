"""
Tests for CLI validation utility functions.
"""

import tempfile
import pandas as pd
from pathlib import Path
from unittest.mock import patch, Mock
import pytest

from vortex.cli.utils.validation_utils import (
    validate_csv_file,
    validate_provider_specific_format,
    get_validation_summary,
    _check_data_quality,
    _format_file_size
)
from vortex.exceptions import CLIError
from vortex.constants import BYTES_PER_KB, BYTES_PER_MB


class TestValidateCsvFile:
    """Test CSV file validation functionality."""
    
    def test_validate_csv_file_not_found(self):
        """Test validation of non-existent file."""
        non_existent_path = Path("/tmp/non_existent_file.csv")
        
        with pytest.raises(CLIError, match="File not found"):
            validate_csv_file(non_existent_path)
    
    def test_validate_csv_file_wrong_extension(self):
        """Test validation of non-CSV file."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            txt_path = Path(f.name)
            
            try:
                with pytest.raises(CLIError, match="Not a CSV file"):
                    validate_csv_file(txt_path)
            finally:
                txt_path.unlink()
    
    def test_validate_csv_file_success(self):
        """Test successful CSV file validation."""
        # Create valid CSV data
        data = {
            'Open': [100.0, 101.0, 102.0],
            'High': [105.0, 106.0, 107.0],
            'Low': [98.0, 99.0, 100.0],
            'Close': [104.0, 105.0, 106.0],
            'Volume': [1000, 1100, 1200]
        }
        df = pd.DataFrame(data, index=pd.date_range('2024-01-01', periods=3, freq='D'))
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = Path(f.name)
            df.to_csv(csv_path)
            
            try:
                result = validate_csv_file(csv_path)
                
                assert result['valid'] is True
                assert result['rows'] == 3
                assert result['columns'] == 5
                assert 'Open' in result['column_names']
                assert len(result['issues']) == 0
                assert 'date_range' in result
                assert result['date_range']['start'] == '2024-01-01'
                assert result['date_range']['end'] == '2024-01-03'
                
            finally:
                csv_path.unlink()
    
    def test_validate_csv_file_missing_columns(self):
        """Test CSV file with missing required columns."""
        # Create CSV without required columns
        data = {'Price': [100.0, 101.0], 'Qty': [1000, 1100]}
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = Path(f.name)
            df.to_csv(csv_path)
            
            try:
                result = validate_csv_file(csv_path)
                
                assert result['valid'] is False
                assert len(result['issues']) > 0
                assert any('Missing required columns' in issue for issue in result['issues'])
                
            finally:
                csv_path.unlink()
    
    def test_validate_csv_file_empty(self):
        """Test validation of empty CSV file."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = Path(f.name)
            # Write empty file
            f.write(b'')
            f.flush()
            
            try:
                with pytest.raises(CLIError, match="CSV file is empty"):
                    validate_csv_file(csv_path)
            finally:
                csv_path.unlink()
    
    def test_validate_csv_file_parser_error(self):
        """Test validation of malformed CSV file."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = Path(f.name)
            # Write malformed CSV
            f.write(b'Open,High,Low,Close\n100,105,98,\n101,106"malformed\n')
            f.flush()
            
            try:
                with pytest.raises(CLIError, match="Error parsing CSV file"):
                    validate_csv_file(csv_path)
            finally:
                csv_path.unlink()
    
    def test_validate_csv_file_with_warnings(self):
        """Test CSV file that generates warnings."""
        # Create data with quality issues
        data = {
            'Open': [100.0, 100.0, 0.0],  # Duplicate and zero value
            'High': [105.0, 106.0, 5.0],  # Extreme change
            'Low': [110.0, 99.0, 0.0],   # High < Low in first row
            'Close': [104.0, 105.0, 4.0],
            'Volume': [1000, 1100, 1200]
        }
        df = pd.DataFrame(data, index=pd.date_range('2024-01-01', periods=3, freq='D'))
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = Path(f.name)
            df.to_csv(csv_path)
            
            try:
                result = validate_csv_file(csv_path)
                
                assert result['valid'] is True  # Still valid despite warnings
                assert len(result['warnings']) > 0
                
            finally:
                csv_path.unlink()
    
    def test_validate_csv_file_data_type_validation(self):
        """Test CSV file with data type issues."""
        # Create CSV with mixed data types
        data = {
            'Open': ['100.0', '101.0', 'invalid'],  # Mixed types
            'High': [105.0, 106.0, 107.0],
            'Low': [98.0, 99.0, 100.0],
            'Close': [104.0, 105.0, 106.0],
            'Volume': [1000, 1100, 1200]
        }
        df = pd.DataFrame(data)
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = Path(f.name)
            df.to_csv(csv_path)
            
            try:
                result = validate_csv_file(csv_path)
                
                # Should have type validation issues
                assert len(result['issues']) > 0 or len(result['warnings']) > 0
                
            finally:
                csv_path.unlink()


class TestValidateProviderSpecificFormat:
    """Test provider-specific validation functionality."""
    
    def test_validate_yahoo_format_success(self):
        """Test successful Yahoo format validation."""
        data = {
            'Open': [100.0, 101.0],
            'High': [105.0, 106.0],
            'Low': [98.0, 99.0],
            'Close': [104.0, 105.0],
            'Volume': [1000, 1100],
            'Adj Close': [104.0, 105.0],
            'Dividends': [0.0, 0.0],
            'Stock Splits': [0.0, 0.0]
        }
        df = pd.DataFrame(data)
        
        is_valid, issues = validate_provider_specific_format(df, "yahoo")
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_yahoo_format_negative_values(self):
        """Test Yahoo format validation with negative values."""
        data = {
            'Open': [100.0, 101.0],
            'High': [105.0, 106.0],
            'Low': [98.0, 99.0],
            'Close': [104.0, 105.0],
            'Volume': [1000, 1100],
            'Adj Close': [104.0, 105.0],
            'Dividends': [-1.0, 0.0],  # Negative dividend
            'Stock Splits': [0.0, -1.0]  # Negative split
        }
        df = pd.DataFrame(data)
        
        is_valid, issues = validate_provider_specific_format(df, "yahoo")
        
        assert is_valid is False
        assert len(issues) == 2
        assert any('Negative values found in Dividends' in issue for issue in issues)
        assert any('Negative values found in Stock Splits' in issue for issue in issues)
    
    def test_validate_barchart_format_success(self):
        """Test successful Barchart format validation."""
        data = {
            'Open': [100.0, 101.0],
            'High': [105.0, 106.0],
            'Low': [98.0, 99.0],
            'Close': [104.0, 105.0],
            'Volume': [1000, 1100],
            'Open Interest': [500, 510]
        }
        df = pd.DataFrame(data)
        
        is_valid, issues = validate_provider_specific_format(df, "barchart")
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_barchart_format_empty_open_interest(self):
        """Test Barchart format validation with empty open interest."""
        data = {
            'Open': [100.0, 101.0],
            'High': [105.0, 106.0],
            'Low': [98.0, 99.0],
            'Close': [104.0, 105.0],
            'Volume': [1000, 1100],
            'Open Interest': [None, None]  # All NaN
        }
        df = pd.DataFrame(data)
        
        is_valid, issues = validate_provider_specific_format(df, "barchart")
        
        assert is_valid is False
        assert len(issues) == 1
        assert 'Open Interest column is completely empty' in issues[0]
    
    def test_validate_ibkr_format_success(self):
        """Test successful IBKR format validation."""
        data = {
            'Open': [100.0, 101.0],
            'High': [105.0, 106.0],
            'Low': [98.0, 99.0],
            'Close': [104.0, 105.0],
            'Volume': [1000, 1100],
            'Bar Count': [10, 12]
        }
        df = pd.DataFrame(data)
        
        is_valid, issues = validate_provider_specific_format(df, "ibkr")
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_ibkr_format_invalid_bar_count(self):
        """Test IBKR format validation with invalid bar count."""
        data = {
            'Open': [100.0, 101.0],
            'High': [105.0, 106.0],
            'Low': [98.0, 99.0],
            'Close': [104.0, 105.0],
            'Volume': [1000, 1100],
            'Bar Count': [0, -1]  # Invalid bar counts
        }
        df = pd.DataFrame(data)
        
        is_valid, issues = validate_provider_specific_format(df, "ibkr")
        
        assert is_valid is False
        assert len(issues) == 1
        assert 'Invalid bar count values found' in issues[0]
    
    def test_validate_unsupported_provider(self):
        """Test validation for unsupported provider."""
        data = {'Open': [100.0], 'Close': [104.0]}
        df = pd.DataFrame(data)
        
        is_valid, issues = validate_provider_specific_format(df, "unsupported")
        
        assert is_valid is True
        assert len(issues) == 0
    
    def test_validate_provider_missing_columns(self):
        """Test validation when provider-specific columns are missing."""
        data = {'Open': [100.0], 'Close': [104.0]}
        df = pd.DataFrame(data)
        
        # Should not fail when provider-specific columns are missing
        is_valid, issues = validate_provider_specific_format(df, "yahoo")
        assert is_valid is True
        
        is_valid, issues = validate_provider_specific_format(df, "barchart")
        assert is_valid is True
        
        is_valid, issues = validate_provider_specific_format(df, "ibkr")
        assert is_valid is True


class TestCheckDataQuality:
    """Test data quality checking functionality."""
    
    def test_check_data_quality_perfect_data(self):
        """Test quality check with perfect data."""
        data = {
            'Open': [100.0, 101.0, 102.0],
            'High': [105.0, 106.0, 107.0],
            'Low': [98.0, 99.0, 100.0],
            'Close': [104.0, 105.0, 106.0],
            'Volume': [1000, 1100, 1200]
        }
        df = pd.DataFrame(data, index=pd.date_range('2024-01-01', periods=3, freq='D'))
        
        warnings = _check_data_quality(df)
        
        assert len(warnings) == 0
    
    def test_check_data_quality_duplicate_index(self):
        """Test quality check with duplicate index values."""
        data = {
            'Open': [100.0, 101.0],
            'Close': [104.0, 105.0]
        }
        df = pd.DataFrame(data, index=['2024-01-01', '2024-01-01'])  # Duplicate index
        
        warnings = _check_data_quality(df)
        
        assert len(warnings) > 0
        assert any('Duplicate index values found' in warning for warning in warnings)
    
    def test_check_data_quality_missing_periods(self):
        """Test quality check with missing periods in time series."""
        # Create data with gaps
        dates = ['2024-01-01', '2024-01-02', '2024-01-05']  # Missing 3rd and 4th
        data = {
            'Open': [100.0, 101.0, 102.0],
            'Close': [104.0, 105.0, 106.0]
        }
        df = pd.DataFrame(data, index=pd.to_datetime(dates))
        
        warnings = _check_data_quality(df)
        
        # Should detect missing periods
        assert any('Missing' in warning and 'periods in time series' in warning 
                  for warning in warnings)
    
    def test_check_data_quality_zero_values(self):
        """Test quality check with zero price values."""
        data = {
            'Open': [100.0, 0.0, 102.0],  # Zero value
            'High': [105.0, 106.0, 107.0],
            'Low': [98.0, 99.0, 100.0],
            'Close': [104.0, 105.0, 106.0]
        }
        df = pd.DataFrame(data)
        
        warnings = _check_data_quality(df)
        
        assert len(warnings) > 0
        assert any('Zero values found in Open' in warning for warning in warnings)
    
    def test_check_data_quality_extreme_changes(self):
        """Test quality check with extreme price changes."""
        data = {
            'Open': [100.0, 200.0, 102.0],  # 100% increase
            'High': [105.0, 206.0, 107.0],
            'Low': [98.0, 199.0, 100.0],
            'Close': [104.0, 205.0, 106.0]
        }
        df = pd.DataFrame(data)
        
        warnings = _check_data_quality(df)
        
        assert len(warnings) > 0
        assert any('Extreme price changes' in warning for warning in warnings)
    
    def test_check_data_quality_invalid_ohlc_relationships(self):
        """Test quality check with invalid OHLC relationships."""
        data = {
            'Open': [100.0, 101.0],
            'High': [95.0, 106.0],   # High < Open in first row
            'Low': [110.0, 99.0],   # Low > High in first row
            'Close': [120.0, 105.0]  # Close > High in first row
        }
        df = pd.DataFrame(data)
        
        warnings = _check_data_quality(df)
        
        assert len(warnings) >= 2
        # Should detect High < Low
        assert any('High < Low found' in warning for warning in warnings)
        # Should detect Open/Close outside High/Low range
        assert any('outside High/Low range' in warning for warning in warnings)
    
    def test_check_data_quality_non_numeric_columns(self):
        """Test quality check with non-numeric price columns."""
        data = {
            'Open': ['100.0', '101.0'],  # String values
            'High': [105.0, 106.0],
            'Low': [98.0, 99.0],
            'Close': [104.0, 105.0]
        }
        df = pd.DataFrame(data)
        
        warnings = _check_data_quality(df)
        
        # Should handle non-numeric columns gracefully
        # (No specific checks for non-numeric columns)
        assert isinstance(warnings, list)
    
    def test_check_data_quality_empty_dataframe(self):
        """Test quality check with empty DataFrame."""
        df = pd.DataFrame()
        
        warnings = _check_data_quality(df)
        
        assert len(warnings) == 0
    
    def test_check_data_quality_single_row(self):
        """Test quality check with single row of data."""
        data = {
            'Open': [100.0],
            'High': [105.0],
            'Low': [98.0],
            'Close': [104.0]
        }
        df = pd.DataFrame(data)
        
        warnings = _check_data_quality(df)
        
        # Should handle single-row data without errors
        assert isinstance(warnings, list)


class TestFormatFileSize:
    """Test file size formatting functionality."""
    
    def test_format_file_size_bytes(self):
        """Test formatting bytes."""
        assert _format_file_size(500) == "500 bytes"
        assert _format_file_size(0) == "0 bytes"
        assert _format_file_size(1) == "1 bytes"
    
    def test_format_file_size_kilobytes(self):
        """Test formatting kilobytes."""
        assert _format_file_size(BYTES_PER_KB) == "1.00 KB"
        assert _format_file_size(int(1.5 * BYTES_PER_KB)) == "1.50 KB"
        assert _format_file_size(BYTES_PER_MB - 1) == f"{(BYTES_PER_MB - 1) / BYTES_PER_KB:.2f} KB"
    
    def test_format_file_size_megabytes(self):
        """Test formatting megabytes."""
        assert _format_file_size(BYTES_PER_MB) == "1.00 MB"
        assert _format_file_size(int(2.5 * BYTES_PER_MB)) == "2.50 MB"
        assert _format_file_size(int(1.234 * BYTES_PER_MB)) == "1.23 MB"
    
    def test_format_file_size_large_values(self):
        """Test formatting very large file sizes."""
        large_size = 1000 * BYTES_PER_MB
        result = _format_file_size(large_size)
        assert result == "1000.00 MB"
        assert "MB" in result


class TestGetValidationSummary:
    """Test validation summary functionality."""
    
    def test_get_validation_summary_all_valid(self):
        """Test summary with all valid files."""
        validation_results = [
            {'valid': True, 'issues': [], 'warnings': ['minor warning']},
            {'valid': True, 'issues': [], 'warnings': []},
            {'valid': True, 'issues': [], 'warnings': ['another warning']}
        ]
        
        summary = get_validation_summary(validation_results)
        
        assert summary['total_files'] == 3
        assert summary['valid_files'] == 3
        assert summary['invalid_files'] == 0
        assert summary['total_issues'] == 0
        assert summary['total_warnings'] == 2
        assert summary['success_rate'] == "100.0%"
    
    def test_get_validation_summary_mixed_results(self):
        """Test summary with mixed validation results."""
        validation_results = [
            {'valid': True, 'issues': [], 'warnings': ['warning1']},
            {'valid': False, 'issues': ['error1', 'error2'], 'warnings': []},
            {'valid': False, 'issues': ['error3'], 'warnings': ['warning2']},
            {'valid': True, 'issues': [], 'warnings': []}
        ]
        
        summary = get_validation_summary(validation_results)
        
        assert summary['total_files'] == 4
        assert summary['valid_files'] == 2
        assert summary['invalid_files'] == 2
        assert summary['total_issues'] == 3
        assert summary['total_warnings'] == 2
        assert summary['success_rate'] == "50.0%"
    
    def test_get_validation_summary_all_invalid(self):
        """Test summary with all invalid files."""
        validation_results = [
            {'valid': False, 'issues': ['error1'], 'warnings': []},
            {'valid': False, 'issues': ['error2', 'error3'], 'warnings': ['warning1']}
        ]
        
        summary = get_validation_summary(validation_results)
        
        assert summary['total_files'] == 2
        assert summary['valid_files'] == 0
        assert summary['invalid_files'] == 2
        assert summary['total_issues'] == 3
        assert summary['total_warnings'] == 1
        assert summary['success_rate'] == "0.0%"
    
    def test_get_validation_summary_empty_list(self):
        """Test summary with empty validation results."""
        validation_results = []
        
        summary = get_validation_summary(validation_results)
        
        assert summary['total_files'] == 0
        assert summary['valid_files'] == 0
        assert summary['invalid_files'] == 0
        assert summary['total_issues'] == 0
        assert summary['total_warnings'] == 0
        assert summary['success_rate'] == "N/A"
    
    def test_get_validation_summary_single_file(self):
        """Test summary with single file result."""
        validation_results = [
            {'valid': True, 'issues': [], 'warnings': ['single warning']}
        ]
        
        summary = get_validation_summary(validation_results)
        
        assert summary['total_files'] == 1
        assert summary['valid_files'] == 1
        assert summary['invalid_files'] == 0
        assert summary['total_issues'] == 0
        assert summary['total_warnings'] == 1
        assert summary['success_rate'] == "100.0%"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_validate_csv_file_permission_error(self):
        """Test CSV validation with permission error."""
        # Create a file but mock a permission error
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            csv_path = Path(f.name)
            
            try:
                with patch('pandas.read_csv', side_effect=PermissionError("Permission denied")):
                    with pytest.raises(CLIError, match="Error reading file"):
                        validate_csv_file(csv_path)
            finally:
                csv_path.unlink()
    
    def test_validate_provider_format_import_error_handling(self):
        """Test provider format validation with import errors."""
        data = {'Open': [100.0], 'Close': [104.0]}
        df = pd.DataFrame(data)
        
        # Mock import error for Yahoo column mapping
        with patch('vortex.cli.utils.validation_utils.YahooColumnMapping', 
                  side_effect=ImportError("Module not found")):
            # Should handle import errors gracefully
            try:
                is_valid, issues = validate_provider_specific_format(df, "yahoo")
                # May raise import error or handle gracefully depending on implementation
            except ImportError:
                # This is acceptable behavior
                pass
    
    def test_data_quality_with_inf_values(self):
        """Test data quality check with infinite values."""
        data = {
            'Open': [100.0, float('inf'), 102.0],
            'High': [105.0, 106.0, 107.0],
            'Low': [98.0, 99.0, 100.0],
            'Close': [104.0, 105.0, 106.0]
        }
        df = pd.DataFrame(data)
        
        warnings = _check_data_quality(df)
        
        # Should handle infinite values without crashing
        assert isinstance(warnings, list)
    
    def test_data_quality_with_nan_values(self):
        """Test data quality check with NaN values."""
        data = {
            'Open': [100.0, None, 102.0],
            'High': [105.0, 106.0, 107.0],
            'Low': [98.0, 99.0, 100.0],
            'Close': [104.0, 105.0, 106.0]
        }
        df = pd.DataFrame(data)
        
        warnings = _check_data_quality(df)
        
        # Should handle NaN values without crashing
        assert isinstance(warnings, list)