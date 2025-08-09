#!/usr/bin/env python3
"""
Test overlapping download ranges to verify deduplication behavior.

This test verifies that when two consecutive downloads have intersecting date ranges,
duplicate rows are properly deduplicated and the final row count is correct.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock
import tempfile
import os

from src.vortex.models.price_series import PriceSeries
from src.vortex.models.metadata import Metadata
from src.vortex.models.columns import (
    DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN
)
from src.vortex.models.period import Period


class TestOverlappingDownloads:
    """Test suite for overlapping download scenarios."""

    @pytest.fixture
    def sample_period(self):
        """Create a mock period for testing."""
        period = Mock()
        period.get_bar_time_delta.return_value = timedelta(days=1)
        period.__str__ = Mock(return_value="1d")
        return period

    def create_sample_data(self, start_date, num_days, base_price=100):
        """Create sample OHLCV data for testing."""
        dates = pd.date_range(start_date, periods=num_days, freq='D', tz='UTC')
        
        data = []
        for i, date in enumerate(dates):
            price = base_price + i
            data.append({
                OPEN_COLUMN: price,
                HIGH_COLUMN: price + 5,
                LOW_COLUMN: price - 5,
                CLOSE_COLUMN: price + 4,
                VOLUME_COLUMN: 1000 + (i * 100)
            })
        
        df = pd.DataFrame(data, index=dates)
        df.index.name = DATE_TIME_COLUMN
        return df

    def create_price_series(self, df, symbol='TEST', data_provider='test_provider', period=None):
        """Create a PriceSeries instance from DataFrame."""
        if period is None:
            period = Mock()
            period.get_bar_time_delta.return_value = timedelta(days=1)
            period.__str__ = Mock(return_value="1d")
        
        start_date = df.index[0].to_pydatetime()
        end_date = df.index[-1].to_pydatetime()
        
        metadata = Metadata(
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            first_row_date=start_date,
            last_row_date=end_date,
            data_provider=data_provider
        )
        
        return PriceSeries(df=df, metadata=metadata)

    def test_df_merge_no_overlap(self, sample_period):
        """Test df_merge with no overlapping data."""
        # First dataset: Jan 1-5, 2024
        df1 = self.create_sample_data('2024-01-01', 5, base_price=100)
        
        # Second dataset: Jan 6-10, 2024 (no overlap)
        df2 = self.create_sample_data('2024-01-06', 5, base_price=105)
        
        merged_df = PriceSeries.df_merge(df1, df2)
        
        # Should have 10 total rows (5 + 5, no duplicates to remove)
        assert len(merged_df) == 10
        assert merged_df.index.is_monotonic_increasing
        
        # Check first and last dates
        assert merged_df.index[0].date() == datetime(2024, 1, 1).date()
        assert merged_df.index[-1].date() == datetime(2024, 1, 10).date()

    def test_df_merge_complete_overlap(self, sample_period):
        """Test df_merge with completely overlapping data (identical ranges)."""
        # First dataset: Jan 1-5, 2024
        df1 = self.create_sample_data('2024-01-01', 5, base_price=100)
        
        # Second dataset: Jan 1-5, 2024 (complete overlap, different prices)
        df2 = self.create_sample_data('2024-01-01', 5, base_price=200)
        
        merged_df = PriceSeries.df_merge(df1, df2, keep='last')
        
        # Should have 5 total rows (duplicates removed, keeping 'last')
        assert len(merged_df) == 5
        assert merged_df.index.is_monotonic_increasing
        
        # Check that we kept the 'last' values (from df2 with base_price=200)
        assert merged_df.iloc[0]['Open'] == 200  # Should be from df2
        assert merged_df.iloc[-1]['Open'] == 204  # Should be from df2

    def test_df_merge_partial_overlap(self, sample_period):
        """Test df_merge with partial overlapping data."""
        # First dataset: Jan 1-7, 2024 (7 days)
        df1 = self.create_sample_data('2024-01-01', 7, base_price=100)
        
        # Second dataset: Jan 5-10, 2024 (6 days, overlaps Jan 5-7)
        df2 = self.create_sample_data('2024-01-05', 6, base_price=200)
        
        merged_df = PriceSeries.df_merge(df1, df2, keep='last')
        
        # Should have 10 unique dates total:
        # Jan 1-4 from df1 (4 days)
        # Jan 5-7 from df2 (3 days, duplicates removed keeping 'last')  
        # Jan 8-10 from df2 (3 days)
        # Total: 4 + 3 + 3 = 10 days
        assert len(merged_df) == 10
        assert merged_df.index.is_monotonic_increasing
        
        # Check date range
        assert merged_df.index[0].date() == datetime(2024, 1, 1).date()
        assert merged_df.index[-1].date() == datetime(2024, 1, 10).date()
        
        # Check that overlapping dates have values from df2 (base_price=200)
        jan5_row = merged_df[merged_df.index.date == datetime(2024, 1, 5).date()]
        assert len(jan5_row) == 1
        assert jan5_row.iloc[0]['Open'] == 200  # Should be from df2
        
        # Check that non-overlapping dates from df1 are preserved
        jan2_row = merged_df[merged_df.index.date == datetime(2024, 1, 2).date()]
        assert len(jan2_row) == 1
        assert jan2_row.iloc[0]['Open'] == 101  # Should be from df1

    def test_merge_method_with_overlap(self, sample_period):
        """Test the PriceSeries.merge() method with overlapping data."""
        # Create first price series: Jan 1-7, 2024
        df1 = self.create_sample_data('2024-01-01', 7, base_price=100)
        series1 = self.create_price_series(df1, period=sample_period)
        
        # Create second price series: Jan 5-10, 2024 (overlaps Jan 5-7)
        df2 = self.create_sample_data('2024-01-05', 6, base_price=200)
        series2 = self.create_price_series(df2, period=sample_period)
        
        # Merge series2 into series1 (series2 is the "existing" download)
        merged_series = series1.merge(series2)
        
        # Check that we got a new PriceSeries instance, not the original
        assert merged_series is not series1
        assert merged_series is not series2
        
        # Check row count
        assert len(merged_series.df) == 10
        
        # Check metadata is updated correctly
        assert merged_series.metadata.start_date.date() == datetime(2024, 1, 1).date()
        assert merged_series.metadata.end_date.date() == datetime(2024, 1, 10).date()
        
        # Check that data is properly merged and deduplicated
        assert merged_series.df.index.is_monotonic_increasing
        
        # Verify no duplicate timestamps
        assert len(merged_series.df.index) == len(merged_series.df.index.unique())

    def test_consecutive_overlapping_downloads_scenario(self, sample_period):
        """
        Test realistic scenario: two consecutive downloads with overlapping ranges.
        
        Simulates:
        1. First download: Jan 1-10, 2024 (gets 10 days of data)
        2. Second download: Jan 8-15, 2024 (overlaps Jan 8-10, adds Jan 11-15)
        Expected result: 15 unique days total (Jan 1-15)
        """
        
        # First download: Jan 1-10, 2024
        df1 = self.create_sample_data('2024-01-01', 10, base_price=100)
        series1 = self.create_price_series(df1, symbol='AAPL', period=sample_period)
        
        print(f"First download: {len(series1.df)} rows from {series1.metadata.start_date.date()} to {series1.metadata.end_date.date()}")
        
        # Second download: Jan 8-15, 2024 (3 days overlap + 5 new days)
        df2 = self.create_sample_data('2024-01-08', 8, base_price=300)  # Different base price to verify dedup logic
        series2 = self.create_price_series(df2, symbol='AAPL', period=sample_period)
        
        print(f"Second download: {len(series2.df)} rows from {series2.metadata.start_date.date()} to {series2.metadata.end_date.date()}")
        
        # Merge second download with first (series1 is "existing", series2 is "new")
        merged_series = series2.merge(series1)
        
        print(f"Merged result: {len(merged_series.df)} rows from {merged_series.metadata.start_date.date()} to {merged_series.metadata.end_date.date()}")
        
        # Should have 15 unique days total (Jan 1-15, 2024)
        assert len(merged_series.df) == 15, f"Expected 15 rows, got {len(merged_series.df)}"
        
        # Check date range
        assert merged_series.metadata.start_date.date() == datetime(2024, 1, 1).date()
        assert merged_series.metadata.end_date.date() == datetime(2024, 1, 15).date()
        
        # Verify no duplicate timestamps
        assert len(merged_series.df.index) == len(merged_series.df.index.unique())
        
        # Check that overlapping days have values from the new download (keep='last')
        # Jan 8 should have values from series2 (base_price=300)
        jan8_row = merged_series.df[merged_series.df.index.date == datetime(2024, 1, 8).date()]
        assert len(jan8_row) == 1
        assert jan8_row.iloc[0]['Open'] == 300, f"Jan 8 Open price should be 300, got {jan8_row.iloc[0]['Open']}"
        
        # Jan 5 should have values from series1 (base_price=100, index 4)
        jan5_row = merged_series.df[merged_series.df.index.date == datetime(2024, 1, 5).date()]
        assert len(jan5_row) == 1
        assert jan5_row.iloc[0]['Open'] == 104, f"Jan 5 Open price should be 104, got {jan5_row.iloc[0]['Open']}"
        
        # Jan 12 should have values from series2 (base_price=300, index 4 in series2)
        jan12_row = merged_series.df[merged_series.df.index.date == datetime(2024, 1, 12).date()]
        assert len(jan12_row) == 1
        assert jan12_row.iloc[0]['Open'] == 304, f"Jan 12 Open price should be 304, got {jan12_row.iloc[0]['Open']}"

    def test_edge_case_single_day_overlap(self, sample_period):
        """Test edge case with single day overlap."""
        # First dataset: Jan 1-5, 2024
        df1 = self.create_sample_data('2024-01-01', 5, base_price=100)
        
        # Second dataset: Jan 5-8, 2024 (single day overlap on Jan 5)
        df2 = self.create_sample_data('2024-01-05', 4, base_price=200)
        
        merged_df = PriceSeries.df_merge(df1, df2, keep='last')
        
        # Should have 8 unique dates (Jan 1-8)
        assert len(merged_df) == 8
        
        # Jan 5 should have values from df2
        jan5_row = merged_df[merged_df.index.date == datetime(2024, 1, 5).date()]
        assert jan5_row.iloc[0]['Open'] == 200

    def test_dedup_with_different_keep_strategies(self, sample_period):
        """Test deduplication with different 'keep' strategies."""
        # Create overlapping data
        df1 = self.create_sample_data('2024-01-01', 5, base_price=100)
        df2 = self.create_sample_data('2024-01-03', 5, base_price=200)  # Overlaps Jan 3-5
        
        # Test keep='first'
        merged_first = PriceSeries.df_merge(df1, df2, keep='first')
        jan3_first = merged_first[merged_first.index.date == datetime(2024, 1, 3).date()]
        assert jan3_first.iloc[0]['Open'] == 102  # From df1
        
        # Test keep='last' 
        merged_last = PriceSeries.df_merge(df1, df2, keep='last')
        jan3_last = merged_last[merged_last.index.date == datetime(2024, 1, 3).date()]
        assert jan3_last.iloc[0]['Open'] == 200  # From df2
        
        # Both should have same number of unique dates
        assert len(merged_first) == len(merged_last) == 7  # Jan 1-7


if __name__ == '__main__':
    # Run the tests
    test_instance = TestOverlappingDownloads()
    
    # Create sample period mock
    sample_period = Mock()
    sample_period.get_bar_time_delta.return_value = timedelta(days=1)
    sample_period.__str__ = Mock(return_value="1d")
    
    print("🧪 Testing overlapping download deduplication...")
    
    try:
        # Run individual tests
        print("\n1. Testing no overlap scenario...")
        test_instance.test_df_merge_no_overlap(sample_period)
        print("✅ No overlap test passed")
        
        print("\n2. Testing complete overlap scenario...")
        test_instance.test_df_merge_complete_overlap(sample_period)
        print("✅ Complete overlap test passed")
        
        print("\n3. Testing partial overlap scenario...")
        test_instance.test_df_merge_partial_overlap(sample_period)
        print("✅ Partial overlap test passed")
        
        print("\n4. Testing merge method with overlap...")
        test_instance.test_merge_method_with_overlap(sample_period)
        print("✅ Merge method test passed")
        
        print("\n5. Testing realistic consecutive downloads scenario...")
        test_instance.test_consecutive_overlapping_downloads_scenario(sample_period)
        print("✅ Consecutive downloads test passed")
        
        print("\n6. Testing single day overlap edge case...")
        test_instance.test_edge_case_single_day_overlap(sample_period)
        print("✅ Single day overlap test passed")
        
        print("\n7. Testing different keep strategies...")
        test_instance.test_dedup_with_different_keep_strategies(sample_period)
        print("✅ Keep strategies test passed")
        
        print("\n🎉 All deduplication tests passed!")
        print("\n📋 Summary:")
        print("• Overlapping download ranges are properly deduplicated")
        print("• Row counts are correct after merge operations")
        print("• The 'keep=last' strategy preserves newer data in overlaps")
        print("• Both df_merge() and merge() methods work correctly")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()