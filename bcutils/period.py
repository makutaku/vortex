import enum
from datetime import timedelta


class Period(enum.Enum):
    Minute_1 = '1m'
    Minute_2 = '2m'
    Minute_5 = '5m'
    Minute_10 = '10m'
    Minute_15 = '15m'
    Minute_20 = '20m'
    Minute_30 = '30m'
    Hourly = '1h'
    Daily = '1d'
    Weekly = '1W'
    Monthly = '1M'
    Quarterly = '3M'

    def __str__(self):
        return self.value

    def get_delta_time(self):
        time_units = {
            Period.Minute_1: 24*timedelta(minutes=1)/5,
            Period.Minute_2: 24*timedelta(minutes=2)/5,
            Period.Minute_5: 24*timedelta(minutes=5)/5,
            Period.Minute_10: 24*timedelta(minutes=10)/5,
            Period.Minute_15: 24*timedelta(minutes=15)/5,
            Period.Minute_20: 24*timedelta(minutes=20)/5,
            Period.Minute_30: 24*timedelta(minutes=30)/5,
            Period.Hourly: 24*timedelta(hours=1)/5,
            Period.Daily: 7*timedelta(days=1)/5,
            Period.Weekly: timedelta(weeks=1),
            Period.Monthly: timedelta(days=30),  # Approximate for a month
            Period.Quarterly: timedelta(days=90)  # Approximate for a quarter
        }
        return time_units[self]

    def periods_in_timedelta(self, timedelta_value):
        period_delta = self.get_delta_time()
        return int(timedelta_value / period_delta)

    @staticmethod
    def get_periods_from_str(period_values: str):
        return [Period(val) for val in period_values.split(',')] if period_values else []
