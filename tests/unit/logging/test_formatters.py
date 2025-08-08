"""
Unit tests for logging formatters.

Tests structured JSON formatting, console formatting, and Rich terminal output.
"""

import json
import logging
import unittest.mock as mock
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from vortex.logging.formatters import (
    StructuredFormatter,
    create_console_formatter,
    create_rich_handler,
    create_structured_formatter,
)


class TestStructuredFormatter:
    """Test cases for StructuredFormatter."""

    def test_init_default_values(self):
        """Test formatter initialization with default values."""
        formatter = StructuredFormatter()
        assert formatter.service_name == "vortex"
        assert formatter.version == "unknown"

    def test_init_custom_values(self):
        """Test formatter initialization with custom values."""
        formatter = StructuredFormatter(service_name="test-service", version="1.2.3")
        assert formatter.service_name == "test-service"
        assert formatter.version == "1.2.3"

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = StructuredFormatter(service_name="test", version="1.0")
        
        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        record.created = 1642684800.0  # Fixed timestamp for testing

        result = formatter.format(record)
        log_entry = json.loads(result)
        
        # Verify basic structure (timestamp should be ISO format)
        assert log_entry["timestamp"].startswith("2022-01-20T")
        assert log_entry["timestamp"].endswith("+00:00")
        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "Test message"
        assert log_entry["service"] == "test"
        assert log_entry["version"] == "1.0"
        assert log_entry["logger"] == "test.logger"
        assert log_entry["module"] == "test_module"
        assert log_entry["function"] == "test_function"
        assert log_entry["line"] == 42
        assert log_entry["thread"] == 12345
        assert log_entry["thread_name"] == "MainThread"

    def test_format_with_correlation_id(self):
        """Test formatting record with correlation ID."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "corr-123-456"
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        record.created = 1642684800.0

        result = formatter.format(record)
        log_entry = json.loads(result)
        
        assert log_entry["correlation_id"] == "corr-123-456"

    def test_format_with_performance_metrics(self):
        """Test formatting record with performance metrics."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.duration = 123.45
        record.operation = "download_data"
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        record.created = 1642684800.0

        result = formatter.format(record)
        log_entry = json.loads(result)
        
        assert log_entry["duration_ms"] == 123.45
        assert log_entry["operation"] == "download_data"

    def test_format_with_extra_context(self):
        """Test formatting record with extra context."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.extra_context = {
            "user_id": "user123",
            "request_id": "req456",
            "custom_field": "value"
        }
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        record.created = 1642684800.0

        result = formatter.format(record)
        log_entry = json.loads(result)
        
        assert log_entry["user_id"] == "user123"
        assert log_entry["request_id"] == "req456"
        assert log_entry["custom_field"] == "value"

    def test_format_with_exception(self):
        """Test formatting record with exception information."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = logging.sys.exc_info()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=exc_info
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        record.created = 1642684800.0

        result = formatter.format(record)
        log_entry = json.loads(result)
        
        assert "exception" in log_entry
        assert log_entry["exception"]["type"] == "ValueError"
        assert log_entry["exception"]["message"] == "Test exception"
        assert isinstance(log_entry["exception"]["traceback"], list)
        assert len(log_entry["exception"]["traceback"]) > 0

    def test_format_with_message_args(self):
        """Test formatting record with message arguments."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message with %s and %d",
            args=("argument", 123),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        record.created = 1642684800.0

        result = formatter.format(record)
        log_entry = json.loads(result)
        
        assert log_entry["message"] == "Test message with argument and 123"

    def test_format_json_serializable(self):
        """Test that formatted output is valid JSON."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        record.created = 1642684800.0

        result = formatter.format(record)
        
        # Should not raise an exception
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


class TestConsoleFormatter:
    """Test cases for console formatter."""

    def test_create_console_formatter(self):
        """Test console formatter creation."""
        formatter = create_console_formatter()
        
        assert isinstance(formatter, logging.Formatter)
        assert formatter._fmt == '%(asctime)s [%(levelname)8s] %(name)s: %(message)s'
        assert formatter.datefmt == '%Y-%m-%d %H:%M:%S'

    def test_console_formatter_output(self):
        """Test console formatter output format."""
        formatter = create_console_formatter()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.created = 1642684800.0  # Fixed timestamp
        
        result = formatter.format(record)
        
        # Should contain timestamp, level, logger name, and message
        assert "2022-01-20" in result  # Date part should be correct
        assert "[    INFO]" in result
        assert "test.logger" in result
        assert "Test message" in result


class TestRichHandler:
    """Test cases for Rich handler."""

    @patch('vortex.logging.formatters.rich_available', True)
    @patch('vortex.logging.formatters.RichHandler')
    @patch('vortex.logging.formatters.Console')
    def test_create_rich_handler_success(self, mock_console, mock_rich_handler):
        """Test successful Rich handler creation."""
        mock_console_instance = MagicMock()
        mock_console.return_value = mock_console_instance
        mock_handler_instance = MagicMock()
        mock_rich_handler.return_value = mock_handler_instance
        
        result = create_rich_handler()
        
        # Verify Console was created with correct parameters
        mock_console.assert_called_once_with(stderr=True)
        
        # Verify RichHandler was created with correct parameters
        mock_rich_handler.assert_called_once_with(
            console=mock_console_instance,
            show_time=True,
            show_level=True,
            show_path=True,
            markup=True,
            rich_tracebacks=True
        )
        
        assert result is mock_handler_instance

    @patch('vortex.logging.formatters.rich_available', False)
    def test_create_rich_handler_not_available(self):
        """Test Rich handler creation when Rich is not available."""
        with pytest.raises(ImportError, match="Rich library not available"):
            create_rich_handler()


class TestStructuredFormatterFactory:
    """Test cases for structured formatter factory."""

    def test_create_structured_formatter_default(self):
        """Test structured formatter creation with default parameters."""
        formatter = create_structured_formatter()
        
        assert isinstance(formatter, StructuredFormatter)
        assert formatter.service_name == "vortex"
        assert formatter.version == "unknown"

    def test_create_structured_formatter_custom(self):
        """Test structured formatter creation with custom parameters."""
        formatter = create_structured_formatter(service_name="custom", version="2.0.0")
        
        assert isinstance(formatter, StructuredFormatter)
        assert formatter.service_name == "custom"
        assert formatter.version == "2.0.0"


class TestRichImportHandling:
    """Test cases for Rich import handling."""

    @patch('vortex.logging.formatters.rich_available', False)
    def test_rich_not_available_module_level(self):
        """Test module behavior when Rich is not available."""
        # The module should still load and rich_available should be False
        from vortex.logging.formatters import rich_available
        assert rich_available is False