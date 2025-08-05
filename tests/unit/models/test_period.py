import pytest
from datetime import timedelta, datetime, timezone
from unittest.mock import patch

from vortex.models.period import Period, FrequencyAttributes


class TestPeriod:
    def test_period_enum_values(self):
        """Test that all period enum values have correct string representations."""
        expected_values = {
            Period.Minute_1: '1m',
            Period.Minute_2: '2m',
            Period.Minute_5: '5m',
            Period.Minute_10: '10m',
            Period.Minute_15: '15m',
            Period.Minute_20: '20m',
            Period.Minute_30: '30m',
            Period.Hourly: '1h',
            Period.Daily: '1d',
            Period.Weekly: '1W',
            Period.Monthly: '1M',
            Period.Quarterly: '3M'
        }
        
        for period, expected_str in expected_values.items():
            assert period.value == expected_str
            assert str(period) == expected_str

    def test_get_bar_time_delta_minutes(self):
        """Test get_bar_time_delta for minute-based periods."""
        test_cases = [
            (Period.Minute_1, timedelta(minutes=1)),
            (Period.Minute_2, timedelta(minutes=2)),
            (Period.Minute_5, timedelta(minutes=5)),
            (Period.Minute_10, timedelta(minutes=10)),
            (Period.Minute_15, timedelta(minutes=15)),
            (Period.Minute_20, timedelta(minutes=20)),
            (Period.Minute_30, timedelta(minutes=30))
        ]
        
        for period, expected_delta in test_cases:
            assert period.get_bar_time_delta() == expected_delta

    def test_get_bar_time_delta_larger_periods(self):
        """Test get_bar_time_delta for hour, day, week, month, quarter periods."""
        test_cases = [
            (Period.Hourly, timedelta(hours=1)),
            (Period.Daily, timedelta(days=1)),
            (Period.Weekly, timedelta(weeks=1)),
            (Period.Monthly, timedelta(days=30)),
            (Period.Quarterly, timedelta(days=90))
        ]
        
        for period, expected_delta in test_cases:
            assert period.get_bar_time_delta() == expected_delta

    def test_get_delta_time_minutes(self):
        """Test get_delta_time for minute-based periods."""
        # For minute periods, delta_time = 24 * base_timedelta / 5
        test_cases = [
            (Period.Minute_1, 24 * timedelta(minutes=1) / 5),
            (Period.Minute_2, 24 * timedelta(minutes=2) / 5),
            (Period.Minute_5, 24 * timedelta(minutes=5) / 5),
            (Period.Minute_10, 24 * timedelta(minutes=10) / 5),
            (Period.Minute_15, 24 * timedelta(minutes=15) / 5),
            (Period.Minute_20, 24 * timedelta(minutes=20) / 5),
            (Period.Minute_30, 24 * timedelta(minutes=30) / 5)
        ]
        
        for period, expected_delta in test_cases:
            result = period.get_delta_time()
            assert abs((result - expected_delta).total_seconds()) < 0.001

    def test_get_delta_time_hourly_daily(self):
        """Test get_delta_time for hourly and daily periods."""
        # Hourly: 24 * timedelta(hours=1) / 5
        hourly_expected = 24 * timedelta(hours=1) / 5
        assert abs((Period.Hourly.get_delta_time() - hourly_expected).total_seconds()) < 0.001
        
        # Daily: 7 * timedelta(days=1) / 5
        daily_expected = 7 * timedelta(days=1) / 5
        assert abs((Period.Daily.get_delta_time() - daily_expected).total_seconds()) < 0.001

    def test_get_delta_time_larger_periods(self):
        """Test get_delta_time for week, month, quarter periods."""
        test_cases = [
            (Period.Weekly, timedelta(weeks=1)),
            (Period.Monthly, timedelta(days=30)),
            (Period.Quarterly, timedelta(days=90))
        ]
        
        for period, expected_delta in test_cases:
            assert period.get_delta_time() == expected_delta

    def test_is_intraday(self):
        """Test is_intraday method for different periods."""
        daily_delta = Period.Daily.get_delta_time()
        
        # All minute and hourly periods should be intraday
        intraday_periods = [
            Period.Minute_1, Period.Minute_2, Period.Minute_5,
            Period.Minute_10, Period.Minute_15, Period.Minute_20,
            Period.Minute_30, Period.Hourly
        ]
        
        for period in intraday_periods:
            assert period.is_intraday() is True, f"{period} should be intraday"
        
        # Daily and larger periods should not be intraday
        non_intraday_periods = [
            Period.Daily, Period.Weekly, Period.Monthly, Period.Quarterly
        ]
        
        for period in non_intraday_periods:
            assert period.is_intraday() is False, f"{period} should not be intraday"

    def test_periods_in_timedelta(self):
        """Test periods_in_timedelta method."""
        # Test with Daily period
        daily_period = Period.Daily
        daily_delta = daily_period.get_delta_time()
        
        # Test with a timedelta that's exactly 2 times the period delta
        test_timedelta = 2 * daily_delta
        result = daily_period.periods_in_timedelta(test_timedelta)
        assert result == 2
        
        # Test with Hourly period
        hourly_period = Period.Hourly
        hourly_delta = hourly_period.get_delta_time()
        
        # Test with a timedelta that's 3 times the period delta
        test_timedelta = 3 * hourly_delta
        result = hourly_period.periods_in_timedelta(test_timedelta)
        assert result == 3

    def test_periods_in_timedelta_fractional(self):
        """Test periods_in_timedelta with fractional results."""
        period = Period.Daily
        period_delta = period.get_delta_time()
        
        # Test with 1.5 times the period delta (should return 1 due to int conversion)
        test_timedelta = 1.5 * period_delta
        result = period.periods_in_timedelta(test_timedelta)
        assert result == 1

    def test_get_periods_from_str_valid(self):
        """Test get_periods_from_str with valid string."""
        period_str = '1d,1h,5m'
        result = Period.get_periods_from_str(period_str)
        
        expected = [Period.Daily, Period.Hourly, Period.Minute_5]
        assert result == expected

    def test_get_periods_from_str_single(self):
        """Test get_periods_from_str with single period."""
        period_str = '1d'
        result = Period.get_periods_from_str(period_str)
        
        expected = [Period.Daily]
        assert result == expected

    def test_get_periods_from_str_empty(self):
        """Test get_periods_from_str with empty string."""
        result = Period.get_periods_from_str('')
        assert result == []
        
        result = Period.get_periods_from_str(None)
        assert result == []

    def test_get_periods_from_str_invalid(self):
        """Test get_periods_from_str with invalid period."""
        period_str = '1d,invalid,1h'
        
        with pytest.raises(ValueError):
            Period.get_periods_from_str(period_str)

    def test_period_creation_from_string(self):
        """Test creating Period enum from string values."""
        test_cases = [
            ('1m', Period.Minute_1),
            ('5m', Period.Minute_5),
            ('1h', Period.Hourly),
            ('1d', Period.Daily),
            ('1W', Period.Weekly),
            ('1M', Period.Monthly),
            ('3M', Period.Quarterly)
        ]
        
        for string_val, expected_period in test_cases:
            assert Period(string_val) == expected_period


class TestFrequencyAttributes:
    def test_frequency_attributes_basic(self):
        """Test basic FrequencyAttributes creation."""
        freq_attr = FrequencyAttributes(frequency=Period.Daily)
        
        assert freq_attr.frequency == Period.Daily
        assert freq_attr.min_start is None
        assert freq_attr.max_window is None
        assert freq_attr.properties is None

    def test_frequency_attributes_with_all_fields(self):
        """Test FrequencyAttributes with all fields."""
        min_start = timedelta(days=30)
        max_window = timedelta(days=365)
        properties = {'key': 'value'}
        
        freq_attr = FrequencyAttributes(
            frequency=Period.Hourly,
            min_start=min_start,
            max_window=max_window,
            properties=properties
        )
        
        assert freq_attr.frequency == Period.Hourly
        assert freq_attr.min_start == min_start
        assert freq_attr.max_window == max_window
        assert freq_attr.properties == properties

    def test_get_min_start_none(self):
        """Test get_min_start when min_start is None."""
        freq_attr = FrequencyAttributes(frequency=Period.Daily)
        result = freq_attr.get_min_start()
        assert result is None

    def test_get_min_start_datetime(self):
        """Test get_min_start when min_start is datetime."""
        test_datetime = datetime(2024, 1, 15, tzinfo=timezone.utc)
        freq_attr = FrequencyAttributes(
            frequency=Period.Daily,
            min_start=test_datetime
        )
        
        result = freq_attr.get_min_start()
        assert result == test_datetime

    def test_get_min_start_timedelta(self):
        """Test get_min_start when min_start is timedelta."""
        min_start_delta = timedelta(days=7)
        freq_attr = FrequencyAttributes(
            frequency=Period.Daily,
            min_start=min_start_delta
        )
        
        result = freq_attr.get_min_start()
        
        # Result should be roughly 7 days ago
        now = datetime.now(timezone.utc)
        expected_min = now - min_start_delta - timedelta(seconds=5)  # Allow 5 sec tolerance
        expected_max = now - min_start_delta + timedelta(seconds=5)
        
        assert expected_min <= result <= expected_max

    def test_get_min_start_invalid_type(self):
        """Test get_min_start with invalid min_start type."""
        freq_attr = FrequencyAttributes(
            frequency=Period.Daily,
            min_start="invalid_string"  # Invalid type
        )
        
        with pytest.raises(ValueError):
            freq_attr.get_min_start()

    def test_frequency_attributes_with_timedelta_min_start(self):
        """Test FrequencyAttributes with timedelta min_start."""
        min_start = timedelta(hours=6)
        freq_attr = FrequencyAttributes(
            frequency=Period.Hourly,
            min_start=min_start
        )
        
        assert freq_attr.min_start == min_start
        assert isinstance(freq_attr.min_start, timedelta)

    def test_frequency_attributes_properties_dict(self):
        """Test FrequencyAttributes with complex properties dict."""
        properties = {
            'exchange': 'NYSE',
            'trading_hours': {'open': '09:30', 'close': '16:00'},
            'holidays': ['2024-01-01', '2024-07-04'],
            'decimal_places': 2
        }
        
        freq_attr = FrequencyAttributes(
            frequency=Period.Daily,
            properties=properties
        )
        
        assert freq_attr.properties == properties
        assert freq_attr.properties['exchange'] == 'NYSE'
        assert freq_attr.properties['decimal_places'] == 2