import os
import tempfile
from datetime import timedelta

import pandas as pd
import yfinance as yf
from pandas import DataFrame

from .data_provider import DataProvider
from vortex.models.columns import DATE_TIME_COLUMN
from vortex.models.instrument import Instrument
from vortex.models.period import Period, FrequencyAttributes


class YahooDataProvider(DataProvider):

    YAHOO_DATE_TIME_COLUMN = "Date"
    PROVIDER_NAME = "YahooFinance"

    def __init__(self):
        YahooDataProvider.set_yf_tz_cache()

    def get_name(self) -> str:
        return YahooDataProvider.PROVIDER_NAME

    def _get_frequency_attributes(self) -> list[FrequencyAttributes]:

        return [
            FrequencyAttributes(Period.Monthly,
                                min_start=None,
                                properties={'interval': '1mo'}),
            FrequencyAttributes(Period.Weekly,
                                min_start=None,
                                properties={'interval': '1wk'}),
            FrequencyAttributes(Period.Daily,
                                min_start=None,
                                properties={'interval': '1d'}),
            FrequencyAttributes(Period.Hourly,
                                min_start=timedelta(days=729),
                                properties={'interval': '1h'}),
            FrequencyAttributes(Period.Minute_30,
                                min_start=timedelta(days=59),
                                properties={'interval': '30m'}),
            FrequencyAttributes(Period.Minute_15,
                                min_start=timedelta(days=59),
                                properties={'interval': '15m'}),
            FrequencyAttributes(Period.Minute_5,
                                min_start=timedelta(days=59),
                                properties={'interval': '5m'}),
            FrequencyAttributes(Period.Minute_1,
                                min_start=timedelta(days=7),
                                properties={'interval': '1m'}),
        ]

    def _fetch_historical_data(self, instrument: Instrument,
                               freq_attrs: FrequencyAttributes,
                               start, end) -> DataFrame:
        interval = freq_attrs.properties.get('interval')
        df = YahooDataProvider.fetch_historical_data_for_symbol(instrument.get_symbol(), interval, start, end)
        return df

    @staticmethod
    def fetch_historical_data_for_symbol(symbol: str, interval: str, start_date, end_date) -> DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=interval,
            back_adjust=True,
            repair=True,
            raise_errors=True)

        df.index.name = DATE_TIME_COLUMN
        df.index = pd.to_datetime(df.index, utc=True)
        return df

    @staticmethod
    def set_yf_tz_cache():
        # Get the temporary folder for the current user
        temp_folder = tempfile.gettempdir()

        # Create the subfolder "/.cache/py-yfinance" under the temporary folder
        cache_folder = os.path.join(temp_folder, '.cache', 'py-yfinance')
        os.makedirs(cache_folder, exist_ok=True)

        # Set the cache location for timezone data
        yf.set_tz_cache_location(cache_folder)
