"""Unit tests for CLI instrument parser utilities."""

import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from vortex.cli.utils.instrument_parser import (
    detect_instrument_type,
    expand_symbol_patterns,
    load_symbols_from_file,
    normalize_symbol,
    parse_instruments,
    validate_symbol,
)


class TestParseInstruments:
    """Test the main parse_instruments function."""
    
    def test_parse_instruments_symbols_only(self):
        """Test parsing with symbols only."""
        symbols = ("AAPL", "googl", " MSFT ")
        result = parse_instruments(symbols, None)
        
        assert result == ["AAPL", "GOOGL", "MSFT"]
    
    def test_parse_instruments_empty_symbols(self):
        """Test parsing with empty symbols."""
        result = parse_instruments((), None)
        assert result == []
    
    def test_parse_instruments_with_duplicates(self):
        """Test parsing removes duplicates while preserving order."""
        symbols = ("AAPL", "googl", "AAPL", "msft", "GOOGL")
        result = parse_instruments(symbols, None)
        
        assert result == ["AAPL", "GOOGL", "MSFT"]
    
    def test_parse_instruments_with_empty_strings(self):
        """Test parsing filters out empty strings."""
        symbols = ("AAPL", "", "  ", "GOOGL")
        result = parse_instruments(symbols, None)
        
        assert result == ["AAPL", "GOOGL"]
    
    @patch('vortex.cli.utils.instrument_parser.load_symbols_from_file')
    def test_parse_instruments_with_file(self, mock_load):
        """Test parsing with symbols file."""
        mock_load.return_value = ["TSLA", "NVDA"]
        
        symbols = ("AAPL",)
        file_path = Path("test.txt")
        
        result = parse_instruments(symbols, file_path)
        
        assert result == ["AAPL", "TSLA", "NVDA"]
        mock_load.assert_called_once_with(file_path)
    
    @patch('vortex.cli.utils.instrument_parser.load_symbols_from_file')
    def test_parse_instruments_file_and_cli_duplicates(self, mock_load):
        """Test parsing with overlapping symbols from CLI and file."""
        mock_load.return_value = ["AAPL", "TSLA"]
        
        symbols = ("aapl", "GOOGL")
        file_path = Path("test.txt")
        
        result = parse_instruments(symbols, file_path)
        
        assert result == ["AAPL", "GOOGL", "TSLA"]
        mock_load.assert_called_once_with(file_path)


class TestLoadSymbolsFromFile:
    """Test loading symbols from file."""
    
    def test_load_symbols_basic(self):
        """Test loading basic symbols from file."""
        content = "AAPL\nGOOGL\nMSFT\n"
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = load_symbols_from_file(Path("test.txt"))
        
        assert result == ["AAPL", "GOOGL", "MSFT"]
    
    def test_load_symbols_with_comments(self):
        """Test loading symbols while skipping comments."""
        content = "# This is a comment\nAAPL\n# Another comment\nGOOGL\nMSFT\n"
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = load_symbols_from_file(Path("test.txt"))
        
        assert result == ["AAPL", "GOOGL", "MSFT"]
    
    def test_load_symbols_with_empty_lines(self):
        """Test loading symbols while skipping empty lines."""
        content = "AAPL\n\n\nGOOGL\n   \nMSFT\n"
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = load_symbols_from_file(Path("test.txt"))
        
        assert result == ["AAPL", "GOOGL", "MSFT"]
    
    def test_load_symbols_comma_separated(self):
        """Test loading comma-separated symbols."""
        content = "AAPL,GOOGL,MSFT\nTSLA, NVDA , AMD\n"
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = load_symbols_from_file(Path("test.txt"))
        
        assert result == ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMD"]
    
    def test_load_symbols_mixed_format(self):
        """Test loading mixed format (lines and comma-separated)."""
        content = "# Comment\nAAPL\nGOOGL, MSFT\n\nTSLA\n# More comments\nNVDA,AMD,INTC\n"
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = load_symbols_from_file(Path("test.txt"))
        
        assert result == ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMD", "INTC"]
    
    def test_load_symbols_whitespace_handling(self):
        """Test proper whitespace handling."""
        content = "  AAPL  \n\t GOOGL \t\n MSFT,  TSLA  , NVDA\n"
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = load_symbols_from_file(Path("test.txt"))
        
        assert result == ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]
    
    def test_load_symbols_file_not_found(self):
        """Test FileNotFoundError when file doesn't exist."""
        with patch("builtins.open", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError, match="Symbols file not found"):
                load_symbols_from_file(Path("nonexistent.txt"))
    
    def test_load_symbols_io_error(self):
        """Test IOError when file cannot be read."""
        with patch("builtins.open", side_effect=IOError("Permission denied")):
            with pytest.raises(IOError, match="Error reading symbols file.*Permission denied"):
                load_symbols_from_file(Path("test.txt"))
    
    def test_load_symbols_empty_file(self):
        """Test loading from empty file."""
        with patch("builtins.open", mock_open(read_data="")):
            result = load_symbols_from_file(Path("test.txt"))
        
        assert result == []
    
    def test_load_symbols_only_comments(self):
        """Test loading from file with only comments."""
        content = "# Comment 1\n# Comment 2\n   # Comment 3\n"
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = load_symbols_from_file(Path("test.txt"))
        
        assert result == []
    
    def test_load_symbols_encoding(self):
        """Test that file is opened with UTF-8 encoding."""
        content = "AAPL\n"
        
        m = mock_open(read_data=content)
        with patch("builtins.open", m):
            load_symbols_from_file(Path("test.txt"))
        
        m.assert_called_once_with(Path("test.txt"), 'r', encoding='utf-8')


class TestValidateSymbol:
    """Test symbol validation."""
    
    def test_validate_symbol_valid_cases(self):
        """Test valid symbol cases."""
        valid_symbols = [
            "AAPL",
            "GOOGL",
            "GC",
            "GCZ21",
            "GC-DEC21",
            "ES_H22",
            "SPY",
            "QQQ",
            "EUR/USD",
            "BTC-USD",
            "A",
            "ABC123",
        ]
        
        for symbol in valid_symbols:
            assert validate_symbol(symbol), f"Symbol {symbol} should be valid"
    
    def test_validate_symbol_invalid_cases(self):
        """Test invalid symbol cases."""
        invalid_symbols = [
            "",
            None,
            123,
            [],
            {},
            "   ",
            "ABC@123",
            "ABC%DEF",
            "ABC&DEF",
            "ABC*DEF",
            "ABC+DEF",
            "ABC=DEF",
            "ABC!DEF",
        ]
        
        for symbol in invalid_symbols:
            assert not validate_symbol(symbol), f"Symbol {symbol} should be invalid"
    
    def test_validate_symbol_whitespace(self):
        """Test symbol validation with whitespace."""
        assert validate_symbol("  AAPL  ")
        assert validate_symbol("\tGOOGL\n")
        assert not validate_symbol("   ")
    
    def test_validate_symbol_case_insensitive(self):
        """Test that validation is case insensitive."""
        assert validate_symbol("aapl")
        assert validate_symbol("googl")
        assert validate_symbol("MsFt")


class TestNormalizeSymbol:
    """Test symbol normalization."""
    
    def test_normalize_symbol_basic(self):
        """Test basic symbol normalization."""
        assert normalize_symbol("aapl") == "AAPL"
        assert normalize_symbol("googl") == "GOOGL"
        assert normalize_symbol("MsFt") == "MSFT"
    
    def test_normalize_symbol_whitespace(self):
        """Test normalization removes whitespace."""
        assert normalize_symbol("  AAPL  ") == "AAPL"
        assert normalize_symbol("\tGOOGL\n") == "GOOGL"
        assert normalize_symbol(" ") == ""
    
    def test_normalize_symbol_empty(self):
        """Test normalization of empty/None values."""
        assert normalize_symbol("") == ""
        assert normalize_symbol(None) == ""
    
    def test_normalize_symbol_preserves_format(self):
        """Test that normalization preserves symbol format."""
        assert normalize_symbol("gcz21") == "GCZ21"
        assert normalize_symbol("es-h22") == "ES-H22"
        assert normalize_symbol("eur/usd") == "EUR/USD"


class TestDetectInstrumentType:
    """Test instrument type detection."""
    
    def test_detect_futures(self):
        """Test futures detection."""
        futures_symbols = [
            "GCZ21",   # Gold December 2021
            "ESH22",   # E-mini S&P March 2022
            "CLM23",   # Crude Oil June 2023
            "ZBU24",   # 30-Year Treasury September 2024
            "NQZ25",   # E-mini Nasdaq December 2025
        ]
        
        for symbol in futures_symbols:
            assert detect_instrument_type(symbol) == "future", f"Symbol {symbol} should be detected as future"
    
    def test_detect_stocks(self):
        """Test stock detection."""
        stock_symbols = [
            "AAPL",
            "GOOGL",
            "MSFT",
            "TSLA",
            "NVDA",
            "A",
            "BRK",
        ]
        
        for symbol in stock_symbols:
            assert detect_instrument_type(symbol) == "stock", f"Symbol {symbol} should be detected as stock"
    
    def test_detect_forex(self):
        """Test forex detection."""
        forex_symbols = [
            "EUR/USD",
            "GBP/JPY",
            "USD/CHF",
            "AUD/NZD",
            "EUR_USD",
            "GBP_JPY",
        ]
        
        for symbol in forex_symbols:
            assert detect_instrument_type(symbol) == "forex", f"Symbol {symbol} should be detected as forex"
    
    def test_detect_unknown(self):
        """Test unknown instrument detection."""
        unknown_symbols = [
            "",
            "123",
            "TOOLONG123456",  # Too long to be a stock
            "EURUSD",  # No separator for forex
            "ABC/DEFG",  # Wrong length for forex
            "XY/Z",  # Wrong length for forex
        ]
        
        for symbol in unknown_symbols:
            assert detect_instrument_type(symbol) == "unknown", f"Symbol {symbol} should be detected as unknown"
    
    def test_detect_case_insensitive(self):
        """Test detection is case insensitive."""
        assert detect_instrument_type("gcz21") == "future"
        assert detect_instrument_type("aapl") == "stock"
        assert detect_instrument_type("eur/usd") == "forex"
    
    def test_detect_whitespace(self):
        """Test detection handles whitespace."""
        assert detect_instrument_type("  GCZ21  ") == "future"
        assert detect_instrument_type("\tAAPL\n") == "stock"
        assert detect_instrument_type(" EUR/USD ") == "forex"


class TestExpandSymbolPatterns:
    """Test symbol pattern expansion."""
    
    def test_expand_no_patterns(self):
        """Test expansion with no patterns."""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        result = expand_symbol_patterns(symbols)
        
        assert result == symbols
    
    def test_expand_with_wildcards(self):
        """Test expansion preserves wildcards (not implemented yet)."""
        symbols = ["AAPL", "GC*", "ES?21"]
        result = expand_symbol_patterns(symbols)
        
        # Current implementation just passes through
        assert result == symbols
    
    def test_expand_empty_list(self):
        """Test expansion with empty list."""
        result = expand_symbol_patterns([])
        assert result == []
    
    def test_expand_mixed_patterns(self):
        """Test expansion with mixed patterns and normal symbols."""
        symbols = ["AAPL", "GC*", "MSFT", "ES?21", "GOOGL"]
        result = expand_symbol_patterns(symbols)
        
        # Current implementation just passes through
        assert result == symbols


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_real_world_symbol_file(self):
        """Test processing a realistic symbols file."""
        content = """# Stock symbols for testing
AAPL
GOOGL, MSFT, TSLA

# Futures contracts  
GCZ21
ESH22

# Forex pairs
EUR/USD
GBP/JPY, USD/CHF

# Empty lines and more comments


# Final symbols
NVDA
AMD, INTC
"""
        
        with patch("builtins.open", mock_open(read_data=content)):
            result = load_symbols_from_file(Path("realistic.txt"))
        
        expected = [
            "AAPL", "GOOGL", "MSFT", "TSLA",
            "GCZ21", "ESH22",
            "EUR/USD", "GBP/JPY", "USD/CHF",
            "NVDA", "AMD", "INTC"
        ]
        
        assert result == expected
    
    def test_cli_and_file_integration(self):
        """Test full integration of CLI symbols and file symbols."""
        file_content = "TSLA\nNVDA, AMD\n# Comment\nINTC\n"
        
        with patch("builtins.open", mock_open(read_data=file_content)):
            cli_symbols = ("aapl", "GOOGL", "tsla")  # TSLA duplicate
            file_path = Path("test.txt")
            
            result = parse_instruments(cli_symbols, file_path)
        
        # Should remove duplicates and normalize case
        assert result == ["AAPL", "GOOGL", "TSLA", "NVDA", "AMD", "INTC"]
    
    def test_validation_and_normalization_pipeline(self):
        """Test complete validation and normalization pipeline."""
        symbols = ["  aapl  ", "GOOGL", "gc@invalid", "ESH22", ""]
        
        processed = []
        for symbol in symbols:
            normalized = normalize_symbol(symbol)
            if normalized and validate_symbol(normalized):
                processed.append(normalized)
        
        assert processed == ["AAPL", "GOOGL", "ESH22"]
    
    def test_instrument_type_classification(self):
        """Test classification of mixed instrument types."""
        symbols = ["AAPL", "GCZ21", "EUR/USD", "GOOGL", "ESH22", "GBP/JPY"]
        
        classification = {}
        for symbol in symbols:
            instrument_type = detect_instrument_type(symbol)
            if instrument_type not in classification:
                classification[instrument_type] = []
            classification[instrument_type].append(symbol)
        
        expected = {
            "stock": ["AAPL", "GOOGL"],
            "future": ["GCZ21", "ESH22"],
            "forex": ["EUR/USD", "GBP/JPY"]
        }
        
        assert classification == expected