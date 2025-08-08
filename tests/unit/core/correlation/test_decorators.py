"""
Tests for correlation decorators.
"""

import pytest
from unittest.mock import Mock, patch, call
from contextlib import contextmanager

from vortex.core.correlation.decorators import (
    with_correlation, with_provider_correlation, track_operation
)
from vortex.core.correlation.manager import CorrelationIdManager


@pytest.mark.unit
class TestWithCorrelation:
    """Test the with_correlation decorator."""
    
    def test_with_correlation_default_operation_name(self):
        """Test decorator uses function name as default operation."""
        @with_correlation()
        def test_function():
            return "result"
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_context:
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()
            
            result = test_function()
            
            mock_context.assert_called_once_with(
                correlation_id=None,
                operation='test_function',
                provider=None
            )
            assert result == "result"
    
    def test_with_correlation_custom_operation_name(self):
        """Test decorator with custom operation name."""
        @with_correlation(operation="custom_op")
        def test_function():
            return "result"
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_context:
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()
            
            test_function()
            
            mock_context.assert_called_once_with(
                correlation_id=None,
                operation='custom_op',
                provider=None
            )
    
    def test_with_correlation_provider_specified(self):
        """Test decorator with provider specified."""
        @with_correlation(provider="test_provider")
        def test_function():
            return "result"
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_context:
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()
            
            test_function()
            
            mock_context.assert_called_once_with(
                correlation_id=None,
                operation='test_function',
                provider='test_provider'
            )
    
    def test_with_correlation_generate_id_false(self):
        """Test decorator with generate_id=False uses existing correlation ID."""
        @with_correlation(generate_id=False)
        def test_function():
            return "result"
        
        with patch.object(CorrelationIdManager, 'get_current_id', return_value='existing-id') as mock_get_id, \
             patch.object(CorrelationIdManager, 'correlation_context') as mock_context:
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()
            
            test_function()
            
            mock_get_id.assert_called_once()
            mock_context.assert_called_once_with(
                correlation_id='existing-id',
                operation='test_function',
                provider=None
            )
    
    def test_with_correlation_generate_id_false_no_existing_id(self):
        """Test decorator with generate_id=False when no existing correlation ID."""
        @with_correlation(generate_id=False)
        def test_function():
            return "result"
        
        with patch.object(CorrelationIdManager, 'get_current_id', return_value=None) as mock_get_id, \
             patch.object(CorrelationIdManager, 'correlation_context') as mock_context:
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()
            
            test_function()
            
            mock_get_id.assert_called_once()
            mock_context.assert_called_once_with(
                correlation_id=None,
                operation='test_function',
                provider=None
            )
    
    def test_with_correlation_preserves_function_metadata(self):
        """Test that decorator preserves function metadata."""
        @with_correlation()
        def test_function():
            """Test docstring."""
            pass
        
        assert test_function.__name__ == 'test_function'
        assert test_function.__doc__ == "Test docstring."
    
    def test_with_correlation_with_args_and_kwargs(self):
        """Test decorator passes through function arguments correctly."""
        @with_correlation()
        def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_context:
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()
            
            result = test_function("a", "b", kwarg1="c")
            
            assert result == "a-b-c"
    
    def test_with_correlation_exception_propagation(self):
        """Test that exceptions from decorated functions are propagated."""
        @with_correlation()
        def failing_function():
            raise ValueError("Test error")
        
        # Create a proper context manager mock that doesn't suppress exceptions
        @contextmanager
        def mock_context_manager(*args, **kwargs):
            yield Mock()
        
        with patch.object(CorrelationIdManager, 'correlation_context', side_effect=mock_context_manager):
            with pytest.raises(ValueError, match="Test error"):
                failing_function()


@pytest.mark.unit
class TestWithProviderCorrelation:
    """Test the with_provider_correlation decorator."""
    
    def test_with_provider_correlation(self):
        """Test provider correlation decorator."""
        @with_provider_correlation("yahoo")
        def test_function():
            return "result"
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_context:
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()
            
            result = test_function()
            
            mock_context.assert_called_once_with(
                correlation_id=None,
                operation='test_function',
                provider='yahoo'
            )
            assert result == "result"
    
    def test_with_provider_correlation_generates_new_id(self):
        """Test that provider correlation always generates new ID."""
        @with_provider_correlation("barchart")
        def test_function():
            return "result"
        
        # Even if there's an existing ID, it should generate a new one
        with patch.object(CorrelationIdManager, 'get_current_id', return_value='existing-id'), \
             patch.object(CorrelationIdManager, 'correlation_context') as mock_context:
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()
            
            test_function()
            
            # Should be called with correlation_id=None to generate new
            mock_context.assert_called_once_with(
                correlation_id=None,
                operation='test_function',
                provider='barchart'
            )


@pytest.mark.unit
class TestTrackOperation:
    """Test the track_operation decorator."""
    
    def test_track_operation_basic(self):
        """Test basic operation tracking."""
        @track_operation("test_operation")
        def test_function():
            return "result"
        
        mock_context = Mock()
        mock_context.correlation_id = 'test-correlation-id'
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_correlation_context, \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=None):
            mock_correlation_context.return_value.__enter__ = Mock(return_value=mock_context)
            mock_correlation_context.return_value.__exit__ = Mock()
            
            result = test_function()
            
            mock_correlation_context.assert_called_once_with(
                correlation_id=None,
                operation='test_operation'
            )
            assert result == "result"
    
    def test_track_operation_with_correlation_id(self):
        """Test operation tracking with specified correlation ID."""
        @track_operation("test_operation", correlation_id="custom-id")
        def test_function():
            return "result"
        
        mock_context = Mock()
        mock_context.correlation_id = 'custom-id'
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_correlation_context, \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=None):
            mock_correlation_context.return_value.__enter__ = Mock(return_value=mock_context)
            mock_correlation_context.return_value.__exit__ = Mock()
            
            test_function()
            
            mock_correlation_context.assert_called_once_with(
                correlation_id="custom-id",
                operation='test_operation'
            )
    
    def test_track_operation_with_logger_start_and_success(self):
        """Test operation tracking with logger that has operation methods."""
        @track_operation("test_operation")
        def test_function():
            return "result"
        
        mock_context = Mock()
        mock_context.correlation_id = 'test-correlation-id'
        
        mock_logger = Mock()
        mock_logger.log_operation_start = Mock()
        mock_logger.log_operation_success = Mock()
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_correlation_context, \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=mock_logger):
            mock_correlation_context.return_value.__enter__ = Mock(return_value=mock_context)
            mock_correlation_context.return_value.__exit__ = Mock()
            
            result = test_function()
            
            # Check operation start logging
            mock_logger.log_operation_start.assert_called_once_with(
                operation='test_operation',
                correlation_id='test-correlation-id',
                context={
                    'function': 'test_function',
                    'module': 'test_decorators',
                    'args_count': 0,
                    'kwargs_keys': []
                }
            )
            
            # Check operation success logging
            mock_logger.log_operation_success.assert_called_once_with(
                operation='test_operation',
                correlation_id='test-correlation-id',
                context={'result_type': 'str'}
            )
            
            assert result == "result"
    
    def test_track_operation_with_logger_failure(self):
        """Test operation tracking with logger when function fails."""
        @track_operation("test_operation")
        def failing_function():
            raise ValueError("Test error")
        
        mock_context = Mock()
        mock_context.correlation_id = 'test-correlation-id'
        
        mock_logger = Mock()
        mock_logger.log_operation_start = Mock()
        mock_logger.log_operation_failure = Mock()
        
        # Create a proper context manager that allows exceptions through
        @contextmanager
        def mock_context_manager(*args, **kwargs):
            yield mock_context
        
        with patch.object(CorrelationIdManager, 'correlation_context', side_effect=mock_context_manager), \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=mock_logger):
            
            with pytest.raises(ValueError, match="Test error"):
                failing_function()
            
            # Check operation start logging
            mock_logger.log_operation_start.assert_called_once()
            
            # Check operation failure logging
            mock_logger.log_operation_failure.assert_called_once()
            call_args = mock_logger.log_operation_failure.call_args
            assert call_args[1]['operation'] == 'test_operation'
            assert call_args[1]['correlation_id'] == 'test-correlation-id'
            assert isinstance(call_args[1]['error'], ValueError)
            assert call_args[1]['context']['function'] == 'failing_function'
    
    def test_track_operation_logger_without_operation_methods(self):
        """Test operation tracking with logger that doesn't have operation methods."""
        @track_operation("test_operation")
        def test_function():
            return "result"
        
        mock_context = Mock()
        mock_context.correlation_id = 'test-correlation-id'
        
        # Logger without operation methods
        mock_logger = Mock()
        del mock_logger.log_operation_start
        del mock_logger.log_operation_success
        del mock_logger.log_operation_failure
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_correlation_context, \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=mock_logger):
            mock_correlation_context.return_value.__enter__ = Mock(return_value=mock_context)
            mock_correlation_context.return_value.__exit__ = Mock()
            
            # Should not raise exception, just skip logging
            result = test_function()
            assert result == "result"
    
    def test_track_operation_with_args_and_kwargs(self):
        """Test operation tracking captures function arguments."""
        @track_operation("test_operation")
        def test_function(arg1, arg2, kwarg1=None, kwarg2=None):
            return f"{arg1}-{arg2}-{kwarg1}-{kwarg2}"
        
        mock_context = Mock()
        mock_context.correlation_id = 'test-correlation-id'
        
        mock_logger = Mock()
        mock_logger.log_operation_start = Mock()
        mock_logger.log_operation_success = Mock()
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_correlation_context, \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=mock_logger):
            mock_correlation_context.return_value.__enter__ = Mock(return_value=mock_context)
            mock_correlation_context.return_value.__exit__ = Mock()
            
            result = test_function("a", "b", kwarg1="c", kwarg2="d")
            
            # Check that args and kwargs are captured
            start_call_context = mock_logger.log_operation_start.call_args[1]['context']
            assert start_call_context['args_count'] == 2
            assert set(start_call_context['kwargs_keys']) == {'kwarg1', 'kwarg2'}
            
            assert result == "a-b-c-d"
    
    def test_track_operation_adds_correlation_id_to_vortex_error(self):
        """Test that correlation ID is added to VortexError exceptions."""
        class TestError(Exception):
            pass
        
        @track_operation("test_operation")
        def failing_function():
            error = TestError("Test error")
            # Simulate a VortexError-like exception with correlation_id attribute
            error.correlation_id = None
            raise error
        
        mock_context = Mock()
        mock_context.correlation_id = 'test-correlation-id'
        
        # Create a proper context manager that allows exceptions through
        @contextmanager
        def mock_context_manager(*args, **kwargs):
            yield mock_context
        
        with patch.object(CorrelationIdManager, 'correlation_context', side_effect=mock_context_manager), \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=None):
            
            with pytest.raises(TestError) as exc_info:
                failing_function()
            
            # Check that correlation ID was added to the exception
            assert hasattr(exc_info.value, 'correlation_id')
            assert exc_info.value.correlation_id == 'test-correlation-id'
    
    def test_track_operation_exception_without_correlation_id_attribute(self):
        """Test handling of exceptions without correlation_id attribute."""
        @track_operation("test_operation")
        def failing_function():
            raise ValueError("Regular error")
        
        mock_context = Mock()
        mock_context.correlation_id = 'test-correlation-id'
        
        # Create a proper context manager that allows exceptions through
        @contextmanager
        def mock_context_manager(*args, **kwargs):
            yield mock_context
        
        with patch.object(CorrelationIdManager, 'correlation_context', side_effect=mock_context_manager), \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=None):
            
            # Should not raise AttributeError, just skip adding correlation ID
            with pytest.raises(ValueError, match="Regular error"):
                failing_function()
    
    def test_track_operation_preserves_function_metadata(self):
        """Test that track_operation decorator preserves function metadata."""
        @track_operation("test_operation")
        def test_function():
            """Test docstring for track_operation."""
            pass
        
        assert test_function.__name__ == 'test_function'
        assert test_function.__doc__ == "Test docstring for track_operation."


@pytest.mark.unit
class TestDecoratorsIntegration:
    """Test integration scenarios with multiple decorators."""
    
    def test_multiple_decorators_combination(self):
        """Test combining multiple correlation decorators."""
        # This is more of a functional test to ensure decorators can be stacked
        @track_operation("outer_operation")
        @with_correlation(operation="inner_operation")
        def test_function():
            return "result"
        
        with patch.object(CorrelationIdManager, 'correlation_context') as mock_context, \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=None):
            mock_context.return_value.__enter__ = Mock()
            mock_context.return_value.__exit__ = Mock()
            
            result = test_function()
            
            # Should be called twice - once for each decorator
            assert mock_context.call_count == 2
            assert result == "result"
    
    def test_decorator_error_handling_integration(self):
        """Test error handling when decorators are combined."""
        @track_operation("track_op")
        @with_correlation(operation="with_corr_op")
        def failing_function():
            raise RuntimeError("Integration test error")
        
        # Create a proper context manager that allows exceptions through
        @contextmanager
        def mock_context_manager(*args, **kwargs):
            yield Mock()
        
        with patch.object(CorrelationIdManager, 'correlation_context', side_effect=mock_context_manager), \
             patch('vortex.core.correlation.decorators.get_structured_logger', return_value=None):
            
            with pytest.raises(RuntimeError, match="Integration test error"):
                failing_function()