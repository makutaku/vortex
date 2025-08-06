import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock

from vortex.models.price_series import (
    PriceSeries, 
    file_is_placeholder_for_no_hourly_data,
    is_placeholder_for_no_data,
    check_row_date,
    EXPIRATION_THRESHOLD,
    LOW_DATA_THRESHOLD
)
from vortex.models.metadata import Metadata
from vortex.models.columns import DATE_TIME_COLUMN
from vortex.models.period import Period


class TestPriceSeries:
    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame for testing."""
        dates = pd.date_range('2024-01-01', periods=5, freq='D', tz='UTC')
        return pd.DataFrame({
            'Open': [100, 101, 102, 103, 104],
            'High': [105, 106, 107, 108, 109],
            'Low': [95, 96, 97, 98, 99],
            'Close': [104, 105, 106, 107, 108],
            'Volume': [1000, 1100, 1200, 1300, 1400]
        }, index=dates)

    @pytest.fixture
    def sample_metadata(self):
        """Create sample metadata for testing."""
        period = Mock()
        period.get_bar_time_delta.return_value = timedelta(days=1)
        
        return Metadata(
            symbol='TEST',
            period=period,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 5),
            first_row_date=datetime(2024, 1, 1),
            last_row_date=datetime(2024, 1, 5),
            data_provider='test_provider'
        )

    @pytest.fixture
    def price_series(self, sample_df, sample_metadata):
        """Create PriceSeries instance for testing."""
        return PriceSeries(df=sample_df, metadata=sample_metadata)

    def test_str_representation(self, price_series):
        """Test string representation of PriceSeries."""
        result = str(price_series)
        assert "(5, 5)" in result  # DataFrame shape
        assert "TEST" in result    # Symbol from metadata

    def test_is_data_coverage_acceptable_with_empty_df(self, sample_metadata):
        """Test coverage check with empty DataFrame."""
        empty_df = pd.DataFrame()
        price_series = PriceSeries(df=empty_df, metadata=sample_metadata)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        result = price_series.is_data_coverage_acceptable(start_date, end_date)
        assert result is False

    def test_is_data_coverage_acceptable_within_threshold(self, price_series):
        """Test coverage check when data is within acceptable threshold."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        result = price_series.is_data_coverage_acceptable(start_date, end_date)
        assert result is True

    def test_is_data_coverage_acceptable_outside_threshold(self, price_series):
        """Test coverage check when data is outside acceptable threshold."""
        start_date = datetime(2023, 12, 1)  # Much earlier
        end_date = datetime(2024, 2, 1)     # Much later
        
        result = price_series.is_data_coverage_acceptable(start_date, end_date)
        assert result is False

    def test_is_data_coverage_acceptable_with_expiration_threshold(self, sample_df):
        """Test coverage check with expiration threshold logic."""
        # Set up metadata where last_row_date is far behind end_date
        period = Mock()
        period.get_bar_time_delta.return_value = timedelta(days=1)
        
        metadata = Metadata(
            symbol='TEST',
            period=period,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 15),  # End date much later
            first_row_date=datetime(2024, 1, 1),
            last_row_date=datetime(2024, 1, 5),  # Last row date much earlier
            data_provider='test_provider'
        )
        
        price_series = PriceSeries(df=sample_df, metadata=metadata)
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 10)
        
        result = price_series.is_data_coverage_acceptable(start_date, end_date)
        assert result is True  # Should be acceptable due to expiration threshold

    def test_merge_with_none(self, price_series):
        """Test merge with None returns original series."""
        result = price_series.merge(None)
        assert result is price_series

    def test_merge_with_no_overlap(self, sample_df, sample_metadata):
        """Test merge with non-overlapping data."""
        # Create second price series with later dates
        later_dates = pd.date_range('2024-02-01', periods=3, freq='D', tz='UTC')
        later_df = pd.DataFrame({
            'Open': [200, 201, 202],
            'High': [205, 206, 207],
            'Low': [195, 196, 197],
            'Close': [204, 205, 206],
            'Volume': [2000, 2100, 2200]
        }, index=later_dates)
        
        later_metadata = Metadata(
            symbol='TEST',
            period=sample_metadata.period,
            start_date=datetime(2024, 2, 1),
            end_date=datetime(2024, 2, 3),
            first_row_date=datetime(2024, 2, 1),
            last_row_date=datetime(2024, 2, 3),
            data_provider='test_provider'
        )
        
        later_series = PriceSeries(df=later_df, metadata=later_metadata)
        original_series = PriceSeries(df=sample_df, metadata=sample_metadata)
        
        result = original_series.merge(later_series)
        assert result is original_series  # Should return original when no overlap

    def test_merge_basic_functionality(self, sample_df, sample_metadata):
        """Test basic merge functionality."""
        original_series = PriceSeries(df=sample_df, metadata=sample_metadata)
        
        # Test merge with None
        result = original_series.merge(None)
        assert result is original_series
        
        # Test merge with non-overlapping series (should return original)
        later_metadata = Metadata(
            symbol='TEST',
            period=sample_metadata.period,
            start_date=datetime(2024, 2, 1),
            end_date=datetime(2024, 2, 5),
            first_row_date=datetime(2024, 2, 1),
            last_row_date=datetime(2024, 2, 5),
            data_provider='test_provider'
        )
        
        later_dates = pd.date_range('2024-02-01', periods=3, freq='D', tz='UTC')
        later_df = pd.DataFrame({
            'Open': [200, 201, 202],
            'Close': [204, 205, 206]
        }, index=later_dates)
        
        later_series = PriceSeries(df=later_df, metadata=later_metadata)
        result = original_series.merge(later_series)
        assert result is original_series


class TestUtilityFunctions:
    def test_check_row_date_true(self):
        """Test check_row_date with 1970-01-01 date."""
        test_date = datetime(1970, 1, 1)
        result = check_row_date(test_date)
        assert result is True

    def test_check_row_date_false(self):
        """Test check_row_date with non-1970 date."""
        test_date = datetime(2024, 1, 1)
        result = check_row_date(test_date)
        assert result is False

    def test_is_placeholder_for_no_data_true(self):
        """Test is_placeholder_for_no_data with placeholder data."""
        # Create DataFrame with two 1970-01-01 rows
        placeholder_df = pd.DataFrame({
            DATE_TIME_COLUMN: ['1970-01-01T00:00:00+00:00', '1970-01-01T00:00:00+00:00'],
            'Open': [0, 0],
            'Close': [0, 0]
        })
        
        result = is_placeholder_for_no_data(placeholder_df)
        assert result is True

    def test_is_placeholder_for_no_data_false_wrong_length(self):
        """Test is_placeholder_for_no_data with wrong number of rows."""
        # Create DataFrame with three rows
        df = pd.DataFrame({
            DATE_TIME_COLUMN: ['1970-01-01T00:00:00+00:00', '1970-01-01T00:00:00+00:00', '1970-01-01T00:00:00+00:00'],
            'Open': [0, 0, 0],
            'Close': [0, 0, 0]
        })
        
        result = is_placeholder_for_no_data(df)
        assert result is False

    def test_is_placeholder_for_no_data_false_wrong_dates(self):
        """Test is_placeholder_for_no_data with non-placeholder dates."""
        # Create DataFrame with two non-1970 rows
        df = pd.DataFrame({
            DATE_TIME_COLUMN: ['2024-01-01T00:00:00+00:00', '2024-01-02T00:00:00+00:00'],
            'Open': [100, 101],
            'Close': [104, 105]
        })
        
        result = is_placeholder_for_no_data(df)
        assert result is False

    @pytest.fixture
    def temp_csv_file(self, tmp_path):
        """Create temporary CSV file for testing."""
        csv_file = tmp_path / "test.csv"
        return str(csv_file)

    def test_file_is_placeholder_for_no_hourly_data_true(self, temp_csv_file):
        """Test file_is_placeholder_for_no_hourly_data with small placeholder file."""
        # Create small CSV file with placeholder data
        placeholder_content = f"{DATE_TIME_COLUMN},Open,Close\n1970-01-01T00:00:00+00:00,0,0\n1970-01-01T00:00:00+00:00,0,0\n"
        
        with open(temp_csv_file, 'w') as f:
            f.write(placeholder_content)
        
        result = file_is_placeholder_for_no_hourly_data(temp_csv_file)
        assert result is True

    def test_file_is_placeholder_for_no_hourly_data_false_large_file(self, temp_csv_file):
        """Test file_is_placeholder_for_no_hourly_data with large file."""
        # Create large CSV file (over 150 bytes)
        large_content = f"{DATE_TIME_COLUMN},Open,High,Low,Close,Volume\n"
        for i in range(10):
            large_content += f"2024-01-{i+1:02d}T00:00:00+00:00,100,105,95,104,1000\n"
        
        with open(temp_csv_file, 'w') as f:
            f.write(large_content)
        
        result = file_is_placeholder_for_no_hourly_data(temp_csv_file)
        assert result is False

    def test_file_is_placeholder_for_no_hourly_data_false_real_data(self, temp_csv_file):
        """Test file_is_placeholder_for_no_hourly_data with real data in small file."""
        # Create small CSV file with real data (not placeholder)
        real_content = f"{DATE_TIME_COLUMN},Open,Close\n2024-01-01T00:00:00+00:00,100,104\n2024-01-02T00:00:00+00:00,101,105\n"
        
        with open(temp_csv_file, 'w') as f:
            f.write(real_content)
        
        result = file_is_placeholder_for_no_hourly_data(temp_csv_file)
        assert result is False