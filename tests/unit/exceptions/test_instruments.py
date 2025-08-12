"""
Unit tests for instrument-related exceptions.

Tests all instrument exception classes and their initialization patterns.
"""

import pytest

from vortex.exceptions.instruments import (
    InstrumentError,
    InvalidInstrumentError, 
    UnsupportedInstrumentError,
)


class TestInstrumentError:
    """Test base InstrumentError class."""
    
    def test_inheritance(self):
        """Test that InstrumentError inherits from VortexError."""
        error = InstrumentError("Test message")
        # VortexError always includes correlation ID in string representation
        assert "Test message" in str(error)
        assert "🔍 Error ID:" in str(error)
        assert error.error_code is None
        assert error.help_text is None
        
    def test_with_help_and_code(self):
        """Test InstrumentError with help text and error code."""
        from vortex.exceptions.base import ExceptionContext
        context = ExceptionContext(help_text="Help text", error_code="TEST_CODE")
        error = InstrumentError("Test message", context)
        error_str = str(error)
        assert "Test message" in error_str
        assert "💡 Help: Help text" in error_str
        assert "🔍 Error ID:" in error_str
        assert error.help_text == "Help text"
        assert error.error_code == "TEST_CODE"


class TestInvalidInstrumentError:
    """Test InvalidInstrumentError class."""
    
    def test_basic_initialization(self):
        """Test basic initialization with symbol and reason."""
        error = InvalidInstrumentError("AAPL", "invalid format")
        error_str = str(error)
        assert "Invalid instrument 'AAPL': invalid format" in error_str
        assert "Check the symbol format" in error_str  # Part of help text
        assert "🔍 Error ID:" in error_str
        assert error.error_code == "INVALID_INSTRUMENT"
        
    def test_with_empty_symbol(self):
        """Test with empty symbol."""
        error = InvalidInstrumentError("", "symbol cannot be empty")
        assert "Invalid instrument '': symbol cannot be empty" in str(error)
        assert error.error_code == "INVALID_INSTRUMENT"
        
    def test_with_special_characters(self):
        """Test with symbols containing special characters."""
        error = InvalidInstrumentError("ABC@123", "contains invalid characters")
        assert "Invalid instrument 'ABC@123': contains invalid characters" in str(error)
        assert error.error_code == "INVALID_INSTRUMENT"


class TestUnsupportedInstrumentError:
    """Test UnsupportedInstrumentError class."""
    
    def test_basic_initialization(self):
        """Test basic initialization without supported types."""
        error = UnsupportedInstrumentError("BTCUSD", "barchart")
        error_str = str(error)
        assert "Instrument 'BTCUSD' not supported by barchart" in error_str
        assert "vortex providers --info barchart" in error_str  # Part of help text
        assert error.error_code == "UNSUPPORTED_INSTRUMENT"
        
    def test_with_supported_types(self):
        """Test initialization with supported types list."""
        supported_types = ["futures", "stocks", "forex"]
        error = UnsupportedInstrumentError("CRYPTO", "yahoo", supported_types)
        error_str = str(error)
        assert "Instrument 'CRYPTO' not supported by yahoo" in error_str
        assert "supports: futures, stocks, forex" in error_str
        assert error.error_code == "UNSUPPORTED_INSTRUMENT"
        
    def test_with_empty_supported_types(self):
        """Test with empty supported types list."""
        error = UnsupportedInstrumentError("TEST", "provider", [])
        assert "Instrument 'TEST' not supported by provider" in str(error)
        
    def test_with_single_supported_type(self):
        """Test with single supported type."""
        error = UnsupportedInstrumentError("TEST", "provider", ["stocks"])
        error_str = str(error)
        assert "Instrument 'TEST' not supported by provider" in error_str
        assert "supports: stocks" in error_str
        
    def test_with_none_supported_types(self):
        """Test with None supported types (should not show supports clause)."""
        error = UnsupportedInstrumentError("TEST", "provider", None)
        error_str = str(error)
        assert "Instrument 'TEST' not supported by provider" in error_str
        assert "supports:" not in error_str
        
    def test_inheritance(self):
        """Test that UnsupportedInstrumentError inherits from InstrumentError."""
        error = UnsupportedInstrumentError("TEST", "provider")
        assert isinstance(error, InstrumentError)


class TestInstrumentErrorIntegration:
    """Integration tests for instrument exceptions."""
    
    def test_exception_chaining(self):
        """Test that instrument errors can be chained."""
        try:
            raise InvalidInstrumentError("BAD", "test error")
        except InvalidInstrumentError as e:
            # Chain with another exception
            chained = UnsupportedInstrumentError("OTHER", "provider")
            chained.__cause__ = e
            assert chained.__cause__ is e
            
    def test_error_codes_unique(self):
        """Test that different error classes have unique codes."""
        invalid_error = InvalidInstrumentError("TEST", "reason")
        unsupported_error = UnsupportedInstrumentError("TEST", "provider")
        
        assert invalid_error.error_code == "INVALID_INSTRUMENT"
        assert unsupported_error.error_code == "UNSUPPORTED_INSTRUMENT"
        assert invalid_error.error_code != unsupported_error.error_code