import logging
import time
from datetime import timedelta, datetime, timezone

import pandas as pd
from ib_insync import IB, util
from pandas import DataFrame

from data_providers.data_provider import DataProvider
from instruments import period
from instruments.columns import DATE_TIME_COLUMN, VOLUME_COLUMN
from instruments.instrument import Instrument
from instruments.period import Period
from instruments.price_series import SOURCE_TIME_ZONE
from utils.utils import random_sleep

TIMEOUT_SECONDS_ON_HISTORICAL_DATA = 60


class IbkrDataProvider(DataProvider):
    MAX_BARS_PER_DOWNLOAD = 10000
    YAHOO_DATE_TIME_COLUMN = "Date"
    PROVIDER_NAME = "InteractiveBrokers"

    EARLIEST_AVAILABLE_PER_PERIOD = {
        Period.Minute_1: timedelta(days=7),
        Period.Minute_5: timedelta(days=90),
        Period.Minute_15: timedelta(days=365),
        Period.Minute_30: timedelta(days=365),
        Period.Hourly: timedelta(days=10*365),
        Period.Daily: None,
        Period.Weekly: None,
        Period.Monthly: None
    }

    def __init__(self, ipaddress, port, dry_run, random_sleep_in_sec=None):
        self.sleep_random_seconds = random_sleep_in_sec if random_sleep_in_sec > 0 else None
        self.dry_run = dry_run

        self.ib = IB()

        client_id = 999
        self.ib.connect(ipaddress, port, clientId=client_id, readonly=True)

        # Sometimes takes a few seconds to resolve... only have to do this once per process so no biggie
        time.sleep(5)

        # logging.debug("Terminating %s" % str(self._ib_connection_config))
        # try:
        #     # Try and disconnect IB client
        #     self.ib.disconnect()
        # except BaseException:
        #     logging.warning("Trying to disconnect IB client failed... ensure process is killed")

    def get_name(self) -> str:
        return IbkrDataProvider.PROVIDER_NAME

    def get_max_range(self, period: Period) -> timedelta:
        return period.get_delta_time() * IbkrDataProvider.MAX_BARS_PER_DOWNLOAD

    def get_min_start(self, period: Period) -> datetime | None:
        delta = self.EARLIEST_AVAILABLE_PER_PERIOD.get(period, None)
        utcnow = datetime.now(timezone.utc)
        return (utcnow - delta) if delta else None

    def get_supported_timeframes(self, instrument: Instrument) -> list[Period]:
        return list(self.EARLIEST_AVAILABLE_PER_PERIOD.keys())

    def fetch_historical_data(self, instrument: Instrument, period, start, end) -> DataFrame:
        self.pretend_not_a_bot()
        df = self.fetch_historical_data_for_symbol(instrument.get_symbol(), period, start, end)
        return df

    def pretend_not_a_bot(self):
        if self.sleep_random_seconds is not None:
            # cursory attempt to not appear like a bot
            random_sleep(self.sleep_random_seconds)
        else:
            logging.warning("Random sleep is disabled. Enable to avoid bot detection.")

    def fetch_historical_data_for_symbol(self, symbol: str, period, start_date, end_date) -> DataFrame:

        from ib_insync import Stock
        stock = Stock(symbol, 'SMART', 'USD')

        ## If live data is available a request for delayed data would be ignored by TWS.
        self.ib.reqMarketDataType(3)
        bars = self.ib.reqHistoricalData(
            stock,
            endDateTime="",
            durationStr=IbkrDataProvider.to_ibkr_finance_duration_str(period),
            barSizeSetting=IbkrDataProvider.to_ibkr_finance_bar_size(period),
            whatToShow='TRADES',
            useRTH=True,
            formatDate=2,
            timeout=TIMEOUT_SECONDS_ON_HISTORICAL_DATA,
        )
        df = util.df(bars)
        logging.debug(f"Received data {df.shape} from {self.get_name()}")

        columns = {
            "date": DATE_TIME_COLUMN,
            "volume": VOLUME_COLUMN,
            "high": "High",
            "low": "Low",
            "open": "Open",
            "close": "Close"
        }
        df = df.rename(columns=columns)

        if not period.is_intraday():
            df[DATE_TIME_COLUMN] = (pd.to_datetime(df[DATE_TIME_COLUMN], format='%Y-%m-%d', errors='coerce')
                                    .dt.tz_localize(SOURCE_TIME_ZONE).dt.tz_convert('UTC'))

        df.set_index(DATE_TIME_COLUMN, inplace=True)

        return df

    @staticmethod
    def to_ibkr_finance_bar_size(period: Period) -> str:
        ibkr_intervals = {
            Period.Minute_1: '1 min',
            Period.Minute_2: '2 mins',
            Period.Minute_5: '5 mins',
            Period.Minute_15: '15 mins',
            Period.Minute_30: '30 mins',
            Period.Hourly: '1 hour',
            Period.Daily: '1 day',
            Period.Weekly: '1 week',
            Period.Monthly: '1 month',
            Period.Quarterly: '3 months'
        }
        return ibkr_intervals.get(period)

    @staticmethod
    def to_ibkr_finance_duration_str(period: Period) -> str:

        duration_lookup = dict(
            [
                (Period.Quarterly, "50 Y"),
                (Period.Monthly, "50 Y"),
                (Period.Weekly, "50 Y"),
                (Period.Daily, "50 Y"),
                (Period.Hourly, "1 Y"),
                (Period.Minute_30, "1 Y"),
                (Period.Minute_15, "1 Y"),
                (Period.Minute_5, "90 D"),
                (Period.Minute_1, "7 D"),
            ]
        )
        return duration_lookup.get(period)
