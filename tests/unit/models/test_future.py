import pytest
import calendar
from datetime import datetime, timedelta
import pytz

from vortex.models.future import Future


class TestFuture:
    def test_future_creation(self):
        """Test basic Future creation and post_init logic."""
        tick_date = datetime(2024, 1, 15)
        future = Future(
            id='GC_H24',
            futures_code='GC',
            year=2024,
            month_code='H',
            tick_date=tick_date,
            days_count=90
        )
        
        assert future.id == 'GC_H24'
        assert future.futures_code == 'GC'
        assert future.year == 2024
        assert future.month_code == 'H'
        assert future.month == 3  # H = March
        assert future.symbol == 'GCH24'  # futures_code + month_code + year_code
        assert future.tick_date == tick_date
        assert future.days_count == 90

    def test_future_symbol_generation(self):
        """Test symbol generation with different years."""
        future_2024 = Future(
            id='ES_U24',
            futures_code='ES',
            year=2024,
            month_code='U',
            tick_date=datetime(2024, 1, 1),
            days_count=90
        )
        
        future_2025 = Future(
            id='ES_U25',
            futures_code='ES',
            year=2025,
            month_code='U',
            tick_date=datetime(2025, 1, 1),
            days_count=90
        )
        
        assert future_2024.symbol == 'ESU24'
        assert future_2025.symbol == 'ESU25'

    def test_str_representation(self):
        """Test string representation of Future."""
        future = Future(
            id='CL_M24',
            futures_code='CL',
            year=2024,
            month_code='M',
            tick_date=datetime(2024, 1, 1),
            days_count=60
        )
        
        result = str(future)
        assert result == 'F|CL_M24|CLM24'

    def test_is_dated(self):
        """Test that futures are always dated."""
        future = Future(
            id='GC_Z24',
            futures_code='GC',
            year=2024,
            month_code='Z',
            tick_date=datetime(2024, 1, 1),
            days_count=90
        )
        
        assert future.is_dated() is True

    def test_get_code(self):
        """Test get_code method returns futures_code."""
        future = Future(
            id='NG_H24',
            futures_code='NG',
            year=2024,
            month_code='H',
            tick_date=datetime(2024, 1, 1),
            days_count=60
        )
        
        assert future.get_code() == 'NG'

    def test_get_symbol(self):
        """Test get_symbol method returns generated symbol."""
        future = Future(
            id='ZC_K24',
            futures_code='ZC',
            year=2024,
            month_code='K',
            tick_date=datetime(2024, 1, 1),
            days_count=120
        )
        
        assert future.get_symbol() == 'ZCK24'

    def test_get_date_range(self):
        """Test get_date_range method."""
        future = Future(
            id='GC_H24',
            futures_code='GC',
            year=2024,
            month_code='H',  # March
            tick_date=datetime(2024, 1, 1),
            days_count=90
        )
        
        tz = pytz.timezone('US/Central')
        start, end = future.get_date_range(tz)
        
        # End should be last day of March 2024
        expected_end_day = calendar.monthrange(2024, 3)[1]  # 31
        expected_end = tz.localize(datetime(2024, 3, expected_end_day))
        
        # Start should be 90 days before end
        expected_start = tz.localize(datetime(2024, 3, expected_end_day) - timedelta(days=90))
        
        assert start == expected_start
        assert end == expected_end
        assert start.tzinfo.zone == tz.zone
        assert end.tzinfo.zone == tz.zone

    def test_get_date_range_leap_year_february(self):
        """Test get_date_range with February in leap year."""
        future = Future(
            id='GC_G24',
            futures_code='GC',
            year=2024,  # Leap year
            month_code='G',  # February
            tick_date=datetime(2024, 1, 1),
            days_count=60
        )
        
        tz = pytz.timezone('UTC')
        start, end = future.get_date_range(tz)
        
        # February 2024 has 29 days (leap year)
        expected_end = tz.localize(datetime(2024, 2, 29))
        expected_start = tz.localize(datetime(2024, 2, 29) - timedelta(days=60))
        
        assert start == expected_start
        assert end == expected_end

    def test_get_date_range_non_leap_year_february(self):
        """Test get_date_range with February in non-leap year."""
        future = Future(
            id='GC_G23',
            futures_code='GC',
            year=2023,  # Non-leap year
            month_code='G',  # February
            tick_date=datetime(2023, 1, 1),
            days_count=60
        )
        
        tz = pytz.timezone('UTC')
        start, end = future.get_date_range(tz)
        
        # February 2023 has 28 days (non-leap year)
        expected_end = tz.localize(datetime(2023, 2, 28))
        expected_start = tz.localize(datetime(2023, 2, 28) - timedelta(days=60))
        
        assert start == expected_start
        assert end == expected_end

    def test_get_code_for_month_all_months(self):
        """Test get_code_for_month for all 12 months."""
        expected_codes = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']
        
        for month in range(1, 13):
            code = Future.get_code_for_month(month)
            assert code == expected_codes[month - 1]

    def test_get_month_from_code_all_codes(self):
        """Test get_month_from_code for all month codes."""
        month_codes = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']
        expected_months = list(range(1, 13))
        
        for i, code in enumerate(month_codes):
            month = Future.get_month_from_code(code)
            assert month == expected_months[i]

    def test_get_code_for_year_various_years(self):
        """Test get_code_for_year for various years."""
        test_cases = [
            (2024, '24'),
            (2023, '23'),
            (2030, '30'),
            (2000, '00'),
            (2009, '09'),
            (1999, '99')
        ]
        
        for year, expected_code in test_cases:
            code = Future.get_code_for_year(year)
            assert code == expected_code

    def test_month_code_month_consistency(self):
        """Test that month_code and calculated month are consistent."""
        for month_code in Future.MONTH_LIST:
            future = Future(
                id=f'TEST_{month_code}24',
                futures_code='TEST',
                year=2024,
                month_code=month_code,
                tick_date=datetime(2024, 1, 1),
                days_count=90
            )
            
            # Verify that month_code -> month -> month_code is consistent
            calculated_month = Future.get_month_from_code(month_code)
            reverse_code = Future.get_code_for_month(calculated_month)
            
            assert future.month == calculated_month
            assert reverse_code == month_code

    def test_all_month_codes_valid(self):
        """Test that all predefined month codes are valid."""
        expected_codes = ['F', 'G', 'H', 'J', 'K', 'M', 'N', 'Q', 'U', 'V', 'X', 'Z']
        assert Future.MONTH_LIST == expected_codes
        assert len(Future.MONTH_LIST) == 12

    def test_symbol_generation_edge_cases(self):
        """Test symbol generation with edge cases."""
        # Test with single digit year codes
        future_2000 = Future(
            id='TEST_F00',
            futures_code='TEST',
            year=2000,
            month_code='F',
            tick_date=datetime(2000, 1, 1),
            days_count=30
        )
        assert future_2000.symbol == 'TESTF00'
        
        # Test with long futures code
        future_long = Future(
            id='LONGCODE_Z24',
            futures_code='LONGCODE',
            year=2024,
            month_code='Z',
            tick_date=datetime(2024, 1, 1),
            days_count=30
        )
        assert future_long.symbol == 'LONGCODEZ24'

    def test_date_range_with_different_timezones(self):
        """Test get_date_range with different timezones."""
        future = Future(
            id='ES_M24',
            futures_code='ES',
            year=2024,
            month_code='M',  # June
            tick_date=datetime(2024, 1, 1),
            days_count=60
        )
        
        # Test with different timezones
        timezones = [
            pytz.timezone('US/Eastern'),
            pytz.timezone('Europe/London'),
            pytz.timezone('Asia/Tokyo'),
            pytz.UTC
        ]
        
        for tz in timezones:
            start, end = future.get_date_range(tz)
            
            # Both dates should have the same timezone
            assert start.tzinfo.zone == tz.zone
            assert end.tzinfo.zone == tz.zone
            
            # The time difference should be 60 days
            assert (end - start).days == 60
            
            # End should be last day of June 2024
            assert end.month == 6
            assert end.year == 2024
            assert end.day == 30  # June has 30 days