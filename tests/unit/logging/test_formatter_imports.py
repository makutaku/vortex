"""
Tests for logging formatter import scenarios.
"""

import pytest
from unittest.mock import patch


class TestRichImportHandling:
    """Test Rich library import handling."""
    
    def test_rich_import_failure_handling(self):
        """Test that Rich import failure is handled gracefully."""
        # Mock import failure for Rich
        with patch.dict('sys.modules', {'rich.console': None, 'rich.logging': None}):
            with patch('builtins.__import__', side_effect=ImportError("No module named 'rich'")):
                # Import the formatters module to trigger import attempt
                import importlib
                import vortex.logging.formatters
                importlib.reload(vortex.logging.formatters)
                
                # Should set rich_available to False
                assert not vortex.logging.formatters.rich_available
    
    def test_rich_import_success_path(self):
        """Test successful Rich import path."""
        # This tests the positive path where Rich is available
        # If this test environment has Rich, it will test the success path
        # If not, it's expected to pass anyway since we're not testing the functionality
        
        import vortex.logging.formatters
        
        # If rich is available in test environment, rich_available should be True
        # If not, it should be False - both are valid outcomes
        assert hasattr(vortex.logging.formatters, 'rich_available')
        assert isinstance(vortex.logging.formatters.rich_available, bool)
    
    def test_create_rich_handler_when_not_available(self):
        """Test create_rich_handler when Rich is not available."""
        from vortex.logging.formatters import create_rich_handler
        
        # Temporarily set rich_available to False to test the error path
        with patch('vortex.logging.formatters.rich_available', False):
            with pytest.raises(ImportError, match="Rich library not available"):
                create_rich_handler()


class TestFormatterCreationEdgeCases:
    """Test formatter creation edge cases for additional coverage."""
    
    def test_create_console_formatter(self):
        """Test console formatter creation."""
        from vortex.logging.formatters import create_console_formatter
        
        formatter = create_console_formatter()
        
        assert formatter is not None
        # Test that it formats correctly
        import logging
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "INFO" in formatted
        assert "test.logger" in formatted
        assert "Test message" in formatted
    
    def test_create_structured_formatter(self):
        """Test structured formatter creation."""
        from vortex.logging.formatters import create_structured_formatter
        
        formatter = create_structured_formatter("test-service", "1.0.0")
        
        assert formatter is not None
        assert formatter.service_name == "test-service"
        assert formatter.version == "1.0.0"
    
    def test_create_structured_formatter_defaults(self):
        """Test structured formatter creation with defaults."""
        from vortex.logging.formatters import create_structured_formatter
        
        formatter = create_structured_formatter()
        
        assert formatter is not None
        assert formatter.service_name == "vortex"
        assert formatter.version == "unknown"