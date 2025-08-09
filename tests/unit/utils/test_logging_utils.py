"""Tests for logging utilities."""

import pytest
import logging
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from vortex.utils.logging_utils import (
    init_logging, LoggingContext, StructuredErrorLogger,
    get_structured_logger, log_error_with_context
)


class TestInitLogging:
    """Test the init_logging function."""
    
    @patch('vortex.utils.logging_utils.logging.basicConfig')
    def test_init_logging_default_level(self, mock_basic_config):
        """Test init_logging with default INFO level."""
        init_logging()
        
        mock_basic_config.assert_called_once_with(
            level=logging.INFO,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    @patch('vortex.utils.logging_utils.logging.basicConfig')
    def test_init_logging_custom_level(self, mock_basic_config):
        """Test init_logging with custom level."""
        init_logging(level=logging.DEBUG)
        
        mock_basic_config.assert_called_once_with(
            level=logging.DEBUG,
            format='%(asctime)s %(levelname)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


class TestLoggingContext:
    """Test the LoggingContext class."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)
    
    def test_logging_context_initialization_defaults(self):
        """Test LoggingContext initialization with defaults."""
        context = LoggingContext()
        
        assert context.entry_msg is None
        assert context.success_msg is None
        assert context.failure_msg is None
        assert context.exit_msg is None
        assert context.entry_level == logging.DEBUG
        assert context.exit_level == logging.DEBUG
        assert context.success_level == logging.INFO
        assert context.failure_level == logging.ERROR
    
    def test_logging_context_initialization_custom(self, mock_logger):
        """Test LoggingContext initialization with custom values."""
        context = LoggingContext(
            entry_msg="Starting",
            success_msg="Success",
            failure_msg="Failed",
            exit_msg="Finished",
            logger=mock_logger,
            entry_level=logging.INFO,
            exit_level=logging.INFO,
            success_level=logging.DEBUG,
            failure_level=logging.CRITICAL
        )
        
        assert context.entry_msg == "Starting"
        assert context.success_msg == "Success"
        assert context.failure_msg == "Failed"
        assert context.exit_msg == "Finished"
        assert context.logger == mock_logger
        assert context.entry_level == logging.INFO
        assert context.exit_level == logging.INFO
        assert context.success_level == logging.DEBUG
        assert context.failure_level == logging.CRITICAL
    
    def test_logging_context_successful_execution(self, mock_logger):
        """Test LoggingContext with successful execution (no exception)."""
        context = LoggingContext(
            entry_msg="Starting task",
            success_msg="Task completed",
            exit_msg="Exiting",
            logger=mock_logger
        )
        
        # Test context manager for successful execution
        with context:
            pass  # No exception raised
        
        # Verify logging calls
        expected_calls = [
            (logging.DEBUG, "Starting task"),
            (logging.INFO, "Task completed"),
            (logging.DEBUG, "Exiting")
        ]
        
        assert mock_logger.log.call_count == 3
        for i, (level, message) in enumerate(expected_calls):
            call_args = mock_logger.log.call_args_list[i]
            assert call_args[0] == (level, message)
    
    def test_logging_context_exception_execution(self, mock_logger):
        """Test LoggingContext with exception during execution."""
        context = LoggingContext(
            entry_msg="Starting task",
            failure_msg="Task failed",
            exit_msg="Exiting after error",
            logger=mock_logger
        )
        
        # Test context manager with exception
        with pytest.raises(ValueError):
            with context:
                raise ValueError("Test error")
        
        # Verify logging calls
        expected_calls = [
            (logging.DEBUG, "Starting task"),
            (logging.ERROR, "Task failed"),  
            (logging.DEBUG, "Exiting after error")
        ]
        
        assert mock_logger.log.call_count == 3
        for i, (level, message) in enumerate(expected_calls):
            call_args = mock_logger.log.call_args_list[i]
            assert call_args[0] == (level, message)
    
    def test_logging_context_no_messages(self, mock_logger):
        """Test LoggingContext with no messages configured."""
        context = LoggingContext(logger=mock_logger)
        
        # Test context manager with no messages
        with context:
            pass
        
        # Should not call log since no messages are set
        mock_logger.log.assert_not_called()
    
    def test_logging_context_partial_messages(self, mock_logger):
        """Test LoggingContext with only some messages configured."""
        context = LoggingContext(
            entry_msg="Starting",
            success_msg=None,  # No success message
            failure_msg="Failed",
            exit_msg=None,     # No exit message
            logger=mock_logger
        )
        
        # Test successful execution
        with context:
            pass
        
        # Should only log entry message (success and exit are None)
        mock_logger.log.assert_called_once_with(logging.DEBUG, "Starting")
    
    def test_log_method_with_message(self, mock_logger):
        """Test the log method with a message."""
        context = LoggingContext(logger=mock_logger)
        
        context.log("Test message", logging.WARNING)
        
        mock_logger.log.assert_called_once_with(logging.WARNING, "Test message")
    
    def test_log_method_with_none_message(self, mock_logger):
        """Test the log method with None message."""
        context = LoggingContext(logger=mock_logger)
        
        context.log(None, logging.INFO)
        
        # Should not call log when message is None
        mock_logger.log.assert_not_called()
    
    def test_log_method_with_empty_message(self, mock_logger):
        """Test the log method with empty string message."""
        context = LoggingContext(logger=mock_logger)
        
        context.log("", logging.INFO)
        
        # Should not call log when message is empty
        mock_logger.log.assert_not_called()
    
    def test_log_method_default_level(self, mock_logger):
        """Test the log method with default INFO level."""
        context = LoggingContext(logger=mock_logger)
        
        context.log("Test message")
        
        mock_logger.log.assert_called_once_with(logging.INFO, "Test message")
    
    @patch('vortex.utils.logging_utils.logging.getLogger')
    def test_default_logger_creation(self, mock_get_logger):
        """Test that default logger is created when none provided."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        context = LoggingContext(entry_msg="Test")
        
        mock_get_logger.assert_called_once_with('vortex.utils.logging_utils')
        assert context.logger == mock_logger


class TestStructuredErrorLogger:
    """Test the StructuredErrorLogger class."""
    
    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock(spec=logging.Logger)
    
    @patch('vortex.utils.logging_utils.logging.getLogger')
    def test_structured_error_logger_initialization(self, mock_get_logger):
        """Test StructuredErrorLogger initialization."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        error_logger = StructuredErrorLogger("test.logger")
        
        mock_get_logger.assert_called_once_with("test.logger")
        assert error_logger.logger == mock_logger
    
    @patch('vortex.utils.logging_utils.logging.getLogger')
    def test_structured_error_logger_default_name(self, mock_get_logger):
        """Test StructuredErrorLogger with default logger name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        error_logger = StructuredErrorLogger()
        
        mock_get_logger.assert_called_once_with("vortex.error")
        assert error_logger.logger == mock_logger
    
    def test_log_error_basic(self):
        """Test basic error logging functionality."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        test_error = ValueError("Test error message")
        correlation_id = error_logger.log_error(
            error=test_error,
            message="Something went wrong"
        )
        
        # Should return a correlation ID
        assert correlation_id is not None
        assert len(correlation_id) == 8
        
        # Should have logged the error
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Something went wrong" in call_args[0][0]
        assert correlation_id in call_args[0][0]
        
        # Should have structured data in extra
        extra = call_args[1]['extra']
        assert 'error_data' in extra
        assert 'correlation_id' in extra
        assert extra['structured'] is True
    
    def test_log_error_with_all_params(self):
        """Test error logging with all parameters."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        test_error = RuntimeError("Database connection failed")
        custom_correlation_id = "test-123"
        
        returned_id = error_logger.log_error(
            error=test_error,
            message="Database operation failed",
            correlation_id=custom_correlation_id,
            context={"table": "users", "query": "SELECT *"},
            user_id="user123",
            operation="fetch_users",
            provider="postgres",
            include_traceback=True
        )
        
        assert returned_id == custom_correlation_id
        
        # Check the structured data
        call_args = mock_logger.error.call_args
        error_data = call_args[1]['extra']['error_data']
        
        assert error_data['correlation_id'] == custom_correlation_id
        assert error_data['error_type'] == 'RuntimeError'
        assert error_data['error_message'] == 'Database connection failed'
        assert error_data['message'] == 'Database operation failed'
        assert error_data['context'] == {"table": "users", "query": "SELECT *"}
        assert error_data['user_id'] == "user123"
        assert error_data['operation'] == "fetch_users"
        assert error_data['provider'] == "postgres"
        assert 'traceback' in error_data
        assert 'timestamp' in error_data
    
    def test_log_error_with_vortex_error_attributes(self):
        """Test error logging with VortexError-like attributes."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        # Create a mock error with VortexError attributes
        test_error = ValueError("Custom error")
        test_error.correlation_id = "vortex-456"
        test_error.error_code = "DATA_FETCH_ERROR"
        test_error.context = {"provider": "yahoo", "symbol": "AAPL"}
        
        error_logger.log_error(error=test_error, message="Vortex operation failed")
        
        call_args = mock_logger.error.call_args
        error_data = call_args[1]['extra']['error_data']
        
        assert error_data['vortex_correlation_id'] == "vortex-456"
        assert error_data['error_code'] == "DATA_FETCH_ERROR"
        assert error_data['vortex_context'] == {"provider": "yahoo", "symbol": "AAPL"}
    
    def test_log_error_no_traceback(self):
        """Test error logging without traceback."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        test_error = ValueError("Test error")
        error_logger.log_error(
            error=test_error,
            message="Error without traceback",
            include_traceback=False
        )
        
        call_args = mock_logger.error.call_args
        error_data = call_args[1]['extra']['error_data']
        
        assert 'traceback' not in error_data
    
    def test_log_operation_start(self):
        """Test operation start logging."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        correlation_id = error_logger.log_operation_start(
            operation="download_data",
            context={"provider": "yahoo", "symbol": "AAPL"}
        )
        
        assert correlation_id is not None
        assert len(correlation_id) == 8
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Operation started: download_data" in call_args[0][0]
        assert correlation_id in call_args[0][0]
        
        operation_data = call_args[1]['extra']['operation_data']
        assert operation_data['operation'] == "download_data"
        assert operation_data['status'] == "started"
        assert operation_data['context'] == {"provider": "yahoo", "symbol": "AAPL"}
    
    def test_log_operation_start_with_existing_correlation_id(self):
        """Test operation start with existing correlation ID."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        existing_id = "existing-123"
        returned_id = error_logger.log_operation_start(
            operation="validate_data",
            correlation_id=existing_id
        )
        
        assert returned_id == existing_id
        
        call_args = mock_logger.info.call_args
        operation_data = call_args[1]['extra']['operation_data']
        assert operation_data['correlation_id'] == existing_id
    
    def test_log_operation_success(self):
        """Test operation success logging."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        error_logger.log_operation_success(
            operation="process_data",
            correlation_id="test-456",
            duration_ms=1234.5,
            context={"records_processed": 100}
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Operation completed: process_data" in call_args[0][0]
        assert "test-456" in call_args[0][0]
        
        operation_data = call_args[1]['extra']['operation_data']
        assert operation_data['operation'] == "process_data"
        assert operation_data['status'] == "completed"
        assert operation_data['duration_ms'] == 1234.5
        assert operation_data['context'] == {"records_processed": 100}
    
    def test_log_operation_success_no_duration(self):
        """Test operation success logging without duration."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        error_logger.log_operation_success(
            operation="simple_task",
            correlation_id="test-789"
        )
        
        call_args = mock_logger.info.call_args
        operation_data = call_args[1]['extra']['operation_data']
        assert 'duration_ms' not in operation_data
    
    def test_log_operation_failure(self):
        """Test operation failure logging."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        test_error = ConnectionError("Network timeout")
        error_logger.log_operation_failure(
            operation="fetch_remote_data",
            correlation_id="test-999",
            error=test_error,
            duration_ms=5000.0,
            context={"retry_count": 3}
        )
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Operation failed: fetch_remote_data" in call_args[0][0]
        assert "test-999" in call_args[0][0]
        
        operation_data = call_args[1]['extra']['operation_data']
        assert operation_data['operation'] == "fetch_remote_data"
        assert operation_data['status'] == "failed"
        assert operation_data['error_type'] == "ConnectionError"
        assert operation_data['error_message'] == "Network timeout"
        assert operation_data['duration_ms'] == 5000.0
        assert operation_data['context'] == {"retry_count": 3}
    
    def test_log_operation_failure_no_duration(self):
        """Test operation failure logging without duration."""
        mock_logger = Mock()
        error_logger = StructuredErrorLogger()
        error_logger.logger = mock_logger
        
        test_error = ValueError("Invalid input")
        error_logger.log_operation_failure(
            operation="validate_input",
            correlation_id="test-000",
            error=test_error
        )
        
        call_args = mock_logger.error.call_args
        operation_data = call_args[1]['extra']['operation_data']
        assert 'duration_ms' not in operation_data
    
    def test_generate_correlation_id(self):
        """Test correlation ID generation."""
        correlation_id = StructuredErrorLogger.generate_correlation_id()
        
        assert isinstance(correlation_id, str)
        assert len(correlation_id) == 8
        
        # Generate multiple IDs to ensure uniqueness (statistical test)
        ids = [StructuredErrorLogger.generate_correlation_id() for _ in range(10)]
        assert len(set(ids)) == 10  # All should be unique


class TestLoggingUtilsGlobalFunctions:
    """Test global logging utility functions."""
    
    @patch('vortex.utils.logging_utils._structured_logger')
    def test_get_structured_logger_existing_instance(self, mock_existing_logger):
        """Test get_structured_logger with existing instance."""
        mock_instance = Mock()
        mock_existing_logger = mock_instance
        
        # This will use the global variable directly
        import vortex.utils.logging_utils as utils_module
        utils_module._structured_logger = mock_instance
        
        result = get_structured_logger()
        assert result is mock_instance
    
    def test_get_structured_logger_new_instance(self):
        """Test get_structured_logger creates new instance."""
        # Reset global logger
        import vortex.utils.logging_utils as utils_module
        utils_module._structured_logger = None
        
        result = get_structured_logger()
        assert isinstance(result, StructuredErrorLogger)
        
        # Second call should return same instance
        result2 = get_structured_logger()
        assert result is result2
    
    @patch('vortex.utils.logging_utils.get_structured_logger')
    def test_log_error_with_context(self, mock_get_logger):
        """Test log_error_with_context convenience function."""
        mock_logger_instance = Mock()
        mock_logger_instance.log_error.return_value = "correlation-123"
        mock_get_logger.return_value = mock_logger_instance
        
        test_error = RuntimeError("Test error")
        result = log_error_with_context(
            error=test_error,
            message="Something failed",
            operation="test_operation",
            provider="test_provider",
            custom_field="custom_value"
        )
        
        assert result == "correlation-123"
        mock_get_logger.assert_called_once()
        mock_logger_instance.log_error.assert_called_once_with(
            test_error,
            "Something failed",
            context={
                "operation": "test_operation",
                "provider": "test_provider", 
                "custom_field": "custom_value"
            }
        )


class TestLoggingContextIntegration:
    """Integration tests for LoggingContext."""
    
    def test_nested_logging_contexts(self):
        """Test nested LoggingContext usage."""
        mock_logger = Mock()
        
        outer_context = LoggingContext(
            entry_msg="Outer start",
            success_msg="Outer success",
            logger=mock_logger
        )
        
        inner_context = LoggingContext(
            entry_msg="Inner start", 
            success_msg="Inner success",
            logger=mock_logger
        )
        
        with outer_context:
            with inner_context:
                pass  # Both contexts succeed
        
        # Should have 4 log calls total
        assert mock_logger.log.call_count == 4
        
        # Verify the order of calls
        call_messages = [call[0][1] for call in mock_logger.log.call_args_list]
        expected_messages = ["Outer start", "Inner start", "Inner success", "Outer success"]
        assert call_messages == expected_messages
    
    def test_logging_context_with_return_value(self):
        """Test LoggingContext doesn't interfere with return values."""
        mock_logger = Mock()
        context = LoggingContext(
            entry_msg="Processing",
            success_msg="Done",
            logger=mock_logger
        )
        
        def test_function():
            with context:
                return "test_result"
        
        result = test_function()
        assert result == "test_result"
        mock_logger.log.assert_called()


class TestLoggingUtilsEdgeCases:
    """Test edge cases for logging utilities."""
    
    def test_logging_context_exception_preservation(self):
        """Test that LoggingContext preserves the original exception."""
        mock_logger = Mock()
        context = LoggingContext(failure_msg="Failed", logger=mock_logger)
        
        original_exception = ValueError("Original error")
        
        with pytest.raises(ValueError) as exc_info:
            with context:
                raise original_exception
        
        # The exception should be the same object
        assert exc_info.value is original_exception
        
        # Should have logged the failure
        mock_logger.log.assert_called_with(logging.ERROR, "Failed")
    
    def test_logging_context_with_complex_logger_hierarchy(self):
        """Test LoggingContext with logger that has complex hierarchy."""
        # Create a logger with a complex name
        logger_name = "vortex.services.downloader.barchart"
        
        with patch('vortex.utils.logging_utils.logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            context = LoggingContext(entry_msg="Test", logger=None)  # Use default
            
            # Should get logger for the module
            mock_get_logger.assert_called_once_with('vortex.utils.logging_utils')
            assert context.logger == mock_logger