"""Tests for the validate CLI command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
from click.testing import CliRunner
import tempfile
import csv
import json

from vortex.cli.commands.validate import (
    validate, get_files_to_validate, run_validation, 
    validate_single_file, validate_csv_file
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
            writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
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
            writer.writerow(["Date", "Open", "High", "Low", "Close", "Volume"])
            writer.writerow(["2024-01-01", "100", "105", "98", "102", "1000"])
            temp_path = Path(temp_file.name)
            
            try:
                result = validate_csv_file(temp_path, "yahoo")
                assert isinstance(result["errors"], list)
                assert isinstance(result["warnings"], list)
                assert isinstance(result["metrics"], dict)
            finally:
                temp_path.unlink()