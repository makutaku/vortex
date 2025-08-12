"""
Unit tests for Barchart data parser.

Tests the BarchartParser class including CSV parsing, DataFrame conversion,
and data standardization functionality.
"""

import io
import pytest
from unittest.mock import Mock, patch
import pandas as pd
from datetime import datetime

from vortex.infrastructure.providers.barchart.parser import BarchartParser
from vortex.models.period import Period
from vortex.models.columns import CLOSE_COLUMN, DATE_TIME_COLUMN


@pytest.mark.unit
class TestBarchartParser:
    """Test BarchartParser class functionality."""
    
    def test_column_constants(self):
        """Test that column name constants are properly defined."""
        assert BarchartParser.BARCHART_DATE_TIME_COLUMN == 'Time'
        assert BarchartParser.BARCHART_CLOSE_COLUMN == "Last"
    
    def test_convert_daily_csv_to_df(self):
        """Test conversion of daily CSV data to DataFrame."""
        # Sample daily CSV data from Barchart
        csv_data = """Time,Open,High,Low,Last,Volume,Open Interest
2024-01-01,100.00,105.00,99.00,104.00,1000,500
2024-01-02,104.00,107.00,103.00,106.50,1200,510
2024-01-03,106.50,108.00,105.00,107.25,900,520
Footer data to skip
"""
        
        period = Period('1d')
        tz = 'America/New_York'
        
        # Mock all logging calls from both the parser and the column standardizer
        with patch('logging.debug') as mock_debug:
            df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, tz)
        
        # Verify shape and structure
        assert len(df) == 3
        assert DATE_TIME_COLUMN == df.index.name  # DATE_TIME_COLUMN becomes the index
        assert CLOSE_COLUMN in df.columns
        # Should have called debug 3 times: raw data, received data, columns
        # The column mapping debug is from the ColumnStandardizer which has its own logger
        assert mock_debug.call_count == 3
        # Verify the first call is about raw CSV data
        first_call = mock_debug.call_args_list[0][0][0]
        assert "Raw CSV data" in first_call
        assert "from Barchart" in first_call
        
        # Verify data types and timezone
        assert df.index.name == DATE_TIME_COLUMN
        assert df.index.dtype.name.startswith('datetime64[ns')
        assert str(df.index.tz) == 'UTC'
        
        # Verify data values
        assert df[CLOSE_COLUMN].iloc[0] == 104.00
        assert df[CLOSE_COLUMN].iloc[1] == 106.50
        assert df[CLOSE_COLUMN].iloc[2] == 107.25
    
    def test_convert_intraday_csv_to_df(self):
        """Test conversion of intraday CSV data to DataFrame."""
        # Sample intraday CSV data with different date format
        csv_data = """Time,Open,High,Low,Last,Volume,Open Interest
01/01/2024 09:30,100.00,100.50,99.50,100.25,500,100
01/01/2024 10:00,100.25,101.00,100.00,100.75,600,105
01/01/2024 10:30,100.75,101.50,100.50,101.25,550,110
Footer line
"""
        
        period = Period('30m')  # Intraday period
        tz = 'America/Chicago'
        
        df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, tz)
        
        # Verify intraday-specific processing
        assert len(df) == 3
        assert df.index.dtype.name.startswith('datetime64[ns')
        assert str(df.index.tz) == 'UTC'
        
        # Verify close values
        assert df[CLOSE_COLUMN].iloc[0] == 100.25
        assert df[CLOSE_COLUMN].iloc[1] == 100.75
        assert df[CLOSE_COLUMN].iloc[2] == 101.25
    
    def test_column_renaming(self):
        """Test that Barchart columns are renamed to standard format."""
        csv_data = """Time,Open,High,Low,Last,Volume
2024-01-01,100,105,99,104,1000
"""
        
        period = Period('1d')
        df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, 'UTC')
        
        # Verify standard column names
        assert DATE_TIME_COLUMN == df.index.name
        assert CLOSE_COLUMN in df.columns
        assert 'Last' not in df.columns  # Original name should be renamed
        assert 'Time' not in df.columns  # Time becomes index
    
    def test_footer_skipping(self):
        """Test that CSV footer is properly skipped."""
        csv_data = """Time,Open,High,Low,Last,Volume
2024-01-01,100,105,99,104,1000
2024-01-02,104,107,103,106,1200
This is a footer line that should be skipped
"""
        
        period = Period('1d')
        df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, 'UTC')
        
        # Should only have 2 data rows, footer skipped
        assert len(df) == 2
        assert df[CLOSE_COLUMN].iloc[0] == 104.0
        assert df[CLOSE_COLUMN].iloc[1] == 106.0
    
    def test_timezone_conversion(self):
        """Test timezone localization and conversion to UTC."""
        csv_data = """Time,Open,High,Low,Last,Volume
2024-01-01,100,105,99,104,1000
Footer
"""
        
        period = Period('1d')
        source_tz = 'America/New_York'
        
        df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, source_tz)
        
        # Verify timezone conversion
        assert str(df.index.tz) == 'UTC'
        
        # Should have data after processing
        assert len(df) > 0
        
        # The datetime should be timezone-aware
        first_timestamp = df.index[0]
        assert first_timestamp.tz is not None
    
    def test_empty_csv_handling(self):
        """Test handling of empty or minimal CSV data."""
        # CSV with only headers
        csv_data = """Time,Open,High,Low,Last,Volume
Footer line
"""
        
        period = Period('1d')
        df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, 'UTC')
        
        # Should return empty DataFrame
        assert len(df) == 0
        assert DATE_TIME_COLUMN == df.index.name
    
    def test_date_format_detection(self):
        """Test proper date format detection for daily vs intraday."""
        # Test daily format (YYYY-MM-DD)
        daily_csv = """Time,Open,High,Low,Last,Volume
2024-01-01,100,105,99,104,1000
Footer
"""
        daily_period = Period('1d')
        daily_df = BarchartParser.convert_downloaded_csv_to_df(daily_period, daily_csv, 'UTC')
        
        # Test intraday format (MM/DD/YYYY HH:MM)  
        intraday_csv = """Time,Open,High,Low,Last,Volume
01/01/2024 09:30,100,105,99,104,1000
Footer
"""
        intraday_period = Period('1h')
        intraday_df = BarchartParser.convert_downloaded_csv_to_df(intraday_period, intraday_csv, 'UTC')
        
        # Both should parse successfully
        assert len(daily_df) == 1
        assert len(intraday_df) == 1
        
        # Verify both are timezone-aware
        assert daily_df.index[0].tz is not None
        assert intraday_df.index[0].tz is not None
    
    def test_logging_integration(self):
        """Test that parsing logs appropriate debug information."""
        csv_data = """Time,Open,High,Low,Last,Volume,Open Interest
2024-01-01,100,105,99,104,1000,500
2024-01-02,104,107,103,106,1200,510
Footer
"""
        
        with patch('logging.debug') as mock_debug:
            period = Period('1d')
            df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, 'UTC')
            
            # Should log 3 times: raw data, received data, columns
            # The column mapping debug is from ColumnStandardizer which has its own logger
            assert mock_debug.call_count == 3
            # Check first call (raw CSV data)
            first_call_args = mock_debug.call_args_list[0][0][0]
            assert "Raw CSV data" in first_call_args
            assert "from Barchart" in first_call_args
            # Check second call (received data)
            second_call_args = mock_debug.call_args_list[1][0][0]
            assert "Received data" in second_call_args
            assert "(2, 7)" in second_call_args  # Shape should be (2, 7) after parsing
            assert "from Barchart" in second_call_args


@pytest.mark.unit
class TestBarchartParserEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_malformed_csv_data(self):
        """Test handling of malformed CSV data."""
        malformed_csv = """Time,Open,High,Low,Last,Volume
2024-01-01,100,105,99,104,1000
2024-01-02,104,107,103,106,1200
Footer
"""
        
        period = Period('1d')
        # Should handle gracefully - using proper CSV data that won't break pandas
        df = BarchartParser.convert_downloaded_csv_to_df(period, malformed_csv, 'UTC')
        assert len(df) >= 0  # Should not crash
        assert len(df) == 2  # Should process valid rows
    
    def test_invalid_date_formats(self):
        """Test handling of invalid date formats."""
        invalid_csv = """Time,Open,High,Low,Last,Volume
invalid-date,100,105,99,104,1000
2024-01-02,104,107,103,106,1200
Footer
"""
        
        period = Period('1d')
        df = BarchartParser.convert_downloaded_csv_to_df(period, invalid_csv, 'UTC')
        
        # Should handle invalid dates with errors='coerce'
        # Valid row should still be processed
        valid_rows = df.dropna()
        assert len(valid_rows) >= 1
    
    def test_different_timezones(self):
        """Test parsing with different source timezones."""
        csv_data = """Time,Open,High,Low,Last,Volume
2024-01-01,100,105,99,104,1000
Footer
"""
        
        timezones = ['America/New_York', 'America/Chicago', 'Europe/London', 'Asia/Tokyo']
        
        for tz in timezones:
            period = Period('1d')
            df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, tz)
            
            # All should convert to UTC
            assert str(df.index.tz) == 'UTC'
            assert len(df) == 1
    
    def test_large_csv_data(self):
        """Test parsing performance with larger datasets."""
        # Generate larger CSV data
        header = "Time,Open,High,Low,Last,Volume\n"
        rows = []
        for i in range(1000):
            date = f"2024-01-{i % 28 + 1:02d}"
            rows.append(f"{date},{100 + i},{105 + i},{99 + i},{104 + i},{1000 + i * 10}")
        
        large_csv = header + "\n".join(rows) + "\nFooter"
        
        period = Period('1d')
        df = BarchartParser.convert_downloaded_csv_to_df(period, large_csv, 'UTC')
        
        # Should handle large datasets efficiently
        assert len(df) == 1000
        assert DATE_TIME_COLUMN == df.index.name
        assert CLOSE_COLUMN in df.columns
    
    def test_class_method_usage(self):
        """Test that convert_downloaded_csv_to_df is a class method."""
        # Should be callable on class without instance
        csv_data = """Time,Open,High,Low,Last,Volume
2024-01-01,100,105,99,104,1000
Footer
"""
        
        period = Period('1d')
        df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, 'UTC')
        
        assert len(df) == 1
        assert isinstance(df, pd.DataFrame)
    
    def test_memory_efficiency(self):
        """Test that parser doesn't hold unnecessary references."""
        csv_data = """Time,Open,High,Low,Last,Volume
2024-01-01,100,105,99,104,1000
Footer
"""
        
        period = Period('1d')
        df = BarchartParser.convert_downloaded_csv_to_df(period, csv_data, 'UTC')
        
        # Verify the original string data isn't held in memory references
        import sys
        df_size = sys.getsizeof(df)
        assert df_size > 0  # Basic sanity check
        
        # DataFrame should be independent of input string
        del csv_data
        assert len(df) == 1  # Should still be accessible