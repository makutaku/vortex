"""Simple tests for error handling utilities to increase coverage."""

import pytest
from pathlib import Path
from unittest.mock import mock_open, patch
from vortex.utils.error_handling import FileOperationHandler
from vortex.exceptions.config import ConfigurationError


class TestFileOperationHandlerSimple:
    """Test file operation handler simple cases."""

    def test_safe_file_operation_success(self):
        """Test successful file operation."""
        mock_content = b"test content"

        with patch("builtins.open", mock_open(read_data=mock_content)):
            result = FileOperationHandler.safe_file_operation(
                file_path="test.txt",
                operation=lambda f: f.read(),
                mode="rb",
                file_type="test file",
                operation_name="read",
            )
            assert result == mock_content

    def test_safe_file_operation_write(self):
        """Test file write operation."""
        with patch("builtins.open", mock_open()) as mocked_file:
            def write_op(f):
                f.write("test data")
                return True

            result = FileOperationHandler.safe_file_operation(
                file_path="test.txt",
                operation=write_op,
                mode="w",
                file_type="test file",
                operation_name="write",
            )
            assert result is True
            mocked_file.assert_called_once_with("test.txt", "w")

    def test_safe_file_operation_with_default(self):
        """Test file operation with default value on missing file."""
        result = FileOperationHandler.safe_file_operation(
            file_path="/nonexistent/file.txt",
            operation=lambda f: f.read(),
            mode="r",
            file_type="config file",
            operation_name="read",
            default_on_missing={},
        )
        assert result == {}

    def test_safe_file_operation_raises_on_missing_read(self):
        """Test that read mode raises on missing file without default."""
        with pytest.raises(ConfigurationError):
            FileOperationHandler.safe_file_operation(
                file_path="/nonexistent/file.txt",
                operation=lambda f: f.read(),
                mode="r",
                file_type="config file",
                operation_name="read",
            )

    def test_safe_file_operation_permission_error(self):
        """Test that permission errors are handled properly."""
        with patch("builtins.open") as mocked_open:
            mocked_open.side_effect = PermissionError("Permission denied")

            with pytest.raises(ConfigurationError, match="Permission"):
                FileOperationHandler.safe_file_operation(
                    file_path="/restricted/file.txt",
                    operation=lambda f: f.read(),
                    mode="r",
                    file_type="config file",
                    operation_name="read",
                )
