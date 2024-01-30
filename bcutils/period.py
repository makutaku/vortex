import enum



class Period(enum.Enum):
    Minute_1 = '1m'
    Minute_2 = '2m'
    Minute_5 = '5m'
    Minute_15 = '15m'
    Minute_30 = '30m'
    Hourly = '1h'
    Daily = '1d'
    Weekly = '1W'
    Monthly = '1M'
    Quarterly = '3M'

    def to_string(self):
        return self.value

    def max_historical_days(self, max_bars):
        trading_days_per_week = 5
        trading_hours_per_day = 7

        hour_bars_in_period = {
            '1m': 1.0 / 60,
            '2m': 1.0 / 30,
            '5m': 1.0 / 12,
            '15m': 1.0 / 4,
            '30m': 1.0 / 2,
            '1h': 1.0,
            '1d': trading_hours_per_day * 1.0,  # Adjust for trading hours per day
            '1W': trading_days_per_week * trading_hours_per_day * 1.0,  # Adjust for trading hours per day
            '1M': trading_days_per_week * trading_hours_per_day * 1.0 * 4,  # Adjust for trading hours per day
            '3M': trading_days_per_week * trading_hours_per_day * 1.0 * 4 * 3,  # Adjust for trading hours per day
        }

        # Calculate the minimum number of days to cover 10,000 bars
        days_required = max_bars * hour_bars_in_period[self.value] / trading_hours_per_day

        return int(days_required)
