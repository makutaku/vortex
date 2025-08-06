"""Tests for logging context management."""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from functools import wraps

from vortex.logging.context import logged, LoggingContext
from vortex.logging.loggers import VortexLogger


class TestLoggedDecorator:
    """Test the @logged decorator."""
    
    def test_logged_decorator_default_level(self):
        """Test logged decorator with default info level."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            @logged()
            def test_function():
                return "success"
            
            result = test_function()
        
        assert result == "success"
        assert mock_logger.info.call_count == 2  # Entry and exit calls
        mock_logger.info.assert_any_call("Calling test_function", function="test_function")
        mock_logger.info.assert_any_call("Completed test_function", function="test_function")
    
    def test_logged_decorator_custom_level(self):
        """Test logged decorator with custom log level."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            @logged(level="debug")
            def test_function():
                return "debug_success"
            
            result = test_function()
        
        assert result == "debug_success"
        assert mock_logger.debug.call_count == 2
        mock_logger.debug.assert_any_call("Calling test_function", function="test_function")
        mock_logger.debug.assert_any_call("Completed test_function", function="test_function")
    
    def test_logged_decorator_custom_logger(self):
        """Test logged decorator with custom logger provided."""
        custom_logger = Mock(spec=VortexLogger)
        
        @logged(logger=custom_logger)
        def test_function():
            return "custom_success"
        
        result = test_function()
        
        assert result == "custom_success"
        assert custom_logger.info.call_count == 2
        custom_logger.info.assert_any_call("Calling test_function", function="test_function")
        custom_logger.info.assert_any_call("Completed test_function", function="test_function")
    
    def test_logged_decorator_with_exception(self):
        """Test logged decorator handling exceptions."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            @logged()
            def failing_function():
                raise ValueError("Test error")
            
            with pytest.raises(ValueError, match="Test error"):
                failing_function()
        
        # Should log entry and error, but not completion
        mock_logger.info.assert_called_once_with("Calling failing_function", function="failing_function")
        mock_logger.error.assert_called_once_with("Failed failing_function: Test error", function="failing_function")
    
    def test_logged_decorator_with_args_kwargs(self):
        """Test logged decorator preserves function arguments."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            @logged()
            def function_with_args(a, b, c=None, d="default"):
                return f"{a}-{b}-{c}-{d}"
            
            result = function_with_args("arg1", "arg2", c="kwarg1", d="kwarg2")
        
        assert result == "arg1-arg2-kwarg1-kwarg2"
        assert mock_logger.info.call_count == 2
    
    def test_logged_decorator_preserves_function_metadata(self):
        """Test that logged decorator preserves original function metadata."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            @logged()
            def original_function():
                """Original function docstring."""
                pass
            
            assert original_function.__name__ == "original_function"
            assert original_function.__doc__ == "Original function docstring."


class TestLoggingContext:
    """Test LoggingContext context manager."""
    
    def test_logging_context_success_flow(self):
        """Test LoggingContext with successful execution."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            with LoggingContext(
                entry_msg="Starting operation",
                success_msg="Operation completed",
                failure_msg="Operation failed"
            ):
                # Simulate successful operation
                pass
        
        mock_logger.debug.assert_called_once_with("Starting operation")
        mock_logger.info.assert_called_once_with("Operation completed")
        assert not mock_logger.error.called
    
    def test_logging_context_failure_flow(self):
        """Test LoggingContext with exception handling."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            with pytest.raises(ValueError):
                with LoggingContext(
                    entry_msg="Starting risky operation",
                    success_msg="Risky operation completed",
                    failure_msg="Risky operation failed"
                ):
                    raise ValueError("Something went wrong")
        
        mock_logger.debug.assert_called_once_with("Starting risky operation")
        mock_logger.error.assert_called_once_with("Risky operation failed")
        assert not mock_logger.info.called
    
    def test_logging_context_custom_logger(self):
        """Test LoggingContext with custom VortexLogger."""
        custom_logger = Mock(spec=VortexLogger)
        
        with LoggingContext(
            entry_msg="Custom logger test",
            success_msg="Success with custom logger",
            logger=custom_logger
        ):
            pass
        
        custom_logger.debug.assert_called_once_with("Custom logger test")
        custom_logger.info.assert_called_once_with("Success with custom logger")
    
    def test_logging_context_standard_logger_conversion(self):
        """Test LoggingContext converts standard logger to VortexLogger."""
        standard_logger = logging.getLogger("test.module")
        mock_vortex_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_vortex_logger
            
            with LoggingContext(
                entry_msg="Standard logger test",
                logger=standard_logger
            ):
                pass
        
        mock_manager.get_logger.assert_called_once_with("test.module")
        mock_vortex_logger.debug.assert_called_once_with("Standard logger test")
    
    def test_logging_context_custom_levels(self):
        """Test LoggingContext with custom log levels."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            with LoggingContext(
                entry_msg="Custom levels test",
                success_msg="Success with custom levels",
                entry_level=logging.INFO,
                success_level=logging.WARNING
            ):
                pass
        
        mock_logger.info.assert_called_once_with("Custom levels test")
        mock_logger.warning.assert_called_once_with("Success with custom levels")
    
    def test_logging_context_no_messages(self):
        """Test LoggingContext with no messages configured."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            with LoggingContext():
                pass
        
        # No messages should be logged
        assert not mock_logger.debug.called
        assert not mock_logger.info.called
        assert not mock_logger.error.called
    
    def test_logging_context_entry_only(self):
        """Test LoggingContext with only entry message."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            with LoggingContext(entry_msg="Only entry message"):
                pass
        
        mock_logger.debug.assert_called_once_with("Only entry message")
        assert not mock_logger.info.called
        assert not mock_logger.error.called
    
    def test_logging_context_failure_only(self):
        """Test LoggingContext with only failure message on exception."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            with pytest.raises(RuntimeError):
                with LoggingContext(failure_msg="Only failure message"):
                    raise RuntimeError("Test error")
        
        mock_logger.error.assert_called_once_with("Only failure message")
        assert not mock_logger.debug.called
        assert not mock_logger.info.called
    
    def test_logging_context_return_self(self):
        """Test LoggingContext returns itself from __enter__."""
        with LoggingContext() as context:
            assert isinstance(context, LoggingContext)
    
    def test_logging_context_level_name_handling(self):
        """Test LoggingContext properly handles log level names."""
        mock_logger = Mock(spec=VortexLogger)
        
        with patch('vortex.logging.context.logging_manager') as mock_manager:
            mock_manager.get_logger.return_value = mock_logger
            
            # Test with different level constants
            with LoggingContext(
                entry_msg="Testing levels",
                success_msg="Success message", 
                entry_level=logging.CRITICAL,
                success_level=logging.DEBUG
            ):
                pass
        
        # Should call appropriate methods based on level
        mock_logger.critical.assert_called_once_with("Testing levels")
        mock_logger.debug.assert_called_once_with("Success message")