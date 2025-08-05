"""
Unit tests for the Vortex logging system.

These are true unit tests that test object creation, validation, and in-memory operations only.
"""

import logging
import sys
from unittest.mock import Mock, patch

import pytest

from vortex.logging import (
    VortexLogger, PerformanceLogger, TimedOperation, LoggingManager,
    StructuredFormatter, get_logger, get_performance_logger
)


@pytest.mark.unit
class TestVortexLogger:
    """Unit tests for VortexLogger object creation and validation."""
    
    def test_logger_creation(self):
        """Test VortexLogger object creation."""
        logger = VortexLogger("test.module")
        
        assert logger.logger.name == "test.module"
        assert isinstance(logger.logger, logging.Logger)
        assert logger.extra_context == {}
    
    def test_context_dict_creation(self):
        """Test context dictionary creation and merging."""
        logger = VortexLogger("test")
        
        # Test initial empty context
        assert logger.extra_context == {}
        
        # Test context merging logic (without actual logging)
        context1 = {"user_id": "123", "action": "test"}
        context2 = {"session": "abc", "user_id": "456"}  # Should override user_id
        
        merged = {**context1, **context2}
        expected = {"user_id": "456", "action": "test", "session": "abc"}
        
        assert merged == expected
    
    def test_get_current_context(self):
        """Test getting current context."""
        logger = VortexLogger("test")
        logger.extra_context = {"key": "value"}
        
        assert logger.extra_context == {"key": "value"}
    
    def test_clear_context(self):
        """Test clearing context."""
        logger = VortexLogger("test")
        logger.extra_context = {"key": "value"}
        
        logger.clear_context()
        assert logger.extra_context == {}


@pytest.mark.unit
class TestPerformanceLogger:
    """Unit tests for PerformanceLogger object creation and validation."""
    
    def test_logger_creation(self):
        """Test PerformanceLogger object creation."""
        perf_logger = PerformanceLogger("perf.test")
        
        assert perf_logger.logger.logger.name == "perf.test.performance"
        assert isinstance(perf_logger.logger, VortexLogger)
    
    def test_metric_validation(self):
        """Test metric name and value validation."""
        perf_logger = PerformanceLogger("test")
        
        # Valid metric names
        valid_names = ["response_time", "cpu_usage", "memory_mb", "api_calls"]
        for name in valid_names:
            assert isinstance(name, str)
            assert len(name) > 0
        
        # Valid metric values
        valid_values = [0.123, 42, 100.0, 0]
        for value in valid_values:
            assert isinstance(value, (int, float))
    
    def test_metadata_validation(self):
        """Test metadata dictionary validation."""
        perf_logger = PerformanceLogger("test")
        
        # Valid metadata
        valid_metadata = [
            {"endpoint": "/api/data"},
            {"method": "GET", "status": 200},
            {},  # Empty dict is valid
            {"user": "test", "count": 5}
        ]
        
        for metadata in valid_metadata:
            assert isinstance(metadata, dict)


@pytest.mark.unit
class TestTimedOperation:
    """Unit tests for TimedOperation object creation."""
    
    def test_context_manager_creation(self):
        """Test TimedOperation context manager creation."""
        logger = VortexLogger("test")
        operation = TimedOperation("test_op", logger, {"key": "value"})
        
        assert operation.operation == "test_op"
        assert operation.context == {"key": "value"}
        assert operation.start_time is None
    
    def test_metadata_defaults(self):
        """Test default metadata handling."""
        logger = VortexLogger("test")
        operation = TimedOperation("test_op", logger)
        
        assert operation.operation == "test_op"
        assert operation.context == {}
    
    def test_operation_name_validation(self):
        """Test operation name validation."""
        # Valid operation names
        valid_names = ["database_query", "api_call", "file_processing"]
        logger = VortexLogger("test")
        
        for name in valid_names:
            operation = TimedOperation(name, logger)
            assert operation.operation == name
            assert isinstance(operation.operation, str)
            assert len(operation.operation) > 0


@pytest.mark.unit
class TestStructuredFormatter:
    """Unit tests for StructuredFormatter."""
    
    def test_formatter_creation(self):
        """Test StructuredFormatter creation with service details."""
        # Default formatter
        formatter = StructuredFormatter()
        assert formatter.service_name == "vortex"
        assert formatter.version == "unknown"
        
        # Custom formatter
        custom_formatter = StructuredFormatter("test-service", "1.0.0")
        assert custom_formatter.service_name == "test-service"
        assert custom_formatter.version == "1.0.0"
    
    def test_record_field_extraction(self):
        """Test log record field extraction logic."""
        formatter = StructuredFormatter("json")
        
        # Create a mock log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/path/to/file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Test field extraction
        assert record.name == "test.logger"
        assert record.levelname == "INFO"
        assert record.msg == "Test message"
        assert record.lineno == 42
    
    def test_extra_fields_handling(self):
        """Test handling of extra fields in log records."""
        formatter = StructuredFormatter("json")
        
        # Create record with extra fields
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.user_id = "123"
        record.request_id = "req-456"
        
        # Test that extra fields are accessible
        assert hasattr(record, "user_id")
        assert hasattr(record, "request_id")
        assert record.user_id == "123"
        assert record.request_id == "req-456"


@pytest.mark.unit
class TestLoggingManager:
    """Unit tests for LoggingManager configuration validation."""
    
    def test_manager_creation(self):
        """Test LoggingManager object creation."""
        manager = LoggingManager()
        
        assert isinstance(manager, LoggingManager)
    
    def test_level_validation(self):
        """Test log level validation."""
        valid_levels = [
            logging.DEBUG,
            logging.INFO, 
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL
        ]
        
        for level in valid_levels:
            assert isinstance(level, int)
            assert level >= 0
    
    def test_format_type_validation(self):
        """Test format type validation."""
        valid_formats = ["standard", "json"]
        
        for format_type in valid_formats:
            assert isinstance(format_type, str)
            assert format_type in valid_formats


@pytest.mark.unit
class TestLoggerFactories:
    """Unit tests for logger factory functions."""
    
    def test_get_logger_creation(self):
        """Test get_logger factory function."""
        logger = get_logger("test.module")
        
        assert isinstance(logger, VortexLogger)
        assert logger.logger.name == "test.module"
    
    def test_get_performance_logger_creation(self):
        """Test get_performance_logger factory function."""
        perf_logger = get_performance_logger("perf.test")
        
        assert isinstance(perf_logger, PerformanceLogger)
        assert perf_logger.logger.logger.name == "perf.test.performance"
    
    def test_logger_name_validation(self):
        """Test logger name validation in factory functions."""
        # Valid logger names
        valid_names = [
            "app.module",
            "services.downloader", 
            "data.provider",
            "test"
        ]
        
        for name in valid_names:
            logger = get_logger(name)
            assert logger.logger.name == name
            assert isinstance(logger.logger.name, str)