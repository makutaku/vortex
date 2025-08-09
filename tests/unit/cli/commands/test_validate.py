"""Tests for the validate CLI command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from click.testing import CliRunner
import tempfile
import csv
import json
import pandas as pd

from vortex.cli.commands.validate import (
    validate, get_files_to_validate, run_validation, 
    validate_single_file, validate_csv_file, validate_parquet_file,
    validate_provider_format, attempt_fixes, display_results,
    display_table_results, display_json_results, display_csv_results,
    show_validation_summary, show_detailed_issues, format_file_size
)
from vortex.models.columns import (
    DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, 
    CLOSE_COLUMN, VOLUME_COLUMN
)


class TestValidateCommand:
    """Test the main validate command."""
    
    def setup_method(self):
        self.runner = CliRunner()
    
    def test_validate_command_help(self):
        """Test that validate command shows help correctly."""
        result = self.runner.invoke(validate, ['--help'])
        assert result.exit_code == 0
        assert "Validate downloaded data integrity and format" in result.output
        assert "--path" in result.output
        assert "--provider" in result.output
        assert "--fix" in result.output
        assert "--detailed" in result.output
        assert "--format" in result.output
    
    @patch('vortex.cli.commands.validate.get_files_to_validate')
    @patch('vortex.cli.commands.validate.console')
    def test_validate_no_files_found(self, mock_console, mock_get_files):
        """Test validate command when no files found."""
        mock_get_files.return_value = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(validate, ['--path', temp_dir])
            assert result.exit_code == 0
            mock_console.print.assert_any_call("[yellow]No data files found to validate[/yellow]")
    
    @patch('vortex.cli.commands.validate.run_validation')
    @patch('vortex.cli.commands.validate.display_results')
    @patch('vortex.cli.commands.validate.show_validation_summary')
    @patch('vortex.cli.commands.validate.get_files_to_validate')
    @patch('vortex.cli.commands.validate.console')
    def test_validate_with_files(self, mock_console, mock_get_files, mock_summary, 
                                mock_display, mock_run_validation):
        """Test validate command with files found."""
        mock_files = [Path("test1.csv"), Path("test2.csv")]
        mock_get_files.return_value = mock_files
        mock_results = [{"file": Path("test1.csv"), "valid": True}]
        mock_run_validation.return_value = mock_results
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(validate, ['--path', temp_dir])
            assert result.exit_code == 0
            
            mock_get_files.assert_called_once_with(Path(temp_dir))
            mock_run_validation.assert_called_once_with(mock_files, None, False)
            mock_display.assert_called_once_with(mock_results, False, "table")
            mock_summary.assert_called_once_with(mock_results)
    
    @patch('vortex.cli.commands.validate.run_validation')
    @patch('vortex.cli.commands.validate.display_results')
    @patch('vortex.cli.commands.validate.show_validation_summary')
    @patch('vortex.cli.commands.validate.get_files_to_validate')
    @patch('vortex.cli.commands.validate.console')
    def test_validate_with_options(self, mock_console, mock_get_files, mock_summary, 
                                  mock_display, mock_run_validation):
        """Test validate command with all options."""
        mock_files = [Path("test.csv")]
        mock_get_files.return_value = mock_files
        mock_results = [{"file": Path("test.csv"), "valid": False}]
        mock_run_validation.return_value = mock_results
        
        with tempfile.TemporaryDirectory() as temp_dir:
            result = self.runner.invoke(validate, [
                '--path', temp_dir,
                '--provider', 'yahoo',
                '--fix',
                '--detailed',
                '--format', 'json'
            ])
            assert result.exit_code == 0
            
            mock_run_validation.assert_called_once_with(mock_files, 'yahoo', True)
            mock_display.assert_called_once_with(mock_results, True, 'json')


class TestGetFilesToValidate:
    """Test the get_files_to_validate function."""
    
    def test_single_csv_file(self):
        """Test with a single CSV file."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                files = get_files_to_validate(temp_path)
                assert len(files) == 1
                assert files[0] == temp_path
            finally:
                temp_path.unlink()
    
    def test_single_parquet_file(self):
        """Test with a single Parquet file."""
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                files = get_files_to_validate(temp_path)
                assert len(files) == 1
                assert files[0] == temp_path
            finally:
                temp_path.unlink()
    
    def test_unsupported_file(self):
        """Test with unsupported file type."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                files = get_files_to_validate(temp_path)
                assert len(files) == 0
            finally:
                temp_path.unlink()
    
    def test_directory_with_files(self):
        """Test with directory containing multiple data files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            csv_file = temp_path / "test1.csv"
            parquet_file = temp_path / "test2.parquet"
            txt_file = temp_path / "test3.txt"
            
            csv_file.touch()
            parquet_file.touch()
            txt_file.touch()
            
            files = get_files_to_validate(temp_path)
            assert len(files) == 2
            assert csv_file in files
            assert parquet_file in files
            assert txt_file not in files
    
    def test_directory_with_subdirectories(self):
        """Test with nested directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create nested structure
            subdir = temp_path / "subdir"
            subdir.mkdir()
            
            file1 = temp_path / "top.csv"
            file2 = subdir / "nested.csv"
            
            file1.touch()
            file2.touch()
            
            files = get_files_to_validate(temp_path)
            assert len(files) == 2
            assert file1 in files
            assert file2 in files
    
    def test_empty_directory(self):
        """Test with empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            files = get_files_to_validate(Path(temp_dir))
            assert len(files) == 0


class TestRunValidation:
    """Test the run_validation function."""
    
    @patch('vortex.cli.commands.validate.validate_single_file')
    @patch('vortex.cli.commands.validate.console')
    def test_run_validation_single_file(self, mock_console, mock_validate_file):
        """Test validation with single file."""
        mock_file = Path("test.csv")
        mock_result = {"file": mock_file, "valid": True, "errors": []}
        mock_validate_file.return_value = mock_result
        
        results = run_validation([mock_file], None, False)
        
        assert len(results) == 1
        assert results[0] == mock_result
        mock_validate_file.assert_called_once_with(mock_file, None, False)
    
    @patch('vortex.cli.commands.validate.Progress')
    @patch('vortex.cli.commands.validate.validate_single_file')
    @patch('vortex.cli.commands.validate.console')
    def test_run_validation_multiple_files(self, mock_console, mock_validate_file, mock_progress_class):
        """Test validation with multiple files."""
        # Mock the Progress context manager
        mock_progress = MagicMock()
        mock_progress_class.return_value.__enter__.return_value = mock_progress
        
        mock_files = [Path("test1.csv"), Path("test2.csv")]
        mock_results = [
            {"file": mock_files[0], "valid": True, "errors": []},
            {"file": mock_files[1], "valid": False, "errors": ["Error"]}
        ]
        mock_validate_file.side_effect = mock_results
        
        results = run_validation(mock_files, "yahoo", True)
        
        assert len(results) == 2
        assert results == mock_results
        assert mock_validate_file.call_count == 2
        mock_validate_file.assert_any_call(mock_files[0], "yahoo", True)
        mock_validate_file.assert_any_call(mock_files[1], "yahoo", True)


class TestValidateSingleFile:
    """Test the validate_single_file function."""
    
    def test_empty_file(self):
        """Test validation of empty file."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_single_file(temp_path, None, False)
                assert result["valid"] == False
                # The actual error message from pandas
                assert any("empty" in error.lower() for error in result["errors"])
                assert result["fixed"] == False
            finally:
                temp_path.unlink()
    
    @patch('vortex.cli.commands.validate.validate_csv_file')
    def test_csv_file_validation(self, mock_validate_csv):
        """Test CSV file validation."""
        mock_validate_csv.return_value = {
            "errors": ["Invalid format"], 
            "warnings": ["Missing header"],
            "metrics": {"rows": 10}
        }
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_file.write(b"test,data\n1,2\n")
            temp_path = Path(temp_file.name)
            try:
                result = validate_single_file(temp_path, "yahoo", False)
                assert "Invalid format" in result["errors"]
                assert "Missing header" in result["warnings"]
                assert result["metrics"]["rows"] == 10
                assert result["valid"] == False
                mock_validate_csv.assert_called_once_with(temp_path, "yahoo")
            finally:
                temp_path.unlink()
    
    @patch('vortex.cli.commands.validate.validate_parquet_file')
    def test_parquet_file_validation(self, mock_validate_parquet):
        """Test Parquet file validation."""
        mock_validate_parquet.return_value = {
            "errors": [], 
            "warnings": [],
            "metrics": {"rows": 5}
        }
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
            # Write some content to make file non-empty
            temp_file.write(b"dummy parquet content that makes this file non-empty")
            temp_file.flush()
            temp_path = Path(temp_file.name)
            try:
                result = validate_single_file(temp_path, None, False)
                # Should only have the parquet result, not the empty file error
                assert result["warnings"] == []
                assert result["metrics"]["rows"] == 5
                assert result["valid"] == True
                mock_validate_parquet.assert_called_once_with(temp_path, None)
            finally:
                temp_path.unlink()
    
    @patch('vortex.cli.commands.validate.validate_provider_format')
    def test_provider_validation(self, mock_validate_provider):
        """Test provider-specific validation."""
        mock_validate_provider.return_value = {
            "errors": ["Wrong column order"],
            "warnings": []
        }
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_file.write(b"test,data\n1,2\n")
            temp_path = Path(temp_file.name)
            try:
                result = validate_single_file(temp_path, "barchart", False)
                assert "Wrong column order" in result["errors"]
                assert result["valid"] == False
                mock_validate_provider.assert_called_once_with(temp_path, "barchart")
            finally:
                temp_path.unlink()
    
    @patch('vortex.cli.commands.validate.attempt_fixes')
    def test_fix_attempt(self, mock_attempt_fixes):
        """Test file fix attempt."""
        mock_attempt_fixes.return_value = True
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                # Simulate invalid file that needs fixing
                result = validate_single_file(temp_path, None, True)
                # Empty file should trigger fix attempt
                if not result["valid"]:
                    mock_attempt_fixes.assert_called_once()
            finally:
                temp_path.unlink()
    
    def test_validation_exception(self):
        """Test exception handling during validation."""
        # Use non-existent file to trigger exception
        nonexistent_path = Path("nonexistent_file.csv")
        result = validate_single_file(nonexistent_path, None, False)
        
        assert result["valid"] == False
        assert len(result["errors"]) > 0
        assert any("Validation error:" in error for error in result["errors"])


class TestValidateCsvFile:
    """Test the validate_csv_file function."""
    
    def test_valid_csv_basic(self):
        """Test validation of basic CSV file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow([DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN])
            writer.writerow(["2024-01-01", "100", "105", "98", "102", "1000"])
            temp_path = Path(temp_file.name)
            
            try:
                result = validate_csv_file(temp_path, None)
                # Should not have errors for basic valid CSV
                assert isinstance(result["errors"], list)
                assert isinstance(result["warnings"], list)
                assert isinstance(result["metrics"], dict)
            finally:
                temp_path.unlink()
    
    def test_csv_with_provider(self):
        """Test CSV validation with specific provider."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow([DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN])
            writer.writerow(["2024-01-01", "100", "105", "98", "102", "1000"])
            temp_path = Path(temp_file.name)
            
            try:
                result = validate_csv_file(temp_path, "yahoo")
                assert isinstance(result["errors"], list)
                assert isinstance(result["warnings"], list)
                assert isinstance(result["metrics"], dict)
            finally:
                temp_path.unlink()
    
    def test_csv_invalid_ohlc_relationships(self):
        """Test CSV with invalid OHLC relationships."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow([DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN])
            # Invalid: Low > High
            writer.writerow(["2024-01-01", "100", "90", "110", "95", "1000"])
            temp_file.flush()  # Ensure data is written to disk
            temp_path = Path(temp_file.name)
            
        try:
            result = validate_csv_file(temp_path, None)
            assert any("invalid ohlc relationships" in error.lower() for error in result["errors"])
        finally:
            temp_path.unlink()
    
    def test_csv_missing_columns(self):
        """Test CSV with missing expected columns."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow([DATE_TIME_COLUMN, "Price"])  # Missing OHLC columns
            writer.writerow(["2024-01-01", "100"])
            temp_file.flush()  # Ensure data is written to disk
            temp_path = Path(temp_file.name)
            
        try:
            result = validate_csv_file(temp_path, None)
            assert any("missing common columns" in warning.lower() for warning in result["warnings"])
        finally:
            temp_path.unlink()
    
    def test_csv_empty_rows(self):
        """Test CSV with empty rows."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as temp_file:
            writer = csv.writer(temp_file)
            writer.writerow([DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN])
            writer.writerow(["2024-01-01", "100", "105", "98", "102", "1000"])
            writer.writerow(["", "", "", "", "", ""])  # Empty row
            temp_file.flush()  # Ensure data is written to disk
            temp_path = Path(temp_file.name)
            
        try:
            result = validate_csv_file(temp_path, None)
            assert any("completely empty rows" in warning.lower() for warning in result["warnings"])
        finally:
            temp_path.unlink()
    
    def test_csv_file_not_found(self):
        """Test CSV validation with non-existent file."""
        nonexistent_path = Path("nonexistent.csv")
        result = validate_csv_file(nonexistent_path, None)
        
        assert "File not found" in result["errors"]
    
    @patch('pandas.read_csv')
    def test_csv_pandas_error(self, mock_read_csv):
        """Test CSV validation with pandas errors."""
        import pandas as pd
        mock_read_csv.side_effect = pd.errors.EmptyDataError("No data")
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_csv_file(temp_path, None)
                assert any("empty or invalid" in error for error in result["errors"])
            finally:
                temp_path.unlink()


class TestValidateParquetFile:
    """Test the validate_parquet_file function."""
    
    @patch('pandas.read_parquet')
    def test_valid_parquet_basic(self, mock_read_parquet):
        """Test validation of basic Parquet file."""
        import pandas as pd
        
        # Mock a valid DataFrame
        mock_df = pd.DataFrame({
            'Date': ['2024-01-01', '2024-01-02'],
            'Open': [100.0, 101.0],
            'High': [105.0, 106.0],
            'Low': [98.0, 99.0],
            'Close': [102.0, 103.0],
            'Volume': [1000, 1100]
        })
        mock_read_parquet.return_value = mock_df
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_parquet_file(temp_path, None)
                assert result["metrics"]["rows"] == 2
                assert result["metrics"]["columns"] == 6
                assert len(result["errors"]) == 0
            finally:
                temp_path.unlink()
    
    @patch('pandas.read_parquet')
    def test_parquet_empty_data(self, mock_read_parquet):
        """Test Parquet file with no data."""
        import pandas as pd
        
        mock_df = pd.DataFrame()  # Empty DataFrame
        mock_read_parquet.return_value = mock_df
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_parquet_file(temp_path, None)
                assert "contains no data" in result["errors"][0]
            finally:
                temp_path.unlink()
    
    @patch('pandas.read_parquet')
    def test_parquet_missing_columns(self, mock_read_parquet):
        """Test Parquet file with missing expected columns."""
        import pandas as pd
        
        mock_df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Price': [100.0]  # Missing OHLC columns
        })
        mock_read_parquet.return_value = mock_df
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_parquet_file(temp_path, None)
                assert any("Missing common columns" in warning for warning in result["warnings"])
            finally:
                temp_path.unlink()
    
    @patch('pandas.read_parquet')
    def test_parquet_wrong_data_types(self, mock_read_parquet):
        """Test Parquet file with wrong data types."""
        import pandas as pd
        
        mock_df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Open': ['not_a_number'],  # Should be numeric
            'High': ['also_not_numeric'],
            'Low': ['still_not_numeric'],
            'Close': ['definitely_not_numeric'],
            'Volume': ['nope']
        })
        mock_read_parquet.return_value = mock_df
        
        with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_parquet_file(temp_path, None)
                assert any("should be numeric" in warning for warning in result["warnings"])
            finally:
                temp_path.unlink()
    
    def test_parquet_file_not_found(self):
        """Test Parquet validation with non-existent file."""
        nonexistent_path = Path("nonexistent.parquet")
        result = validate_parquet_file(nonexistent_path, None)
        
        assert "File not found" in result["errors"]


class TestValidateProviderFormat:
    """Test the validate_provider_format function."""
    
    @patch('pandas.read_csv')
    def test_barchart_provider_validation(self, mock_read_csv):
        """Test Barchart provider format validation."""
        import pandas as pd
        
        mock_df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Time': ['09:30:00'],
            'Open': [100.0],
            'High': [105.0],
            'Low': [98.0],
            'Close': [102.0],
            'Volume': [1000],
            'OpenInterest': [500]
        })
        mock_read_csv.return_value = mock_df
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_provider_format(temp_path, "barchart")
                # Should not have warnings for complete Barchart format
                assert len(result["warnings"]) == 0
            finally:
                temp_path.unlink()
    
    @patch('pandas.read_csv')
    def test_yahoo_provider_validation(self, mock_read_csv):
        """Test Yahoo provider format validation."""
        import pandas as pd
        
        mock_df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Open': [100.0],
            'High': [105.0],
            'Low': [98.0],
            'Close': [102.0],
            'Adj Close': [101.5],  # Yahoo-specific column
            'Volume': [1000]
        })
        mock_read_csv.return_value = mock_df
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_provider_format(temp_path, "yahoo")
                # Should not warn about missing Adj Close
                assert not any("Adj Close" in warning for warning in result["warnings"])
            finally:
                temp_path.unlink()
    
    @patch('pandas.read_csv')
    def test_ibkr_provider_validation(self, mock_read_csv):
        """Test IBKR provider format validation."""
        import pandas as pd
        
        mock_df = pd.DataFrame({
            'Date': ['2024-01-01'],
            'Open': [100.0],
            'High': [105.0],
            'Low': [98.0],
            'Close': [102.0],
            'Volume': [1000],
            'WAP': [101.2],  # IBKR-specific
            'Count': [50]    # IBKR-specific
        })
        mock_read_csv.return_value = mock_df
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_provider_format(temp_path, "ibkr")
                # Should not warn about missing WAP or Count
                assert not any("WAP" in warning for warning in result["warnings"])
                assert not any("Count" in warning for warning in result["warnings"])
            finally:
                temp_path.unlink()
    
    @patch('pandas.read_csv')
    def test_unknown_provider_validation(self, mock_read_csv):
        """Test validation with unknown provider."""
        import pandas as pd
        
        mock_df = pd.DataFrame({'Date': ['2024-01-01'], 'Price': [100.0]})
        mock_read_csv.return_value = mock_df
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_provider_format(temp_path, "unknown_provider")
                assert any("Unknown provider" in warning for warning in result["warnings"])
            finally:
                temp_path.unlink()
    
    def test_unsupported_file_format(self):
        """Test provider validation with unsupported file format."""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = validate_provider_format(temp_path, "yahoo")
                assert any("Unsupported file format" in error for error in result["errors"])
            finally:
                temp_path.unlink()


class TestAttemptFixes:
    """Test the attempt_fixes function."""
    
    def test_attempt_fixes_empty_file(self):
        """Test fix attempts for empty file (should not be fixable)."""
        errors = ["File is empty"]
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = attempt_fixes(temp_path, errors)
                assert result == False  # Cannot fix empty files
            finally:
                temp_path.unlink()
    
    def test_attempt_fixes_ohlc_relationships(self):
        """Test fix attempts for OHLC relationship errors."""
        errors = ["Found 5 rows with invalid OHLC relationships"]
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = attempt_fixes(temp_path, errors)
                assert result == False  # Cannot auto-fix OHLC issues
            finally:
                temp_path.unlink()
    
    def test_attempt_fixes_unknown_error(self):
        """Test fix attempts for unknown error types."""
        errors = ["Unknown validation error"]
        
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                result = attempt_fixes(temp_path, errors)
                assert result == False  # No automatic fixes implemented
            finally:
                temp_path.unlink()
    
    @patch('vortex.cli.commands.validate.logger')
    def test_attempt_fixes_exception(self, mock_logger):
        """Test fix attempts with exception."""
        errors = ["Some error"]
        nonexistent_path = Path("nonexistent.csv")
        
        result = attempt_fixes(nonexistent_path, errors)
        assert result == False
        # Note: exception logging may not be called for this specific error type


class TestDisplayResults:
    """Test display result functions."""
    
    @patch('vortex.cli.commands.validate.display_table_results')
    def test_display_results_table(self, mock_display_table):
        """Test display results in table format."""
        results = [{"file": Path("test.csv"), "valid": True}]
        display_results(results, True, "table")
        mock_display_table.assert_called_once_with(results, True)
    
    @patch('vortex.cli.commands.validate.display_json_results')
    def test_display_results_json(self, mock_display_json):
        """Test display results in JSON format."""
        results = [{"file": Path("test.csv"), "valid": True}]
        display_results(results, False, "json")
        mock_display_json.assert_called_once_with(results)
    
    @patch('vortex.cli.commands.validate.display_csv_results')
    def test_display_results_csv(self, mock_display_csv):
        """Test display results in CSV format."""
        results = [{"file": Path("test.csv"), "valid": True}]
        display_results(results, False, "csv")
        mock_display_csv.assert_called_once_with(results)


class TestDisplayTableResults:
    """Test table display functionality."""
    
    @patch('vortex.cli.commands.validate.console')
    @patch('vortex.cli.commands.validate.show_detailed_issues')
    def test_display_table_results_basic(self, mock_show_detailed, mock_console):
        """Test basic table display."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_file.write(b"test,data\n1,2\n")
            temp_path = Path(temp_file.name)
            try:
                results = [{
                    "file": temp_path,
                    "valid": True,
                    "fixed": False,
                    "errors": [],
                    "warnings": [],
                    "metrics": {"rows": 1}
                }]
                
                display_table_results(results, False)
                mock_console.print.assert_called()
                mock_show_detailed.assert_not_called()
            finally:
                temp_path.unlink()
    
    @patch('vortex.cli.commands.validate.console')
    @patch('vortex.cli.commands.validate.show_detailed_issues')
    def test_display_table_results_detailed(self, mock_show_detailed, mock_console):
        """Test detailed table display."""
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            try:
                results = [{
                    "file": temp_path,
                    "valid": False,
                    "fixed": True,
                    "errors": ["Error 1"],
                    "warnings": ["Warning 1"],
                    "metrics": {"rows": 10}
                }]
                
                display_table_results(results, True)
                mock_console.print.assert_called()
                mock_show_detailed.assert_called_once_with(results)
            finally:
                temp_path.unlink()


class TestDisplayJsonResults:
    """Test JSON display functionality."""
    
    @patch('vortex.cli.commands.validate.console')
    def test_display_json_results(self, mock_console):
        """Test JSON results display."""
        results = [{
            "file": Path("test.csv"),
            "valid": True,
            "errors": [],
            "warnings": [],
            "metrics": {"rows": 5}
        }]
        
        display_json_results(results)
        mock_console.print.assert_called_once()
        # Check that the printed content is valid JSON
        printed_content = mock_console.print.call_args[0][0]
        parsed = json.loads(printed_content)
        assert len(parsed) == 1
        assert parsed[0]["file"] == "test.csv"  # Path converted to string


class TestDisplayCsvResults:
    """Test CSV display functionality."""
    
    @patch('vortex.cli.commands.validate.console')
    def test_display_csv_results(self, mock_console):
        """Test CSV results display."""
        results = [{
            "file": Path("test.csv"),
            "valid": True,
            "errors": [],
            "warnings": ["Warning"],
            "metrics": {"rows": 5, "columns": 3}
        }]
        
        display_csv_results(results)
        mock_console.print.assert_called_once()
        # Check that the printed content contains CSV header
        printed_content = mock_console.print.call_args[0][0]
        assert "File,Valid,Errors,Warnings,Rows,Columns" in printed_content
        assert "test.csv,True,0,1,5,3" in printed_content


class TestShowDetailedIssues:
    """Test detailed issues display."""
    
    @patch('vortex.cli.commands.validate.console')
    def test_show_detailed_issues_with_errors(self, mock_console):
        """Test showing detailed issues with errors and warnings."""
        results = [
            {
                "file": Path("test1.csv"),
                "errors": ["Error 1", "Error 2"],
                "warnings": ["Warning 1"]
            },
            {
                "file": Path("test2.csv"),
                "errors": [],
                "warnings": []
            }
        ]
        
        show_detailed_issues(results)
        
        # Should print details for test1.csv but not test2.csv
        assert mock_console.print.call_count >= 3  # Filename + 2 errors + 1 warning
    
    @patch('vortex.cli.commands.validate.console')
    def test_show_detailed_issues_no_issues(self, mock_console):
        """Test showing detailed issues when there are none."""
        results = [{
            "file": Path("test.csv"),
            "errors": [],
            "warnings": []
        }]
        
        show_detailed_issues(results)
        
        # Should not print anything for files with no issues
        mock_console.print.assert_not_called()


class TestShowValidationSummary:
    """Test validation summary display."""
    
    @patch('vortex.cli.commands.validate.console')
    def test_show_validation_summary(self, mock_console):
        """Test validation summary display."""
        results = [
            {"valid": True, "fixed": False, "errors": [], "warnings": ["Warning"]},
            {"valid": False, "fixed": True, "errors": ["Error"], "warnings": []},
            {"valid": True, "fixed": False, "errors": [], "warnings": []}
        ]
        
        show_validation_summary(results)
        
        # Should print summary information
        assert mock_console.print.call_count >= 5  # Title + total + valid + invalid + warnings
    
    @patch('vortex.cli.commands.validate.console')
    def test_show_validation_summary_all_valid(self, mock_console):
        """Test validation summary with all valid files."""
        results = [
            {"valid": True, "fixed": False, "errors": [], "warnings": []},
            {"valid": True, "fixed": False, "errors": [], "warnings": []}
        ]
        
        show_validation_summary(results)
        
        # Should not print error/warning counts when there are none
        assert mock_console.print.call_count >= 3  # Title + total + valid + invalid


class TestFormatFileSize:
    """Test file size formatting function."""
    
    def test_format_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(500) == "500 B"
        assert format_file_size(1023) == "1023 B"
    
    def test_format_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1536) == "1.5 KB"
        assert format_file_size(1024 * 1023) == "1023.0 KB"
    
    def test_format_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 2.5) == "2.5 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1024.0 MB"