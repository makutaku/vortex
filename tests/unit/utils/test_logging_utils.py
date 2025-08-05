"""Tests for logging utilities."""

import pytest
import logging
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from vortex.utils.logging_utils import (
    init_logging, LoggingContext, StructuredErrorLogger
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