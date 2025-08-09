import enum
from dataclasses import dataclass
from datetime import timedelta, datetime, timezone
from vortex.constants import MINUTE_10, MINUTE_15, MINUTE_20, MINUTE_30, DAYS_IN_MONTH_APPROX


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

    def get_bar_time_delta(self):
        time_units = {
            Period.Minute_1: timedelta(minutes=1),
            Period.Minute_2: timedelta(minutes=2),
            Period.Minute_5: timedelta(minutes=5),
            Period.Minute_10: timedelta(minutes=MINUTE_10),
            Period.Minute_15: timedelta(minutes=MINUTE_15),
            Period.Minute_20: timedelta(minutes=MINUTE_20),
            Period.Minute_30: timedelta(minutes=MINUTE_30),
            Period.Hourly: timedelta(hours=1),
            Period.Daily: timedelta(days=1),
            Period.Weekly: timedelta(weeks=1),
            Period.Monthly: timedelta(days=DAYS_IN_MONTH_APPROX),  # Approximate for a month
            Period.Quarterly: timedelta(days=90)  # Approximate for a quarter
        }
        return time_units[self]

    def get_delta_time(self):
        time_units = {
            Period.Minute_1: 24 * timedelta(minutes=1) / 5,
            Period.Minute_2: 24 * timedelta(minutes=2) / 5,
            Period.Minute_5: 24 * timedelta(minutes=5) / 5,
            Period.Minute_10: 24 * timedelta(minutes=MINUTE_10) / 5,
            Period.Minute_15: 24 * timedelta(minutes=MINUTE_15) / 5,
            Period.Minute_20: 24 * timedelta(minutes=MINUTE_20) / 5,
            Period.Minute_30: 24 * timedelta(minutes=MINUTE_30) / 5,
            Period.Hourly: 24 * timedelta(hours=1) / 5,
            Period.Daily: 7 * timedelta(days=1) / 5,
            Period.Weekly: timedelta(weeks=1),
            Period.Monthly: timedelta(days=DAYS_IN_MONTH_APPROX),  # Approximate for a month
            Period.Quarterly: timedelta(days=90)  # Approximate for a quarter
        }
        return time_units[self]

    def is_intraday(self):
        return self.get_delta_time() < Period.Daily.get_delta_time()

    def periods_in_timedelta(self, timedelta_value):
        period_delta = self.get_delta_time()
        return int(timedelta_value / period_delta)

    @staticmethod
    def get_periods_from_str(period_values: str):
        return [Period(val) for val in period_values.split(',')] if period_values else []


@dataclass
class FrequencyAttributes:
    frequency: Period
    min_start: timedelta | datetime | None = None
    max_window: timedelta | None = None
    properties: dict | None = None

    def get_min_start(self) -> datetime | None:

        min_start = self.min_start
        if not min_start:
            return None

        if isinstance(min_start, datetime):
            return min_start

        if not isinstance(min_start, timedelta):
            raise ValueError(min_start)

        return datetime.now(timezone.utc) - min_start

