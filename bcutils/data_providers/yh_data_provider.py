import logging
import os
import tempfile
from datetime import timedelta, datetime, timezone

import pandas as pd
import yfinance as yf
from pandas import DataFrame

from data_providers.data_provider import DataProvider
from instruments.columns import DATE_TIME_COLUMN
from instruments.instrument import Instrument
from instruments.period import Period
from utils.utils import random_sleep


class YahooDataProvider(DataProvider):
    MAX_BARS_PER_DOWNLOAD = 10000
    YAHOO_DATE_TIME_COLUMN = "Date"
    PROVIDER_NAME = "YahooFinance"

    EARLIEST_AVAILABLE_PER_PERIOD = {
        Period.Minute_1: timedelta(days=7),
        Period.Minute_5: timedelta(days=59),
        Period.Minute_15: timedelta(days=59),
        Period.Minute_30: timedelta(days=59),
        Period.Hourly: timedelta(days=729),
        Period.Daily: None,
        Period.Weekly: None,
        Period.Monthly: None,
        Period.Quarterly: None
    }

    def __init__(self, dry_run, random_sleep_in_sec=None):
        self.sleep_random_seconds = random_sleep_in_sec if random_sleep_in_sec > 0 else None
        self.dry_run = dry_run
        YahooDataProvider.set_yf_tz_cache()

    def get_name(self) -> str:
        return YahooDataProvider.PROVIDER_NAME

    def get_max_range(self, period: Period) -> timedelta:
        return period.get_delta_time() * YahooDataProvider.MAX_BARS_PER_DOWNLOAD

    def get_min_start(self, period: Period) -> datetime | None:
        delta = self.EARLIEST_AVAILABLE_PER_PERIOD.get(period, None)
        utcnow = datetime.now(timezone.utc)
        return (utcnow - delta) if delta else None

    def get_supported_timeframes(self, instrument: Instrument) -> list[Period]:
        return list(self.EARLIEST_AVAILABLE_PER_PERIOD.keys())

    def fetch_historical_data(self, instrument: Instrument, period, start, end) -> DataFrame:
        self.pretend_not_a_bot()
        df = YahooDataProvider.fetch_historical_data_for_symbol(instrument.get_symbol(), period, start, end)
        return df

    def pretend_not_a_bot(self):
        if self.sleep_random_seconds is not None:
            # cursory attempt to not appear like a bot
            random_sleep(self.sleep_random_seconds)
        else:
            logging.warning("Random sleep is disabled. Enable to avoid bot detection.")

    @staticmethod
    def fetch_historical_data_for_symbol(symbol: str, period, start_date, end_date) -> DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=YahooDataProvider.to_yahoo_finance_interval(period),
            back_adjust=True,
            repair=True,
            raise_errors=True)

        df.index.name = DATE_TIME_COLUMN
        df.index = pd.to_datetime(df.index, utc=True)
        return df

    @staticmethod
    def to_yahoo_finance_interval(period: Period) -> str:
        yahoo_intervals = {
            Period.Minute_1: '1m',
            Period.Minute_2: '2m',
            Period.Minute_5: '5m',
            Period.Minute_15: '15m',
            Period.Minute_30: '30m',
            Period.Hourly: '1h',
            Period.Daily: '1d',
            Period.Weekly: '1wk',
            Period.Monthly: '1mo',
            Period.Quarterly: '3mo'
        }
        return yahoo_intervals.get(period)

    @staticmethod
    def set_yf_tz_cache():
        # Get the temporary folder for the current user
        temp_folder = tempfile.gettempdir()

        # Create the subfolder "/.cache/py-yfinance" under the temporary folder
        cache_folder = os.path.join(temp_folder, '.cache', 'py-yfinance')
        os.makedirs(cache_folder, exist_ok=True)

        # Set the cache location for timezone data
        yf.set_tz_cache_location(cache_folder)
