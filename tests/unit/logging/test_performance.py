"""
Comprehensive unit tests for Performance logging module.

Tests all aspects of performance logging including PerformanceLogger,
TimedOperation, and the @timed decorator for complete coverage.
"""

import time
import pytest
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
from uuid import uuid4

from vortex.logging.performance import (
    PerformanceLogger, TimedOperation, get_performance_logger, timed
)
from vortex.logging.loggers import VortexLogger


class TestPerformanceLogger:
    """Test PerformanceLogger class functionality."""
    
    def test_logger_initialization(self):
        """Test PerformanceLogger initialization."""
        perf_logger = PerformanceLogger("test.module")
        
        assert perf_logger.logger.logger.name == "test.module.performance"
        assert isinstance(perf_logger.logger, VortexLogger)
    
    def test_logger_initialization_with_correlation_id(self):
        """Test PerformanceLogger initialization with correlation ID."""
        correlation_id = str(uuid4())
        perf_logger = PerformanceLogger("test.module", correlation_id)
        
        assert perf_logger.logger.logger.name == "test.module.performance"
        assert isinstance(perf_logger.logger, VortexLogger)
    
    @patch('vortex.logging.performance.get_logger')
    def test_time_operation_basic(self, mock_get_logger):
        """Test basic operation timing logging."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        perf_logger.time_operation("test_operation", 123.45)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        # Check message format
        assert "Operation 'test_operation' completed in 123.45ms" in call_args[0][0]
        
        # Check structured data
        assert call_args[1]['operation'] == "test_operation"
        assert call_args[1]['duration'] == 123.45
    
    @patch('vortex.logging.performance.get_logger')
    def test_time_operation_with_context(self, mock_get_logger):
        """Test operation timing with additional context."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        context = {"user_id": "123", "endpoint": "/api/data", "method": "GET"}
        perf_logger.time_operation("api_call", 500.0, **context)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        # Check message includes context
        message = call_args[0][0]
        assert "Operation 'api_call' completed in 500.00ms" in message
        assert "user_id=123" in message
        assert "endpoint=/api/data" in message
        assert "method=GET" in message
        
        # Check structured data includes context
        kwargs = call_args[1]
        assert kwargs['operation'] == "api_call"
        assert kwargs['duration'] == 500.0
        assert kwargs['user_id'] == "123"
        assert kwargs['endpoint'] == "/api/data"
        assert kwargs['method'] == "GET"
    
    @patch('vortex.logging.performance.get_logger')
    def test_time_operation_no_context(self, mock_get_logger):
        """Test operation timing without additional context."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        perf_logger.time_operation("simple_operation", 50.25)
        
        call_args = mock_logger.info.call_args
        message = call_args[0][0]
        
        # Should not contain context parentheses when no context provided
        assert "Operation 'simple_operation' completed in 50.25ms" == message.strip()
        assert "(" not in message  # No context parentheses
    
    def test_start_operation(self):
        """Test starting a timed operation."""
        perf_logger = PerformanceLogger("test")
        context = {"session": "abc123"}
        
        timed_op = perf_logger.start_operation("background_task", **context)
        
        assert isinstance(timed_op, TimedOperation)
        assert timed_op.operation == "background_task"
        assert timed_op.context == context
        assert timed_op.start_time is None  # Not started yet
    
    @patch('vortex.logging.performance.get_logger')
    def test_log_metric(self, mock_get_logger):
        """Test logging performance metrics."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        perf_logger.log_metric("response_time", 125.5, endpoint="/api/users")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        assert call_args[0][0] == "Metric response_time: 125.5"
        assert call_args[1]['metric'] == "response_time"
        assert call_args[1]['value'] == 125.5
        assert call_args[1]['endpoint'] == "/api/users"
    
    @patch('vortex.logging.performance.get_logger')
    def test_log_metric_without_context(self, mock_get_logger):
        """Test logging metrics without additional context."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        perf_logger.log_metric("cpu_usage", 85.2)
        
        call_args = mock_logger.info.call_args
        
        assert call_args[0][0] == "Metric cpu_usage: 85.2"
        assert call_args[1]['metric'] == "cpu_usage"
        assert call_args[1]['value'] == 85.2
        # Should only have metric and value keys
        assert len(call_args[1]) == 2
    
    @patch('vortex.logging.performance.get_logger')
    def test_log_counter(self, mock_get_logger):
        """Test logging performance counters."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        perf_logger.log_counter("processed_items", 1500, batch_id="batch_42")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        assert call_args[0][0] == "Counter processed_items: 1500"
        assert call_args[1]['counter'] == "processed_items"
        assert call_args[1]['count'] == 1500
        assert call_args[1]['batch_id'] == "batch_42"
    
    @patch('vortex.logging.performance.get_logger')
    def test_log_counter_without_context(self, mock_get_logger):
        """Test logging counters without additional context."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        perf_logger.log_counter("error_count", 3)
        
        call_args = mock_logger.info.call_args
        
        assert call_args[0][0] == "Counter error_count: 3"
        assert call_args[1]['counter'] == "error_count"
        assert call_args[1]['count'] == 3
        assert len(call_args[1]) == 2  # Only counter and count keys


class TestTimedOperation:
    """Test TimedOperation context manager."""
    
    @patch('vortex.logging.performance.get_logger')
    def test_timed_operation_basic_initialization(self, mock_get_logger):
        """Test basic TimedOperation initialization."""
        mock_logger = Mock(spec=VortexLogger)
        
        timed_op = TimedOperation("test_operation", mock_logger, {"key": "value"})
        
        assert timed_op.operation == "test_operation"
        assert timed_op.logger == mock_logger
        assert timed_op.context == {"key": "value"}
        assert timed_op.start_time is None
    
    @patch('vortex.logging.performance.get_logger')
    def test_timed_operation_dict_as_second_param(self, mock_get_logger):
        """Test TimedOperation when dict is passed as second parameter (legacy interface)."""
        mock_vortex_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_vortex_logger
        
        context = {"session": "test123"}
        timed_op = TimedOperation("test_operation", context)
        
        assert timed_op.operation == "test_operation"
        assert timed_op.context == context
        assert timed_op.logger == mock_vortex_logger
        mock_get_logger.assert_called_once_with("performance.test_operation")
    
    @patch('vortex.logging.performance.get_logger')
    def test_timed_operation_no_logger_provided(self, mock_get_logger):
        """Test TimedOperation when no logger is provided."""
        mock_vortex_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_vortex_logger
        
        timed_op = TimedOperation("test_operation", None, {"key": "value"})
        
        assert timed_op.operation == "test_operation"
        assert timed_op.context == {"key": "value"}
        assert timed_op.logger == mock_vortex_logger
        mock_get_logger.assert_called_once_with("performance.test_operation")
    
    @patch('vortex.logging.performance.get_logger')
    def test_timed_operation_context_defaults(self, mock_get_logger):
        """Test TimedOperation with default empty context."""
        mock_logger = Mock(spec=VortexLogger)
        
        timed_op = TimedOperation("test_operation", mock_logger)
        
        assert timed_op.operation == "test_operation"
        assert timed_op.logger == mock_logger
        assert timed_op.context == {}
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_context_manager_successful_operation(self, mock_get_logger, mock_perf_counter):
        """Test successful operation timing with context manager."""
        mock_logger = Mock(spec=VortexLogger)
        mock_perf_counter.side_effect = [1000.0, 1000.123]  # Start and end times
        
        timed_op = TimedOperation("test_operation", mock_logger, {"user": "test"})
        
        with timed_op:
            pass  # Simulate work
        
        # Check debug log on entry
        mock_logger.debug.assert_called_once_with(
            "Starting operation: test_operation",
            user="test"
        )
        
        # Check info log on successful exit
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        assert "Completed operation: test_operation in 123.00ms" in call_args[0][0]
        assert call_args[1]['operation'] == "test_operation"
        assert abs(call_args[1]['duration'] - 123.0) < 0.001  # (1000.123 - 1000.0) * 1000
        assert call_args[1]['status'] == "success"
        assert call_args[1]['user'] == "test"
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_context_manager_failed_operation(self, mock_get_logger, mock_perf_counter):
        """Test failed operation timing with context manager."""
        mock_logger = Mock(spec=VortexLogger)
        mock_perf_counter.side_effect = [1000.0, 1000.250]  # Start and end times
        
        timed_op = TimedOperation("test_operation", mock_logger, {"batch": "42"})
        
        # Test exception handling
        test_exception = ValueError("Test error")
        
        with pytest.raises(ValueError):
            with timed_op:
                raise test_exception
        
        # Check debug log on entry
        mock_logger.debug.assert_called_once_with(
            "Starting operation: test_operation",
            batch="42"
        )
        
        # Check error log on failed exit
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        
        assert "Failed operation: test_operation after 250.00ms: Test error" in call_args[0][0]
        assert call_args[1]['operation'] == "test_operation"
        assert call_args[1]['duration'] == 250.0  # (1000.250 - 1000.0) * 1000
        assert call_args[1]['status'] == "failed"
        assert call_args[1]['error_type'] == "ValueError"
        assert call_args[1]['batch'] == "42"
    
    @patch('vortex.logging.performance.get_logger')
    def test_context_manager_no_start_time(self, mock_get_logger):
        """Test context manager exit when start_time is None."""
        mock_logger = Mock(spec=VortexLogger)
        
        timed_op = TimedOperation("test_operation", mock_logger)
        timed_op.start_time = None  # Simulate start_time not set
        
        # Exit should handle None start_time gracefully
        timed_op.__exit__(None, None, None)
        
        # No logging should occur
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_context_manager_exception_types(self, mock_get_logger, mock_perf_counter):
        """Test context manager with different exception types."""
        mock_logger = Mock(spec=VortexLogger)
        mock_perf_counter.side_effect = [1000.0, 1000.100]
        
        timed_op = TimedOperation("test_operation", mock_logger)
        
        # Test with RuntimeError
        with pytest.raises(RuntimeError):
            with timed_op:
                raise RuntimeError("Runtime issue")
        
        call_args = mock_logger.error.call_args
        assert call_args[1]['error_type'] == "RuntimeError"
        
        # Reset mock for next test
        mock_logger.reset_mock()
        mock_perf_counter.side_effect = [2000.0, 2000.200]
        timed_op = TimedOperation("test_operation2", mock_logger)
        
        # Test with custom exception
        class CustomError(Exception):
            pass
        
        with pytest.raises(CustomError):
            with timed_op:
                raise CustomError("Custom issue")
        
        call_args = mock_logger.error.call_args
        assert call_args[1]['error_type'] == "CustomError"


class TestGetPerformanceLogger:
    """Test get_performance_logger factory function."""
    
    def test_get_performance_logger_basic(self):
        """Test basic get_performance_logger factory."""
        perf_logger = get_performance_logger("test.module")
        
        assert isinstance(perf_logger, PerformanceLogger)
        assert perf_logger.logger.logger.name == "test.module.performance"
    
    def test_get_performance_logger_with_correlation_id(self):
        """Test get_performance_logger with correlation ID."""
        correlation_id = str(uuid4())
        perf_logger = get_performance_logger("test.module", correlation_id)
        
        assert isinstance(perf_logger, PerformanceLogger)
        assert perf_logger.logger.logger.name == "test.module.performance"


class TestTimedDecorator:
    """Test @timed decorator functionality."""
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_timed_decorator_successful_function(self, mock_get_logger, mock_perf_counter):
        """Test @timed decorator on successful function execution."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        mock_perf_counter.side_effect = [1000.0, 1000.150]
        
        @timed()
        def sample_function(x, y):
            return x + y
        
        result = sample_function(2, 3)
        
        assert result == 5
        
        # Check logger creation
        expected_module = sample_function.__module__
        mock_get_logger.assert_called_once_with(f"{expected_module}.performance")
        
        # Check timing log
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        expected_op_name = f"{expected_module}.sample_function"
        assert f"Function '{expected_op_name}' completed in 150.00ms" in call_args[0][0]
        assert call_args[1]['operation'] == expected_op_name
        assert abs(call_args[1]['duration'] - 150.0) < 0.001
        assert call_args[1]['status'] == "success"
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_timed_decorator_failed_function(self, mock_get_logger, mock_perf_counter):
        """Test @timed decorator on function that raises exception."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        mock_perf_counter.side_effect = [1000.0, 1000.075]
        
        @timed()
        def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            failing_function()
        
        # Check error log
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        
        expected_module = failing_function.__module__
        expected_op_name = f"{expected_module}.failing_function"
        assert f"Function '{expected_op_name}' failed after 75.00ms: Test error" in call_args[0][0]
        assert call_args[1]['operation'] == expected_op_name
        assert abs(call_args[1]['duration'] - 75.0) < 0.001
        assert call_args[1]['status'] == "failed"
        assert call_args[1]['error_type'] == "ValueError"
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_timed_decorator_custom_operation_name(self, mock_get_logger, mock_perf_counter):
        """Test @timed decorator with custom operation name."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        mock_perf_counter.side_effect = [1000.0, 1000.200]
        
        @timed(operation="custom_operation_name")
        def sample_function():
            return "success"
        
        result = sample_function()
        assert result == "success"
        
        # Check timing log uses custom name
        call_args = mock_logger.info.call_args
        assert "Function 'custom_operation_name' completed in 200.00ms" in call_args[0][0]
        assert call_args[1]['operation'] == "custom_operation_name"
    
    @patch('time.perf_counter')
    def test_timed_decorator_custom_logger(self, mock_perf_counter):
        """Test @timed decorator with custom logger."""
        mock_logger = Mock(spec=VortexLogger)
        mock_perf_counter.side_effect = [1000.0, 1000.100]
        
        @timed(logger=mock_logger)
        def sample_function():
            return "test"
        
        result = sample_function()
        assert result == "test"
        
        # Should use provided logger, not create new one
        call_args = mock_logger.info.call_args
        expected_module = sample_function.__module__
        expected_op_name = f"{expected_module}.sample_function"
        assert call_args[1]['operation'] == expected_op_name
        assert abs(call_args[1]['duration'] - 100.0) < 0.001
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_timed_decorator_with_args_and_kwargs(self, mock_get_logger, mock_perf_counter):
        """Test @timed decorator preserves function arguments."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        mock_perf_counter.side_effect = [1000.0, 1000.050]
        
        @timed()
        def complex_function(a, b, c=None, *args, **kwargs):
            return {
                'a': a,
                'b': b,
                'c': c,
                'args': args,
                'kwargs': kwargs
            }
        
        result = complex_function(1, 2, 4, 5, extra="value")
        
        expected = {
            'a': 1,
            'b': 2,
            'c': 4,  # Third positional arg becomes c
            'args': (5,),  # Remaining positional args
            'kwargs': {'extra': 'value'}
        }
        assert result == expected
        
        # Verify timing was logged
        mock_logger.info.assert_called_once()
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger') 
    def test_timed_decorator_preserves_function_metadata(self, mock_get_logger, mock_perf_counter):
        """Test @timed decorator preserves original function metadata."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        mock_perf_counter.side_effect = [1000.0, 1000.025]
        
        @timed()
        def documented_function():
            """This function has documentation."""
            return "documented"
        
        # Check that function metadata is preserved
        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This function has documentation."
        
        # Test function still works
        result = documented_function()
        assert result == "documented"
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_timed_decorator_different_exception_types(self, mock_get_logger, mock_perf_counter):
        """Test @timed decorator with different exception types."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        @timed()
        def exception_function(error_type):
            if error_type == "value":
                raise ValueError("Value error")
            elif error_type == "type":
                raise TypeError("Type error")
            elif error_type == "runtime":
                raise RuntimeError("Runtime error")
        
        # Test ValueError
        mock_perf_counter.side_effect = [1000.0, 1000.100]
        with pytest.raises(ValueError):
            exception_function("value")
        
        call_args = mock_logger.error.call_args
        assert call_args[1]['error_type'] == "ValueError"
        
        # Reset and test TypeError
        mock_logger.reset_mock()
        mock_perf_counter.side_effect = [2000.0, 2000.200]
        with pytest.raises(TypeError):
            exception_function("type")
        
        call_args = mock_logger.error.call_args
        assert call_args[1]['error_type'] == "TypeError"
    
    def test_timed_decorator_no_args(self):
        """Test @timed decorator can be used without parentheses."""
        # This should work: @timed (without parentheses)
        # The decorator should handle being called directly on the function
        
        @timed()
        def simple_function():
            return "simple"
        
        # Function should still be callable (though timing won't work without mocking)
        assert callable(simple_function)
        assert simple_function.__name__ == "simple_function"


class TestPerformanceEdgeCases:
    """Test edge cases and error handling in performance module."""
    
    @patch('vortex.logging.performance.get_logger')
    def test_performance_logger_with_empty_operation_name(self, mock_get_logger):
        """Test performance logger with empty operation name."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        perf_logger.time_operation("", 100.0)
        
        # Should still log, even with empty operation name
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Operation '' completed in 100.00ms" in call_args[0][0]
    
    @patch('vortex.logging.performance.get_logger')
    def test_performance_logger_with_zero_duration(self, mock_get_logger):
        """Test performance logger with zero duration."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        perf_logger.time_operation("instant_operation", 0.0)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Operation 'instant_operation' completed in 0.00ms" in call_args[0][0]
    
    @patch('vortex.logging.performance.get_logger')
    def test_performance_logger_with_negative_duration(self, mock_get_logger):
        """Test performance logger with negative duration."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        perf_logger.time_operation("backwards_time", -50.0)
        
        # Should still log negative duration
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Operation 'backwards_time' completed in -50.00ms" in call_args[0][0]
    
    @patch('vortex.logging.performance.get_logger')
    def test_log_metric_with_special_float_values(self, mock_get_logger):
        """Test logging metrics with special float values."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        
        # Test with infinity
        perf_logger.log_metric("infinite_metric", float('inf'))
        call_args = mock_logger.info.call_args
        assert call_args[1]['value'] == float('inf')
        
        mock_logger.reset_mock()
        
        # Test with NaN
        perf_logger.log_metric("nan_metric", float('nan'))
        call_args = mock_logger.info.call_args
        # NaN comparison always returns False, so check it's NaN
        import math
        assert math.isnan(call_args[1]['value'])
    
    @patch('vortex.logging.performance.get_logger')
    def test_log_counter_with_zero_and_negative(self, mock_get_logger):
        """Test logging counters with zero and negative values."""
        mock_logger = Mock(spec=VortexLogger)
        mock_get_logger.return_value = mock_logger
        
        perf_logger = PerformanceLogger("test")
        
        # Test with zero
        perf_logger.log_counter("zero_counter", 0)
        call_args = mock_logger.info.call_args
        assert call_args[1]['count'] == 0
        
        mock_logger.reset_mock()
        
        # Test with negative value
        perf_logger.log_counter("negative_counter", -5)
        call_args = mock_logger.info.call_args
        assert call_args[1]['count'] == -5
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_timed_operation_very_fast_execution(self, mock_get_logger, mock_perf_counter):
        """Test timed operation with very fast execution (microseconds)."""
        mock_logger = Mock(spec=VortexLogger)
        mock_perf_counter.side_effect = [1000.0, 1000.000001]  # 1 microsecond
        
        timed_op = TimedOperation("fast_operation", mock_logger)
        
        with timed_op:
            pass
        
        call_args = mock_logger.info.call_args
        # Should handle very small durations
        assert abs(call_args[1]['duration'] - 0.001) < 0.0001  # 1 microsecond = 0.001 ms
    
    @patch('time.perf_counter')
    @patch('vortex.logging.performance.get_logger')
    def test_timed_operation_very_slow_execution(self, mock_get_logger, mock_perf_counter):
        """Test timed operation with very slow execution."""
        mock_logger = Mock(spec=VortexLogger)
        mock_perf_counter.side_effect = [1000.0, 1003.0]  # 3 seconds
        
        timed_op = TimedOperation("slow_operation", mock_logger)
        
        with timed_op:
            pass
        
        call_args = mock_logger.info.call_args
        # Should handle large durations
        assert call_args[1]['duration'] == 3000.0  # 3 seconds = 3000 ms