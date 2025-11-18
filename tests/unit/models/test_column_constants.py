"""
Tests for column constants and mapping functions.

Validates that column constants are correctly defined and that the 
column mapping system works as expected across different providers.
"""

import pytest
import pandas as pd
from unittest.mock import Mock

from vortex.models import (
    CLOSE_COLUMN,
    DATETIME_INDEX_NAME,
    HIGH_COLUMN,
    LOW_COLUMN,
    OPEN_COLUMN,
    REQUIRED_DATA_COLUMNS,
    STANDARD_OHLCV_COLUMNS,
    VOLUME_COLUMN,
    get_column_mapping,
    get_provider_expected_columns,
    standardize_dataframe_columns,
    validate_column_data_types,
    validate_required_columns,
)
from vortex.models.columns import CSV_REQUIRED_COLUMNS, DATETIME_COLUMN_NAME

# Import provider-specific constants from their respective providers
from vortex.infrastructure.providers.yahoo.column_mapping import YahooColumnMapping
from vortex.infrastructure.providers.barchart.column_mapping import BarchartColumnMapping  
from vortex.infrastructure.providers.ibkr.column_mapping import IbkrColumnMapping

# Create instances to access constants
_yahoo_mapping = YahooColumnMapping()
_barchart_mapping = BarchartColumnMapping()
_ibkr_mapping = IbkrColumnMapping()

# Extract constants for backward compatibility in tests
ADJ_CLOSE_COLUMN = _yahoo_mapping.ADJ_CLOSE_COLUMN
DIVIDENDS_COLUMN = _yahoo_mapping.DIVIDENDS_COLUMN  
STOCK_SPLITS_COLUMN = _yahoo_mapping.STOCK_SPLITS_COLUMN
OPEN_INTEREST_COLUMN = _barchart_mapping.OPEN_INTEREST_COLUMN
WAP_COLUMN = _ibkr_mapping.WAP_COLUMN
COUNT_COLUMN = _ibkr_mapping.COUNT_COLUMN

# Create provider-specific column sets for tests
YAHOO_SPECIFIC_COLUMNS = _yahoo_mapping.get_provider_specific_columns()
BARCHART_SPECIFIC_COLUMNS = _barchart_mapping.get_provider_specific_columns()
IBKR_SPECIFIC_COLUMNS = _ibkr_mapping.get_provider_specific_columns()


@pytest.mark.unit
class TestColumnConstants:
    """Test column constant definitions."""
    
    def test_basic_column_constants(self):
        """Test that basic column constants are properly defined."""
        assert DATETIME_COLUMN_NAME == 'Datetime'
        assert OPEN_COLUMN == "Open"
        assert HIGH_COLUMN == "High"
        assert LOW_COLUMN == "Low"
        assert CLOSE_COLUMN == "Close"
        assert VOLUME_COLUMN == "Volume"
    
    def test_provider_specific_constants(self):
        """Test provider-specific column constants."""
        assert ADJ_CLOSE_COLUMN == "Adj Close"
        assert DIVIDENDS_COLUMN == "Dividends"
        assert STOCK_SPLITS_COLUMN == "Stock Splits"
        assert OPEN_INTEREST_COLUMN == "Open Interest"
        assert WAP_COLUMN == "wap"
        assert COUNT_COLUMN == "count"
    
    def test_column_sets(self):
        """Test that column sets are properly defined."""
        expected_ohlcv = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        assert STANDARD_OHLCV_COLUMNS == expected_ohlcv
        
        # Test new data columns constant (without index)
        assert REQUIRED_DATA_COLUMNS == expected_ohlcv
        
        # Test legacy required price columns constant (with index for backward compatibility)
        expected_required = [DATETIME_COLUMN_NAME] + expected_ohlcv
        assert CSV_REQUIRED_COLUMNS == expected_required
        
        assert YAHOO_SPECIFIC_COLUMNS == [ADJ_CLOSE_COLUMN, DIVIDENDS_COLUMN, STOCK_SPLITS_COLUMN]
        assert BARCHART_SPECIFIC_COLUMNS == [OPEN_INTEREST_COLUMN]
        assert IBKR_SPECIFIC_COLUMNS == [WAP_COLUMN, COUNT_COLUMN]


@pytest.mark.unit
class TestColumnValidation:
    """Test column validation functions."""
    
    def test_validate_required_columns_case_sensitive(self):
        """Test case-sensitive column validation."""
        df_columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
        required = [DATETIME_COLUMN_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]
        
        missing, found = validate_required_columns(df_columns, required, case_insensitive=False)
        
        assert DATETIME_COLUMN_NAME in missing  # 'DATETIME' not in df_columns
        assert OPEN_COLUMN in found
        assert HIGH_COLUMN in found
        assert LOW_COLUMN in found
        assert CLOSE_COLUMN in found
    
    def test_validate_required_columns_case_insensitive(self):
        """Test case-insensitive column validation."""
        df_columns = ["date", "open", "high", "low", "close", "volume"]
        required = [DATETIME_COLUMN_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        
        missing, found = validate_required_columns(df_columns, required, case_insensitive=True)
        
        assert len(missing) == 1  # Only DATETIME should be missing (date != DATETIME)
        assert DATETIME_COLUMN_NAME in missing
        assert len(found) == 5  # All OHLCV should be found
    
    def test_validate_required_columns_exact_match(self):
        """Test validation with exact column matches."""
        df_columns = [DATETIME_COLUMN_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        required = CSV_REQUIRED_COLUMNS
        
        missing, found = validate_required_columns(df_columns, required, case_insensitive=False)
        
        assert len(missing) == 0
        assert len(found) == len(required)
        assert set(found) == set(required)
    
    def test_validate_required_columns_empty_inputs(self):
        """Test validation with empty inputs."""
        missing, found = validate_required_columns([], [])
        assert len(missing) == 0
        assert len(found) == 0
        
        # When required_columns is empty, no columns are missing or found
        missing, found = validate_required_columns(["A", "B"], [])
        assert len(missing) == 0  # No required columns to be missing
        assert len(found) == 0    # No required columns to be found
        
        missing, found = validate_required_columns([], ["A", "B"])
        assert missing == ["A", "B"]
        assert len(found) == 0
    
    def test_get_provider_expected_columns(self):
        """Test getting provider-specific expected columns."""
        # Test Yahoo Finance (should return only data columns, not index)
        required, optional = get_provider_expected_columns('yahoo')
        assert required == REQUIRED_DATA_COLUMNS  # Only data columns, not index
        assert optional == YAHOO_SPECIFIC_COLUMNS
        
        # Test Barchart
        required, optional = get_provider_expected_columns('barchart')
        assert required == REQUIRED_DATA_COLUMNS  # Only data columns, not index
        assert optional == BARCHART_SPECIFIC_COLUMNS
        
        # Test IBKR
        required, optional = get_provider_expected_columns('ibkr')
        assert required == REQUIRED_DATA_COLUMNS  # Only data columns, not index
        assert optional == IBKR_SPECIFIC_COLUMNS
        
        # Test unknown provider
        required, optional = get_provider_expected_columns('unknown')
        assert required == REQUIRED_DATA_COLUMNS  # Only data columns, not index
        assert optional == []


@pytest.mark.unit
class TestColumnMapping:
    """Test column mapping functions."""
    
    def test_get_column_mapping_barchart(self):
        """Test Barchart column mapping."""
        df_columns = ["Time", "Open", "High", "Low", "Last", "Volume", "Open Interest"]
        mapping = get_column_mapping('barchart', df_columns)
        
        assert mapping["Time"] == DATETIME_COLUMN_NAME
        assert mapping["Last"] == CLOSE_COLUMN
        assert mapping["Open Interest"] == OPEN_INTEREST_COLUMN
        assert mapping["Open"] == OPEN_COLUMN
        assert mapping["High"] == HIGH_COLUMN
        assert mapping["Low"] == LOW_COLUMN
        assert mapping["Volume"] == VOLUME_COLUMN
    
    def test_get_column_mapping_yahoo(self):
        """Test Yahoo Finance column mapping."""
        df_columns = ["Date", "Open", "High", "Low", "Close", "Volume", "Adj Close", "Dividends"]
        mapping = get_column_mapping('yahoo', df_columns)
        
        assert mapping["Date"] == DATETIME_COLUMN_NAME
        assert mapping["Adj Close"] == ADJ_CLOSE_COLUMN
        assert mapping["Dividends"] == DIVIDENDS_COLUMN
        assert mapping["Open"] == OPEN_COLUMN
        assert mapping["High"] == HIGH_COLUMN
        assert mapping["Low"] == LOW_COLUMN
        assert mapping["Close"] == CLOSE_COLUMN
        assert mapping["Volume"] == VOLUME_COLUMN
    
    def test_get_column_mapping_ibkr(self):
        """Test IBKR column mapping."""
        df_columns = ["date", "open", "high", "low", "close", "volume", "wap", "count"]
        mapping = get_column_mapping('ibkr', df_columns)
        
        assert mapping["date"] == DATETIME_COLUMN_NAME
        assert mapping["wap"] == WAP_COLUMN
        assert mapping["count"] == COUNT_COLUMN
        assert mapping["open"] == OPEN_COLUMN
        assert mapping["high"] == HIGH_COLUMN
        assert mapping["low"] == LOW_COLUMN
        assert mapping["close"] == CLOSE_COLUMN
        assert mapping["volume"] == VOLUME_COLUMN
    
    def test_get_column_mapping_case_insensitive(self):
        """Test case-insensitive column mapping."""
        df_columns = ["TIME", "OPEN", "HIGH", "LOW", "LAST", "VOLUME"]
        mapping = get_column_mapping('barchart', df_columns)
        
        assert mapping["TIME"] == DATETIME_COLUMN_NAME
        assert mapping["LAST"] == CLOSE_COLUMN
        assert mapping["OPEN"] == OPEN_COLUMN
        assert mapping["HIGH"] == HIGH_COLUMN
        assert mapping["LOW"] == LOW_COLUMN
        assert mapping["VOLUME"] == VOLUME_COLUMN
    
    def test_get_column_mapping_with_spaces_and_underscores(self):
        """Test column mapping handles spaces and underscores."""
        df_columns = ["Open_Interest", "open interest", "OpenInterest"]
        
        # Test all variations map to the same constant
        for col in df_columns:
            mapping = get_column_mapping('barchart', [col])
            assert mapping[col] == OPEN_INTEREST_COLUMN
    
    def test_get_column_mapping_unknown_provider(self):
        """Test column mapping for unknown provider."""
        df_columns = ["Date", "Open", "High", "Low", "Close", "Volume"]
        mapping = get_column_mapping('unknown_provider', df_columns)
        
        assert len(mapping) == 0  # Should return empty mapping
    
    def test_standardize_dataframe_columns(self):
        """Test DataFrame column standardization."""
        # Create test DataFrame with Barchart-style columns
        df = pd.DataFrame({
            "Time": ["2024-01-01", "2024-01-02"],
            "Open": [100, 101],
            "High": [105, 106],
            "Low": [98, 99],
            "Last": [102, 103],
            "Volume": [1000, 1100]
        })
        
        standardized_df = standardize_dataframe_columns(df, 'barchart')
        
        # Check that columns were renamed correctly
        assert DATETIME_COLUMN_NAME in standardized_df.columns
        assert CLOSE_COLUMN in standardized_df.columns
        assert "Time" not in standardized_df.columns
        assert "Last" not in standardized_df.columns
        
        # Check that data was preserved
        assert len(standardized_df) == 2
        assert standardized_df[CLOSE_COLUMN].tolist() == [102, 103]
    
    def test_standardize_dataframe_columns_no_mapping(self):
        """Test DataFrame standardization when no mapping is needed."""
        # Create DataFrame with already-standard columns
        df = pd.DataFrame({
            DATETIME_COLUMN_NAME: ["2024-01-01", "2024-01-02"],
            OPEN_COLUMN: [100, 101],
            CLOSE_COLUMN: [102, 103]
        })
        
        standardized_df = standardize_dataframe_columns(df, 'yahoo')
        
        # Should be identical since columns are already standard
        pd.testing.assert_frame_equal(df, standardized_df)


@pytest.mark.unit 
class TestColumnMappingEdgeCases:
    """Test edge cases in column mapping."""
    
    def test_empty_dataframe_columns(self):
        """Test column mapping with empty column list."""
        mapping = get_column_mapping('yahoo', [])
        assert len(mapping) == 0
    
    def test_partial_column_matches(self):
        """Test mapping when only some columns match."""
        df_columns = ["Time", "Price", "SomeOtherColumn"]
        mapping = get_column_mapping('barchart', df_columns)
        
        assert mapping["Time"] == DATETIME_COLUMN_NAME
        assert "Price" not in mapping  # Should not match anything
        assert "SomeOtherColumn" not in mapping
    
    def test_duplicate_column_variations(self):
        """Test handling of duplicate column name variations."""
        df_columns = ["adj close", "Adj Close", "adjclose"]  # Multiple variations
        mapping = get_column_mapping('yahoo', df_columns)
        
        # All should map to the same constant
        for col in df_columns:
            if col in mapping:
                assert mapping[col] == ADJ_CLOSE_COLUMN
    
    def test_case_variations_in_provider_name(self):
        """Test that provider name is case-insensitive."""
        df_columns = ["Time", "Last"]
        
        for provider in ["BARCHART", "Barchart", "barchart", "BarChart"]:
            mapping = get_column_mapping(provider, df_columns)
            assert mapping["Time"] == DATETIME_COLUMN_NAME
            assert mapping["Last"] == CLOSE_COLUMN


@pytest.mark.unit
class TestAdvancedColumnFunctions:
    """Test advanced column functionality."""
    
    def test_standardize_dataframe_columns_strict_mode(self):
        """Test DataFrame standardization in strict mode."""
        # Create DataFrame that actually works without conflicts first
        df = pd.DataFrame({
            "time": ["2024-01-01", "2024-01-02"],
            "open": [100, 101],
            "close": [102, 103]
        })
        
        # Should work in non-strict mode
        result = standardize_dataframe_columns(df, 'barchart', strict=False)
        assert isinstance(result, pd.DataFrame)
        
        # Should also work in strict mode since no conflicts
        result = standardize_dataframe_columns(df, 'barchart', strict=True)
        assert isinstance(result, pd.DataFrame)
    
    def test_standardize_dataframe_columns_with_errors(self):
        """Test DataFrame standardization with errors."""
        # Create DataFrame that will cause errors
        df = pd.DataFrame({"bad_column": [1, 2, 3]})
        
        # Mock the get_column_mapping to raise an exception
        with pytest.raises(ValueError, match="Error in column standardization"):
            # This should trigger error handling
            standardize_dataframe_columns(None, 'invalid_provider', strict=True)
    
    def test_standardize_dataframe_columns_no_mapping_needed(self):
        """Test standardization when no mapping is needed."""
        df = pd.DataFrame({
            DATETIME_COLUMN_NAME: ["2024-01-01", "2024-01-02"],
            OPEN_COLUMN: [100, 101],
            CLOSE_COLUMN: [102, 103]
        })
        
        result = standardize_dataframe_columns(df, 'unknown_provider')
        pd.testing.assert_frame_equal(df, result)


@pytest.mark.unit
class TestColumnDataTypeValidation:
    """Test column data type validation functionality."""
    
    def test_validate_column_data_types_valid_data(self):
        """Test validation with valid data."""
        df = pd.DataFrame({
            OPEN_COLUMN: [100.0, 101.0, 102.0],
            HIGH_COLUMN: [105.0, 106.0, 107.0],
            LOW_COLUMN: [98.0, 99.0, 100.0],
            CLOSE_COLUMN: [102.0, 103.0, 104.0],
            VOLUME_COLUMN: [1000, 1100, 1200]
        })
        df.index = pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"])
        df.index.name = DATETIME_COLUMN_NAME
        
        is_valid, issues = validate_column_data_types(df)
        assert is_valid
        assert len(issues) == 0
    
    def test_validate_column_data_types_invalid_datetime_index(self):
        """Test validation with invalid datetime index."""
        df = pd.DataFrame({
            OPEN_COLUMN: [100.0, 101.0],
            CLOSE_COLUMN: [102.0, 103.0]
        })
        df.index = ["not_datetime", "also_not_datetime"]
        df.index.name = DATETIME_COLUMN_NAME
        
        is_valid, issues = validate_column_data_types(df)
        assert not is_valid
        assert any("should be datetime64" in issue.message for issue in issues)
    
    def test_validate_column_data_types_invalid_price_types(self):
        """Test validation with invalid price column types."""
        df = pd.DataFrame({
            OPEN_COLUMN: ["not_numeric", "also_not_numeric"],
            HIGH_COLUMN: [105.0, 106.0],
            LOW_COLUMN: [98.0, 99.0],
            CLOSE_COLUMN: [102.0, 103.0]
        })
        
        is_valid, issues = validate_column_data_types(df)
        assert not is_valid
        assert any(f"Price column '{OPEN_COLUMN}' should be numeric" in issue.message for issue in issues)
    
    def test_validate_column_data_types_negative_prices(self):
        """Test validation with negative prices."""
        df = pd.DataFrame({
            OPEN_COLUMN: [100.0, -101.0],  # Negative price
            HIGH_COLUMN: [105.0, 106.0],
            LOW_COLUMN: [98.0, -99.0],     # Negative price
            CLOSE_COLUMN: [102.0, 103.0],
            VOLUME_COLUMN: [1000, -1100]   # Negative volume
        })
        
        is_valid, issues = validate_column_data_types(df)
        assert not is_valid
        assert any("negative values" in issue.message for issue in issues)
    
    def test_validate_column_data_types_nan_values(self):
        """Test validation with NaN values in critical columns."""
        import numpy as np
        
        df = pd.DataFrame({
            OPEN_COLUMN: [100.0, np.nan],
            HIGH_COLUMN: [105.0, 106.0],
            LOW_COLUMN: [98.0, 99.0],
            CLOSE_COLUMN: [np.nan, 103.0]
        })
        
        is_valid, issues = validate_column_data_types(df)
        assert not is_valid
        assert any("NaN values" in issue.message for issue in issues)
    
    def test_validate_column_data_types_invalid_ohlc_relationships(self):
        """Test validation with invalid OHLC relationships."""
        df = pd.DataFrame({
            OPEN_COLUMN: [100.0, 101.0],
            HIGH_COLUMN: [95.0, 106.0],   # High < Open (invalid)
            LOW_COLUMN: [110.0, 99.0],   # Low > Open (invalid)
            CLOSE_COLUMN: [102.0, 103.0]
        })
        
        is_valid, issues = validate_column_data_types(df)
        assert not is_valid
        assert any("High <" in issue.message for issue in issues)
        assert any("Low >" in issue.message for issue in issues)
    
    def test_validate_column_data_types_strict_mode(self):
        """Test validation in strict mode raises exceptions."""
        df = pd.DataFrame({
            OPEN_COLUMN: ["not_numeric", "also_not_numeric"]
        })
        
        with pytest.raises(ValueError, match="Column data type validation failed"):
            validate_column_data_types(df, strict=True)
    
    def test_validate_column_data_types_partial_columns(self):
        """Test validation with only some columns present."""
        df = pd.DataFrame({
            OPEN_COLUMN: [100.0, 101.0],
            CLOSE_COLUMN: [102.0, 103.0]
            # Missing HIGH_COLUMN, LOW_COLUMN, VOLUME_COLUMN
        })
        # Set proper datetime index to match internal standard
        df.index = pd.to_datetime(['2024-01-01', '2024-01-02'])
        df.index.name = DATETIME_INDEX_NAME
        
        is_valid, issues = validate_column_data_types(df)
        assert is_valid  # Should pass since only validates present columns
        assert len(issues) == 0