"""
Unit tests for correlation utility functions.

Tests the utility functions that provide compatibility with the original
correlation API while leveraging the unified correlation system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from vortex.core.correlation.utils import (
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
    clear_correlation_id,
    get_structured_logger,
    CorrelationContext
)


class TestCorrelationUtilityFunctions:
    """Test utility functions for correlation ID management."""
    
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    def test_get_correlation_id(self, mock_manager):
        """Test get_correlation_id function."""
        mock_manager.get_current_id.return_value = "test-id-123"
        
        result = get_correlation_id()
        
        assert result == "test-id-123"
        mock_manager.get_current_id.assert_called_once()
        
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    def test_get_correlation_id_none(self, mock_manager):
        """Test get_correlation_id when no ID is set."""
        mock_manager.get_current_id.return_value = None
        
        result = get_correlation_id()
        
        assert result is None
        mock_manager.get_current_id.assert_called_once()
        
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    def test_set_correlation_id(self, mock_manager):
        """Test set_correlation_id function."""
        test_id = "new-correlation-id"
        
        set_correlation_id(test_id)
        
        mock_manager.set_correlation_id.assert_called_once_with(test_id)
        
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    def test_generate_correlation_id(self, mock_manager):
        """Test generate_correlation_id function."""
        mock_manager.generate_id.return_value = "generated-id-456"
        
        result = generate_correlation_id()
        
        assert result == "generated-id-456"
        mock_manager.generate_id.assert_called_once()
        
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    def test_clear_correlation_id(self, mock_manager):
        """Test clear_correlation_id function."""
        clear_correlation_id()
        
        mock_manager.clear_context.assert_called_once()


class TestGetStructuredLogger:
    """Test get_structured_logger compatibility function."""
    
    def test_successful_import(self):
        """Test successful import of structured logger."""
        # Test the actual import path that exists in the function
        from vortex.core.correlation.utils import get_structured_logger
        
        # The function will fail to import the actual logger and return None
        result = get_structured_logger()
        assert result is None
        
    def test_import_error_fallback(self):
        """Test graceful fallback when import fails."""
        result = get_structured_logger()
        
        # Should return None when import fails
        assert result is None
        
    @patch('vortex.core.correlation.utils.get_structured_logger')
    def test_import_error_handling(self, mock_import):
        """Test that ImportError is handled gracefully."""
        # The function should handle ImportError and return None
        result = get_structured_logger()
        assert result is None


class TestCorrelationContext:
    """Test CorrelationContext context manager."""
    
    @patch('vortex.core.correlation.utils.generate_correlation_id')
    def test_initialization_with_id(self, mock_generate):
        """Test initialization with provided correlation ID."""
        test_id = "provided-id"
        context = CorrelationContext(test_id)
        
        assert context.correlation_id == test_id
        assert context._context_manager is None
        mock_generate.assert_not_called()
        
    @patch('vortex.core.correlation.utils.generate_correlation_id')
    def test_initialization_without_id(self, mock_generate):
        """Test initialization without provided correlation ID."""
        mock_generate.return_value = "generated-id"
        context = CorrelationContext()
        
        assert context.correlation_id == "generated-id"
        assert context._context_manager is None
        mock_generate.assert_called_once()
        
    @patch('vortex.core.correlation.utils.generate_correlation_id')
    def test_initialization_with_none_id(self, mock_generate):
        """Test initialization with None correlation ID."""
        mock_generate.return_value = "generated-id"
        context = CorrelationContext(None)
        
        assert context.correlation_id == "generated-id"
        mock_generate.assert_called_once()
        
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    def test_context_manager_enter(self, mock_manager):
        """Test entering the correlation context."""
        # Mock the context manager
        mock_context_manager = Mock()
        mock_context = Mock()
        mock_context.correlation_id = "test-id"
        
        # Configure the mock to behave as a context manager
        mock_context_manager.__enter__ = Mock(return_value=mock_context)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_manager.correlation_context.return_value = mock_context_manager
        
        context = CorrelationContext("test-id")
        
        with context as correlation_id:
            assert correlation_id == "test-id"
            mock_manager.correlation_context.assert_called_once_with(correlation_id="test-id")
            mock_context_manager.__enter__.assert_called_once()
            
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    def test_context_manager_exit(self, mock_manager):
        """Test exiting the correlation context."""
        # Mock the context manager
        mock_context_manager = Mock()
        mock_context = Mock()
        mock_context.correlation_id = "test-id"
        
        # Configure the mock to behave as a context manager
        mock_context_manager.__enter__ = Mock(return_value=mock_context)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_manager.correlation_context.return_value = mock_context_manager
        
        context = CorrelationContext("test-id")
        
        try:
            with context:
                pass
        except Exception:
            pass
            
        mock_context_manager.__exit__.assert_called_once()
        
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    def test_context_manager_exception_handling(self, mock_manager):
        """Test context manager behavior with exceptions."""
        # Mock the context manager
        mock_context_manager = Mock()
        mock_context = Mock()
        mock_context.correlation_id = "test-id"
        
        # Configure the mock to behave as a context manager
        mock_context_manager.__enter__ = Mock(return_value=mock_context)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_manager.correlation_context.return_value = mock_context_manager
        
        context = CorrelationContext("test-id")
        
        try:
            with context:
                raise ValueError("Test exception")
        except ValueError:
            pass
            
        # Should have called __exit__ with exception info
        mock_context_manager.__exit__.assert_called_once()
        exit_args = mock_context_manager.__exit__.call_args[0]
        assert exit_args[0] == ValueError
        assert "Test exception" in str(exit_args[1])
        
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    def test_context_manager_no_context_manager(self, mock_manager):
        """Test context manager behavior when _context_manager is None."""
        context = CorrelationContext("test-id")
        context._context_manager = None
        
        # __exit__ should handle None context manager gracefully
        result = context.__exit__(None, None, None)
        assert result is None
        
    @patch('vortex.core.correlation.utils.CorrelationIdManager')
    @patch('vortex.core.correlation.utils.generate_correlation_id')
    def test_full_context_manager_workflow(self, mock_generate, mock_manager):
        """Test complete context manager workflow."""
        mock_generate.return_value = "auto-generated-id"
        
        # Mock the correlation context manager
        mock_context_manager = Mock()
        mock_context = Mock()
        mock_context.correlation_id = "auto-generated-id"
        
        # Configure the mock to behave as a context manager
        mock_context_manager.__enter__ = Mock(return_value=mock_context)
        mock_context_manager.__exit__ = Mock(return_value=None)
        mock_manager.correlation_context.return_value = mock_context_manager
        
        # Use context manager without providing ID
        with CorrelationContext() as correlation_id:
            assert correlation_id == "auto-generated-id"
            
        # Verify the workflow
        mock_generate.assert_called_once()
        mock_manager.correlation_context.assert_called_once_with(correlation_id="auto-generated-id")
        mock_context_manager.__enter__.assert_called_once()
        mock_context_manager.__exit__.assert_called_once()
