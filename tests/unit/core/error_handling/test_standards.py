"""
Tests for core error handling standards module.

Provides comprehensive coverage for standardized error handling patterns,
decorators, and mixin classes used throughout the Vortex codebase.
"""

import logging
import pytest
from unittest.mock import MagicMock, patch, call
from typing import Any

import click

from vortex.core.error_handling.standards import (
    ErrorCategories,
    standard_error_handler,
    safe_operation,
    validation_error_handler,
    provider_operation_handler,
    cli_command_handler,
    ErrorHandlingMixin
)
from vortex.exceptions.base import VortexError
from vortex.exceptions.providers import DataProviderError, AuthenticationError
from vortex.exceptions.config import ConfigurationError, ConfigurationValidationError
from vortex.exceptions.storage import DataStorageError, VortexPermissionError


class TestErrorCategories:
    """Test error categorization constants."""
    
    def test_expected_errors_tuple(self):
        """Test that expected errors tuple contains standard Python exceptions."""
        assert ValueError in ErrorCategories.EXPECTED_ERRORS
        assert TypeError in ErrorCategories.EXPECTED_ERRORS
        assert KeyError in ErrorCategories.EXPECTED_ERRORS
        assert FileNotFoundError in ErrorCategories.EXPECTED_ERRORS
        assert PermissionError in ErrorCategories.EXPECTED_ERRORS
    
    def test_vortex_expected_errors_tuple(self):
        """Test that Vortex expected errors contain custom exceptions."""
        assert ConfigurationError in ErrorCategories.VORTEX_EXPECTED_ERRORS
        assert ConfigurationValidationError in ErrorCategories.VORTEX_EXPECTED_ERRORS
        assert DataProviderError in ErrorCategories.VORTEX_EXPECTED_ERRORS
        assert DataStorageError in ErrorCategories.VORTEX_EXPECTED_ERRORS
        assert VortexPermissionError in ErrorCategories.VORTEX_EXPECTED_ERRORS
    
    def test_non_retryable_errors_tuple(self):
        """Test that non-retryable errors are properly categorized."""
        assert AuthenticationError in ErrorCategories.NON_RETRYABLE_ERRORS
        assert PermissionError in ErrorCategories.NON_RETRYABLE_ERRORS
        assert VortexPermissionError in ErrorCategories.NON_RETRYABLE_ERRORS
    
    def test_all_expected_errors_union(self):
        """Test that all expected errors combines both tuples."""
        expected_count = len(ErrorCategories.EXPECTED_ERRORS) + len(ErrorCategories.VORTEX_EXPECTED_ERRORS)
        assert len(ErrorCategories.ALL_EXPECTED_ERRORS) == expected_count
        
        # Check that all individual errors are present
        for error in ErrorCategories.EXPECTED_ERRORS:
            assert error in ErrorCategories.ALL_EXPECTED_ERRORS
        for error in ErrorCategories.VORTEX_EXPECTED_ERRORS:
            assert error in ErrorCategories.ALL_EXPECTED_ERRORS


class TestStandardErrorHandler:
    """Test standard error handler decorator."""
    
    def test_decorator_with_successful_function(self, caplog):
        """Test decorator allows successful function execution."""
        @standard_error_handler("test_operation")
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert len(caplog.records) == 0
    
    def test_decorator_with_expected_error(self, caplog):
        """Test decorator handles expected errors correctly."""
        caplog.set_level(logging.WARNING)
        
        @standard_error_handler("test_operation")
        def failing_func():
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            failing_func()
        
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "test_operation failed with expected error" in caplog.records[0].message
    
    def test_decorator_with_unexpected_error_reraise(self, caplog):
        """Test decorator handles unexpected errors with reraise."""
        caplog.set_level(logging.ERROR)
        
        @standard_error_handler("test_operation", reraise_unexpected=True)
        def failing_func():
            raise RuntimeError("unexpected error")
        
        with pytest.raises(RuntimeError):
            failing_func()
        
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert "test_operation failed with unexpected error" in caplog.records[0].message
    
    def test_decorator_with_unexpected_error_no_reraise(self, caplog):
        """Test decorator handles unexpected errors without reraise."""
        caplog.set_level(logging.ERROR)
        
        @standard_error_handler("test_operation", reraise_unexpected=False)
        def failing_func():
            raise RuntimeError("unexpected error")
        
        result = failing_func()
        assert result is None
        
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
    
    def test_decorator_with_custom_expected_errors(self, caplog):
        """Test decorator with custom expected error types."""
        caplog.set_level(logging.WARNING)
        
        @standard_error_handler("test_operation", expected_errors=(RuntimeError,))
        def failing_func():
            raise RuntimeError("custom expected error")
        
        with pytest.raises(RuntimeError):
            failing_func()
        
        assert len(caplog.records) == 1
        assert "test_operation failed with expected error" in caplog.records[0].message
    
    def test_decorator_with_no_logging_unexpected(self, caplog):
        """Test decorator without logging unexpected errors."""
        @standard_error_handler("test_operation", log_unexpected=False)
        def failing_func():
            raise RuntimeError("unexpected error")
        
        with pytest.raises(RuntimeError):
            failing_func()
        
        assert len(caplog.records) == 0


class TestSafeOperation:
    """Test safe operation decorator."""
    
    def test_successful_operation(self):
        """Test safe operation with successful function."""
        @safe_operation("test_operation", default_return="default")
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"
    
    def test_expected_error_returns_default(self, caplog):
        """Test safe operation returns default on expected error."""
        caplog.set_level(logging.WARNING)
        
        @safe_operation("test_operation", default_return="default")
        def failing_func():
            raise ValueError("test error")
        
        result = failing_func()
        assert result == "default"
        
        assert len(caplog.records) == 1
        assert "test_operation failed (expected)" in caplog.records[0].message
    
    def test_unexpected_error_returns_default(self, caplog):
        """Test safe operation returns default on unexpected error."""
        caplog.set_level(logging.ERROR)
        
        @safe_operation("test_operation", default_return="default")
        def failing_func():
            raise RuntimeError("unexpected error")
        
        result = failing_func()
        assert result == "default"
        
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert "test_operation failed (unexpected)" in caplog.records[0].message
    
    def test_custom_log_level(self, caplog):
        """Test safe operation with custom log level."""
        caplog.set_level(logging.INFO)
        
        @safe_operation("test_operation", default_return="default", log_level="info")
        def failing_func():
            raise ValueError("test error")
        
        result = failing_func()
        assert result == "default"
        
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "INFO"
    
    def test_custom_default_return(self):
        """Test safe operation with custom default return value."""
        @safe_operation("test_operation", default_return=42)
        def failing_func():
            raise ValueError("test error")
        
        result = failing_func()
        assert result == 42


class TestValidationErrorHandler:
    """Test validation error handler decorator."""
    
    def test_successful_validation(self):
        """Test validation handler with successful function."""
        @validation_error_handler("test_field")
        def successful_validation():
            return "valid"
        
        result = successful_validation()
        assert result == "valid"
    
    def test_value_error_converted_to_validation_error(self, caplog):
        """Test ValueError converted to ConfigurationValidationError."""
        caplog.set_level(logging.INFO)
        
        @validation_error_handler("test_field")
        def failing_validation():
            raise ValueError("invalid value")
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            failing_validation()
        
        assert "Invalid test_field: invalid value" in str(exc_info.value)
        assert len(caplog.records) == 1
        assert "Validation failed for test_field" in caplog.records[0].message
    
    def test_type_error_converted_to_validation_error(self, caplog):
        """Test TypeError converted to ConfigurationValidationError."""
        caplog.set_level(logging.INFO)
        
        @validation_error_handler("test_field")
        def failing_validation():
            raise TypeError("wrong type")
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            failing_validation()
        
        assert "Invalid test_field: wrong type" in str(exc_info.value)
        assert len(caplog.records) == 1
    
    def test_unexpected_error_converted_to_validation_error(self, caplog):
        """Test unexpected error converted to ConfigurationValidationError."""
        caplog.set_level(logging.ERROR)
        
        @validation_error_handler("test_field")
        def failing_validation():
            raise RuntimeError("unexpected error")
        
        with pytest.raises(ConfigurationValidationError) as exc_info:
            failing_validation()
        
        assert "Validation error for test_field: unexpected error" in str(exc_info.value)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"


class TestProviderOperationHandler:
    """Test provider operation handler decorator."""
    
    def test_successful_provider_operation(self):
        """Test provider handler with successful function."""
        @provider_operation_handler("test_provider")
        def successful_operation():
            return "success"
        
        result = successful_operation()
        assert result == "success"
    
    def test_data_provider_error_reraised(self):
        """Test DataProviderError is re-raised as-is."""
        @provider_operation_handler("test_provider")
        def failing_operation():
            raise DataProviderError("test_provider", "test error")
        
        with pytest.raises(DataProviderError):
            failing_operation()
    
    def test_authentication_error_reraised(self):
        """Test AuthenticationError is re-raised as-is."""
        @provider_operation_handler("test_provider")
        def failing_operation():
            raise AuthenticationError("test_provider", "auth failed")
        
        with pytest.raises(AuthenticationError):
            failing_operation()
    
    def test_value_error_converted_to_provider_error(self, caplog):
        """Test ValueError converted to DataProviderError."""
        caplog.set_level(logging.WARNING)
        
        @provider_operation_handler("test_provider")
        def failing_operation():
            raise ValueError("invalid value")
        
        with pytest.raises(DataProviderError) as exc_info:
            failing_operation()
        
        assert "Operation failed: invalid value" in str(exc_info.value)
        assert len(caplog.records) == 1
        assert "Provider test_provider operation failed" in caplog.records[0].message
    
    def test_unexpected_error_converted_to_provider_error(self, caplog):
        """Test unexpected error converted to DataProviderError."""
        caplog.set_level(logging.ERROR)
        
        @provider_operation_handler("test_provider")
        def failing_operation():
            raise RuntimeError("unexpected error")
        
        with pytest.raises(DataProviderError) as exc_info:
            failing_operation()
        
        assert "Unexpected error: unexpected error" in str(exc_info.value)
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"


class TestCLICommandHandler:
    """Test CLI command handler decorator."""
    
    def test_successful_cli_command(self):
        """Test CLI handler with successful function."""
        @cli_command_handler("test_command")
        def successful_command():
            return "success"
        
        result = successful_command()
        assert result == "success"
    
    def test_keyboard_interrupt_converted_to_click_abort(self, caplog):
        """Test KeyboardInterrupt converted to click.Abort."""
        caplog.set_level(logging.INFO)
        
        @cli_command_handler("test_command")
        def interrupted_command():
            raise KeyboardInterrupt()
        
        with pytest.raises(click.Abort):
            interrupted_command()
        
        assert len(caplog.records) == 1
        assert "CLI command 'test_command' cancelled by user" in caplog.records[0].message
    
    def test_vortex_error_logged_and_reraised(self, caplog):
        """Test VortexError is logged and re-raised."""
        caplog.set_level(logging.ERROR)
        
        from vortex.exceptions.base import ExceptionContext
        context = ExceptionContext(correlation_id="test-123")
        vortex_error = VortexError("test error", context=context)
        
        @cli_command_handler("test_command")
        def failing_command():
            raise vortex_error
        
        with pytest.raises(VortexError):
            failing_command()
        
        assert len(caplog.records) == 1
        assert "CLI command 'test_command' failed: test error" in caplog.records[0].message
    
    def test_unexpected_error_converted_to_click_abort(self, caplog):
        """Test unexpected error converted to click.Abort."""
        caplog.set_level(logging.ERROR)
        
        @cli_command_handler("test_command")
        def failing_command():
            raise RuntimeError("unexpected error")
        
        with pytest.raises(click.Abort):
            failing_command()
        
        assert len(caplog.records) == 1
        assert "Unexpected error in CLI command 'test_command'" in caplog.records[0].message


class TestErrorHandlingMixin:
    """Test ErrorHandlingMixin class."""
    
    def test_mixin_initialization_default_name(self):
        """Test mixin initialization with default component name."""
        class TestClass(ErrorHandlingMixin):
            pass
        
        instance = TestClass()
        assert instance.component_name == "TestClass"
        assert instance.logger is not None
    
    def test_mixin_initialization_custom_name(self):
        """Test mixin initialization with custom component name."""
        class TestClass(ErrorHandlingMixin):
            pass
        
        instance = TestClass(component_name="CustomName")
        assert instance.component_name == "CustomName"
    
    def test_handle_expected_error(self, caplog):
        """Test expected error handling."""
        caplog.set_level(logging.WARNING)
        
        class TestClass(ErrorHandlingMixin):
            pass
        
        instance = TestClass("TestComponent")
        error = ValueError("test error")
        
        instance.handle_expected_error(error, "test_operation")
        
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
        assert "TestComponent test_operation failed: test error" in caplog.records[0].message
    
    def test_handle_unexpected_error(self, caplog):
        """Test unexpected error handling."""
        caplog.set_level(logging.ERROR)
        
        class TestClass(ErrorHandlingMixin):
            pass
        
        instance = TestClass("TestComponent")
        error = RuntimeError("unexpected error")
        
        instance.handle_unexpected_error(error, "test_operation")
        
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
        assert "TestComponent test_operation unexpected error" in caplog.records[0].message
    
    def test_safe_execute_successful(self):
        """Test safe execute with successful function."""
        class TestClass(ErrorHandlingMixin):
            pass
        
        instance = TestClass()
        
        def successful_func():
            return "success"
        
        result = instance.safe_execute("test_operation", successful_func, "default")
        assert result == "success"
    
    def test_safe_execute_expected_error_returns_default(self, caplog):
        """Test safe execute returns default on expected error."""
        caplog.set_level(logging.WARNING)
        
        class TestClass(ErrorHandlingMixin):
            pass
        
        instance = TestClass()
        
        def failing_func():
            raise ValueError("test error")
        
        result = instance.safe_execute("test_operation", failing_func, "default")
        assert result == "default"
        
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "WARNING"
    
    def test_safe_execute_unexpected_error_returns_default(self, caplog):
        """Test safe execute returns default on unexpected error."""
        caplog.set_level(logging.ERROR)
        
        class TestClass(ErrorHandlingMixin):
            pass
        
        instance = TestClass()
        
        def failing_func():
            raise RuntimeError("unexpected error")
        
        result = instance.safe_execute("test_operation", failing_func, "default")
        assert result == "default"
        
        assert len(caplog.records) == 1
        assert caplog.records[0].levelname == "ERROR"
    
    def test_safe_execute_none_default(self):
        """Test safe execute with None as default."""
        class TestClass(ErrorHandlingMixin):
            pass
        
        instance = TestClass()
        
        def failing_func():
            raise ValueError("test error")
        
        result = instance.safe_execute("test_operation", failing_func)
        assert result is None


class TestErrorHandlerIntegration:
    """Integration tests for error handler combinations."""
    
    def test_nested_decorators(self, caplog):
        """Test multiple error decorators can be nested."""
        caplog.set_level(logging.WARNING)
        
        @standard_error_handler("outer_operation")
        @safe_operation("inner_operation", default_return="safe_default")
        def nested_func():
            raise ValueError("test error")
        
        # The safe_operation decorator should catch the error and return default
        # The standard_error_handler should not catch anything
        result = nested_func()
        assert result == "safe_default"
    
    def test_decorator_preserves_function_metadata(self):
        """Test decorators preserve original function metadata."""
        @standard_error_handler("test_operation")
        def original_func():
            """Original docstring."""
            return "original"
        
        assert original_func.__name__ == "original_func"
        assert original_func.__doc__ == "Original docstring."
    
    def test_error_context_information(self, caplog):
        """Test that error context includes proper operation and error type info."""
        caplog.set_level(logging.WARNING)
        
        @standard_error_handler("context_test")
        def context_func():
            raise KeyError("missing key")
        
        with pytest.raises(KeyError):
            context_func()
        
        record = caplog.records[0]
        # Check that structured logging data is in the extra field
        assert hasattr(record, 'operation')
        assert record.operation == "context_test"
        assert hasattr(record, 'error_type')
        assert record.error_type == "KeyError"
        assert hasattr(record, 'error_message')
        assert record.error_message == "'missing key'"


class TestErrorHandlerEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_operation_name(self, caplog):
        """Test decorators handle empty operation names."""
        caplog.set_level(logging.WARNING)
        
        @standard_error_handler("")
        def empty_name_func():
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            empty_name_func()
        
        assert len(caplog.records) == 1
        assert " failed with expected error" in caplog.records[0].message
    
    def test_mixin_with_none_component_name(self):
        """Test mixin handles None component name gracefully."""
        class TestClass(ErrorHandlingMixin):
            pass
        
        instance = TestClass(component_name=None)
        assert instance.component_name == "TestClass"  # Falls back to class name
    
    def test_safe_operation_with_function_returning_none(self):
        """Test safe operation when function legitimately returns None."""
        @safe_operation("test_operation", default_return="default")
        def none_returning_func():
            return None
        
        result = none_returning_func()
        assert result is None  # Should return the actual None, not default
    
    def test_decorator_with_args_and_kwargs(self):
        """Test decorators work with functions that have arguments."""
        @standard_error_handler("test_operation")
        def func_with_args(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"
        
        result = func_with_args("a", "b", kwarg1="c")
        assert result == "a-b-c"
    
    def test_provider_handler_with_function_metadata(self, caplog):
        """Test provider handler includes function name in logs."""
        caplog.set_level(logging.WARNING)
        
        @provider_operation_handler("test_provider")
        def specific_operation():
            raise ValueError("test error")
        
        with pytest.raises(DataProviderError):
            specific_operation()
        
        record = caplog.records[0]
        assert hasattr(record, 'operation')
        assert record.operation == "specific_operation"