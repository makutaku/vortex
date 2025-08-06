"""
Tests for legacy logging compatibility functions.

Tests the backward compatibility interface for the original logging.py.
"""

import pytest
import logging
from unittest.mock import patch, Mock

from vortex.logging.legacy import init_logging


class TestInitLogging:
    """Test init_logging legacy function."""
    
    @patch('vortex.logging.legacy.configure_logging')
    def test_init_logging_default_level(self, mock_configure):
        """Test init_logging with default level."""
        init_logging()
        
        mock_configure.assert_called_once()
        config = mock_configure.call_args[0][0]
        
        assert config.level == logging.INFO
        assert config.format_type == "console"
        assert config.output == ["console"]
    
    @patch('vortex.logging.legacy.configure_logging')
    def test_init_logging_custom_level(self, mock_configure):
        """Test init_logging with custom level."""
        init_logging(level=logging.DEBUG)
        
        mock_configure.assert_called_once()
        config = mock_configure.call_args[0][0]
        
        assert config.level == logging.DEBUG
        assert config.format_type == "console"
        assert config.output == ["console"]
    
    @patch('vortex.logging.legacy.configure_logging')
    def test_init_logging_warning_level(self, mock_configure):
        """Test init_logging with warning level."""
        init_logging(level=logging.WARNING)
        
        mock_configure.assert_called_once()
        config = mock_configure.call_args[0][0]
        
        assert config.level == logging.WARNING