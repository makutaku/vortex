"""
Tests for the Vortex logging and observability system.
"""

import json
import logging
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from vortex.logging import (
    StructuredFormatter, VortexLogger, PerformanceLogger, 
    TimedOperation, LoggingConfig, LoggingManager,
    configure_logging, get_logger, get_performance_logger,
    timed, logged
)
from vortex.logging_integration import (
    configure_logging_from_config, get_module_logger,
    HealthChecker, register_health_check, run_health_checks
)
from vortex.config import VortexConfig


@pytest.mark.unit
class TestStructuredFormatter:
    """Test the structured JSON formatter."""
    
    def test_basic_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter("test-service", "1.0.0")
        
        # Create a log record
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.thread = 12345
        record.threadName = "MainThread"
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["service"] == "test-service"
        assert log_data["version"] == "1.0.0"
        assert log_data["logger"] == "test.logger"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert log_data["thread"] == 12345
        assert log_data["thread_name"] == "MainThread"
        assert "timestamp" in log_data
    
    def test_correlation_id(self):
        """Test correlation ID inclusion."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=1,
            msg="Test", args=(), exc_info=None
        )
        record.correlation_id = "test-correlation-123"
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert log_data["correlation_id"] == "test-correlation-123"
    
    def test_performance_metrics(self):
        """Test performance metrics inclusion."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=1,
            msg="Test", args=(), exc_info=None
        )
        record.duration = 123.45
        record.operation = "test_operation"
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert log_data["duration_ms"] == 123.45
        assert log_data["operation"] == "test_operation"
    
    def test_extra_context(self):
        """Test extra context inclusion."""
        formatter = StructuredFormatter()
        
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=1,
            msg="Test", args=(), exc_info=None
        )
        record.extra_context = {"user_id": "123", "request_id": "abc"}
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert log_data["user_id"] == "123"
        assert log_data["request_id"] == "abc"
    
    def test_exception_info(self):
        """Test exception information formatting."""
        formatter = StructuredFormatter()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="", lineno=1,
                msg="Test error", args=(), exc_info=True
            )
        
        result = formatter.format(record)
        log_data = json.loads(result)
        
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert isinstance(log_data["exception"]["traceback"], list)


@pytest.mark.unit
class TestVortexLogger:
    """Test the enhanced Vortex logger."""
    
    @pytest.fixture
    def logger(self):
        """Create a test logger."""
        return VortexLogger("test.logger", "test-correlation-123")
    
    def test_logger_creation(self, logger):
        """Test logger creation with correlation ID."""
        assert logger.correlation_id == "test-correlation-123"
        assert logger.logger.name == "test.logger"
        assert logger.extra_context == {}
    
    def test_logging_methods(self, logger, caplog):
        """Test different logging methods."""
        with caplog.at_level(logging.DEBUG):
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message", exc_info=False)
            logger.critical("Critical message", exc_info=False)
        
        messages = [record.message for record in caplog.records]
        assert "Debug message" in messages
        assert "Info message" in messages
        assert "Warning message" in messages
        assert "Error message" in messages
        assert "Critical message" in messages
    
    def test_context_management(self, logger):
        """Test context setting and clearing."""
        logger.set_context(user_id="123", session_id="abc")
        assert logger.extra_context["user_id"] == "123"
        assert logger.extra_context["session_id"] == "abc"
        
        logger.clear_context()
        assert logger.extra_context == {}
    
    def test_temporary_context(self, logger, caplog):
        """Test temporary context manager."""
        logger.set_context(permanent="yes")
        
        with logger.context(temporary="value") as ctx_logger:
            assert ctx_logger.extra_context["permanent"] == "yes"
            assert ctx_logger.extra_context["temporary"] == "value"
            
            with caplog.at_level(logging.INFO):
                ctx_logger.info("Test message")
        
        # After context, temporary should be gone but permanent remains
        assert logger.extra_context["permanent"] == "yes"
        assert "temporary" not in logger.extra_context


@pytest.mark.unit
class TestPerformanceLogger:
    """Test the performance logging functionality."""
    
    @pytest.fixture
    def perf_logger(self):
        """Create a performance logger."""
        vortex_logger = VortexLogger("test.perf")
        return PerformanceLogger(vortex_logger)
    
    def test_time_operation(self, perf_logger, caplog):
        """Test operation timing."""
        with caplog.at_level(logging.DEBUG):
            with perf_logger.time_operation("test_operation", user_id="123"):
                time.sleep(0.01)  # Small delay to ensure measurable time
        
        records = caplog.records
        assert len(records) >= 2  # Start and completion messages
        
        # Check start message
        start_record = records[0]
        assert "Started operation: test_operation" in start_record.message
        
        # Check completion message
        completion_record = records[-1]
        assert "Completed operation: test_operation" in completion_record.message
        assert "ms" in completion_record.message
    
    def test_failed_operation(self, perf_logger, caplog):
        """Test timing of failed operations."""
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(ValueError):
                with perf_logger.time_operation("failing_operation"):
                    raise ValueError("Test failure")
        
        records = caplog.records
        assert len(records) >= 2
        
        # Check failure message
        failure_record = records[-1]
        assert "Failed operation: failing_operation" in failure_record.message
        assert "Test failure" in failure_record.message
    
    def test_log_metric(self, perf_logger, caplog):
        """Test metric logging."""
        with caplog.at_level(logging.INFO):
            perf_logger.log_metric("response_time", 123.45, "ms", endpoint="/api/data")
        
        record = caplog.records[0]
        assert "Metric: response_time = 123.45ms" in record.message
    
    def test_log_counter(self, perf_logger, caplog):
        """Test counter logging."""
        with caplog.at_level(logging.INFO):
            perf_logger.log_counter("requests_processed", 5, service="api")
        
        record = caplog.records[0]
        assert "Counter: requests_processed = 5" in record.message


@pytest.mark.unit
class TestTimedOperation:
    """Test the timed operation context manager."""
    
    def test_successful_operation(self, caplog):
        """Test timing a successful operation."""
        logger = VortexLogger("test")
        
        with caplog.at_level(logging.DEBUG):
            with TimedOperation(logger, "test_op", user_id="123"):
                time.sleep(0.01)
        
        records = caplog.records
        assert len(records) == 2
        
        start_record, end_record = records
        assert "Started operation: test_op" in start_record.message
        assert "Completed operation: test_op" in end_record.message
    
    def test_failed_operation(self, caplog):
        """Test timing a failed operation."""
        logger = VortexLogger("test")
        
        with caplog.at_level(logging.DEBUG):
            with pytest.raises(RuntimeError):
                with TimedOperation(logger, "failing_op"):
                    raise RuntimeError("Operation failed")
        
        records = caplog.records
        assert len(records) == 2
        
        start_record, end_record = records
        assert "Started operation: failing_op" in start_record.message
        assert "Failed operation: failing_op" in end_record.message
        assert "Operation failed" in end_record.message


@pytest.mark.unit
class TestLoggingConfig:
    """Test logging configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = LoggingConfig()
        
        assert config.level == logging.INFO
        assert config.format_type == "console"
        assert config.output == ["console"]
        assert config.file_path is None
        assert config.max_file_size == 10 * 1024 * 1024
        assert config.backup_count == 5
        assert config.service_name == "vortex"
        assert config.version == "unknown"
    
    def test_custom_config(self, temp_dir):
        """Test custom configuration."""
        log_file = temp_dir / "app.log"
        
        config = LoggingConfig(
            level=logging.DEBUG,
            format_type="json",
            output=["console", "file"],
            file_path=log_file,
            max_file_size=1024,
            backup_count=3,
            service_name="test-service",
            version="2.0.0"
        )
        
        assert config.level == logging.DEBUG
        assert config.format_type == "json"
        assert config.output == ["console", "file"]
        assert config.file_path == log_file
        assert config.max_file_size == 1024
        assert config.backup_count == 3
        assert config.service_name == "test-service"
        assert config.version == "2.0.0"


@pytest.mark.unit
class TestLoggingManager:
    """Test the centralized logging manager."""
    
    def test_singleton_behavior(self):
        """Test that LoggingManager is a singleton."""
        manager1 = LoggingManager()
        manager2 = LoggingManager()
        
        assert manager1 is manager2
    
    def test_configuration(self, temp_dir):
        """Test logging configuration."""
        log_file = temp_dir / "test.log"
        config = LoggingConfig(
            level=logging.DEBUG,
            format_type="json",
            output=["file"],
            file_path=log_file
        )
        
        manager = LoggingManager()
        manager.configure(config)
        
        assert manager.config == config
        assert len(manager.handlers) == 1
    
    def test_get_logger(self):
        """Test getting logger instances."""
        manager = LoggingManager()
        
        logger1 = manager.get_logger("test.logger")
        logger2 = manager.get_logger("test.logger", "correlation-123")
        
        assert isinstance(logger1, VortexLogger)
        assert isinstance(logger2, VortexLogger)
        assert logger2.correlation_id == "correlation-123"
    
    def test_get_performance_logger(self):
        """Test getting performance logger instances."""
        manager = LoggingManager()
        
        perf_logger = manager.get_performance_logger("test.perf")
        
        assert isinstance(perf_logger, PerformanceLogger)
        assert isinstance(perf_logger.logger, VortexLogger)


@pytest.mark.unit
class TestDecorators:
    """Test logging decorators."""
    
    def test_timed_decorator(self, caplog):
        """Test the @timed decorator."""
        
        @timed("custom_operation")
        def test_function():
            time.sleep(0.01)
            return "result"
        
        with caplog.at_level(logging.DEBUG):
            result = test_function()
        
        assert result == "result"
        
        # Should have timing logs
        messages = [record.message for record in caplog.records]
        start_found = any("Started operation: custom_operation" in msg for msg in messages)
        complete_found = any("Completed operation: custom_operation" in msg for msg in messages)
        
        assert start_found
        assert complete_found
    
    def test_logged_decorator(self, caplog):
        """Test the @logged decorator."""
        
        @logged("info")
        def test_function(x, y):
            return x + y
        
        with caplog.at_level(logging.INFO):
            result = test_function(1, 2)
        
        assert result == 3
        
        messages = [record.message for record in caplog.records]
        assert any("Calling test_function" in msg for msg in messages)
        assert any("Completed test_function" in msg for msg in messages)
    
    def test_logged_decorator_with_exception(self, caplog):
        """Test @logged decorator with exceptions."""
        
        @logged("info") 
        def failing_function():
            raise ValueError("Test error")
        
        with caplog.at_level(logging.INFO):
            with pytest.raises(ValueError):
                failing_function()
        
        messages = [record.message for record in caplog.records]
        assert any("Calling failing_function" in msg for msg in messages)
        assert any("Failed failing_function" in msg for msg in messages)


@pytest.mark.unit
class TestHealthChecker:
    """Test the health check functionality."""
    
    @pytest.fixture
    def health_checker(self):
        """Create a health checker instance."""
        return HealthChecker()
    
    def test_register_check(self, health_checker):
        """Test registering health checks."""
        def dummy_check():
            return True
        
        health_checker.register_check("dummy", dummy_check)
        assert "dummy" in health_checker.checks
        assert health_checker.checks["dummy"] == dummy_check
    
    def test_successful_checks(self, health_checker):
        """Test running successful health checks."""
        def check1():
            return True
        
        def check2():
            return {"healthy": True, "details": "All good"}
        
        health_checker.register_check("check1", check1)
        health_checker.register_check("check2", check2)
        
        results = health_checker.run_checks()
        
        assert results["status"] == "healthy"
        assert "timestamp" in results
        assert len(results["checks"]) == 2
        
        assert results["checks"]["check1"]["healthy"] is True
        assert results["checks"]["check2"]["healthy"] is True
        assert results["checks"]["check2"]["details"] == "All good"
        
        # Should have duration for both checks
        assert "duration_ms" in results["checks"]["check1"]
        assert "duration_ms" in results["checks"]["check2"]
    
    def test_failed_checks(self, health_checker):
        """Test running failed health checks."""
        def failing_check():
            return False
        
        def error_check():
            raise RuntimeError("Check failed")
        
        health_checker.register_check("failing", failing_check)
        health_checker.register_check("error", error_check)
        
        results = health_checker.run_checks()
        
        assert results["status"] == "unhealthy"
        assert results["checks"]["failing"]["healthy"] is False
        assert results["checks"]["error"]["healthy"] is False
        assert results["checks"]["error"]["error"] == "Check failed"
        assert results["checks"]["error"]["error_type"] == "RuntimeError"
    
    def test_mixed_checks(self, health_checker):
        """Test running a mix of successful and failed checks."""
        def good_check():
            return True
        
        def bad_check():
            return False
        
        health_checker.register_check("good", good_check)
        health_checker.register_check("bad", bad_check)
        
        results = health_checker.run_checks()
        
        assert results["status"] == "unhealthy"  # One failure makes overall unhealthy
        assert results["checks"]["good"]["healthy"] is True
        assert results["checks"]["bad"]["healthy"] is False


@pytest.mark.unit
class TestLoggingIntegration:
    """Test integration with Vortex configuration."""
    
    def test_configure_from_config(self, sample_config_data):
        """Test configuring logging from VortexConfig."""
        # Update config with logging settings
        sample_config_data["general"]["logging"] = {
            "level": "DEBUG",
            "format": "json",
            "output": ["console"]
        }
        
        config = VortexConfig(**sample_config_data)
        
        # This should not raise an exception
        configure_logging_from_config(config, "test-service", "1.0.0")
    
    def test_get_module_logger(self):
        """Test getting module logger."""
        logger = get_module_logger("test.module")
        
        assert isinstance(logger, VortexLogger)
        assert logger.logger.name == "test.module"
    
    def test_health_checks_registration(self):
        """Test that built-in health checks are registered."""
        results = run_health_checks()
        
        assert "logging_system" in results["checks"]
        assert "config_system" in results["checks"]
        
        # Both should be healthy in test environment
        assert results["checks"]["logging_system"]["healthy"] is True


@pytest.mark.integration
class TestLoggingEndToEnd:
    """End-to-end logging tests."""
    
    def test_json_logging_to_file(self, temp_dir):
        """Test complete JSON logging to file."""
        log_file = temp_dir / "test.log"
        
        config = LoggingConfig(
            level=logging.INFO,
            format_type="json",
            output=["file"],
            file_path=log_file,
            service_name="test-service",
            version="1.0.0"
        )
        
        configure_logging(config)
        
        logger = get_logger("test.integration", "correlation-123")
        logger.set_context(user_id="user123")
        logger.info("Test message", operation="test_op")
        
        # Force log flush
        for handler in logging.getLogger().handlers:
            handler.flush()
        
        # Read and parse log file
        assert log_file.exists()
        with open(log_file) as f:
            log_line = f.readline().strip()
        
        log_data = json.loads(log_line)
        
        assert log_data["message"] == "Test message"
        assert log_data["level"] == "INFO"
        assert log_data["service"] == "test-service"
        assert log_data["version"] == "1.0.0"
        assert log_data["correlation_id"] == "correlation-123"
        assert log_data["user_id"] == "user123"
        assert log_data["operation"] == "test_op"
    
    def test_performance_logging_integration(self, caplog):
        """Test performance logging integration."""
        perf_logger = get_performance_logger("test.performance")
        
        with caplog.at_level(logging.INFO):
            with perf_logger.time_operation("database_query", table="users"):
                time.sleep(0.01)
            
            perf_logger.log_metric("query_count", 5, "queries")
            perf_logger.log_counter("cache_hits", 3)
        
        messages = [record.message for record in caplog.records]
        
        # Should have timing messages
        assert any("database_query" in msg for msg in messages)
        
        # Should have metric messages
        assert any("Metric: query_count = 5queries" in msg for msg in messages)
        assert any("Counter: cache_hits = 3" in msg for msg in messages)