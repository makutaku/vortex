import logging
import time
from datetime import timedelta, datetime
from functools import singledispatchmethod
from retrying import retry

import pandas as pd
from ib_insync import IB, util
from ib_insync import Stock as IB_Stock, Future as IB_Future, Forex as IB_Forex
from pandas import DataFrame

from data_providers.data_provider import DataProvider
from instruments.columns import DATE_TIME_COLUMN, VOLUME_COLUMN
from instruments.forex import Forex
from instruments.future import Future
from instruments.period import Period, FrequencyAttributes
from instruments.price_series import FUTURES_SOURCE_TIME_ZONE
from instruments.stock import Stock

TIMEOUT_SECONDS_ON_HISTORICAL_DATA = 120


class IbkrDataProvider(DataProvider):
    PROVIDER_NAME = "InteractiveBrokers"

    def __init__(self, ipaddress, port):
        self.ib = IB()
        self.ipaddress = ipaddress
        self.port = port
        self.login()

    def get_name(self) -> str:
        return IbkrDataProvider.PROVIDER_NAME

    @retry(wait_exponential_multiplier=2000,
           stop_max_attempt_number=5)
    def login(self):
        client_id = 998
        self.ib.connect(self.ipaddress, self.port, clientId=client_id, readonly=True, timeout=20)
        # Sometimes takes a few seconds to resolve... only have to do this once per process so no biggie
        time.sleep(10)

    def logout(self):
        try:
            # Try and disconnect IB client
            self.ib.disconnect()
        except BaseException:
            logging.warning("Trying to disconnect IB client failed... ensure process is killed")
        pass

    def _get_frequency_attributes(self) -> list[FrequencyAttributes]:
        return [
            FrequencyAttributes(Period.Monthly,
                                min_start=timedelta(days=10 * 365),
                                properties={'bar_size': '1 month', 'duration': '10 Y'}),
            FrequencyAttributes(Period.Weekly,
                                min_start=timedelta(days=10 * 365),
                                properties={'bar_size': '1 week', 'duration': '10 Y'}),
            FrequencyAttributes(Period.Daily,
                                min_start=timedelta(days=10 * 365),
                                properties={'bar_size': '1 day', 'duration': '10 Y'}),
            FrequencyAttributes(Period.Hourly,
                                min_start=timedelta(days=10 * 365),
                                properties={'bar_size': '1 hour', 'duration': '10 Y'}),
            FrequencyAttributes(Period.Minute_30,
                                min_start=timedelta(days=365),
                                properties={'bar_size': '30 mins', 'duration': '1 Y'}),
            FrequencyAttributes(Period.Minute_15,
                                min_start=timedelta(days=365),
                                properties={'bar_size': '15 mins', 'duration': '1 Y'}),
            FrequencyAttributes(Period.Minute_5,
                                min_start=timedelta(days=90),
                                properties={'bar_size': '5 mins', 'duration': '90 D'}),
            FrequencyAttributes(Period.Minute_1,
                                min_start=timedelta(days=7),
                                properties={'bar_size': '1 min', 'duration': '7 D'}),
        ]

    @singledispatchmethod
    def _fetch_historical_data(self, stock: Stock, freq_attrs: FrequencyAttributes, start, end) -> DataFrame:
        ib_contract = IB_Stock(stock.get_symbol(), 'SMART', 'USD')
        return self.fetch_historical_data_for_symbol(ib_contract, freq_attrs)

    @_fetch_historical_data.register
    def _(self, future: Future, freq_attrs: FrequencyAttributes, start, end) -> DataFrame:
        tokens = future.futures_code.split(".")
        exchange = tokens[0]
        symbol = tokens[1]
        last_contract_month = datetime(year=future.year, month=future.month, day=1).strftime("%Y%m")
        ib_contract = IB_Future(symbol=symbol,
                                lastTradeDateOrContractMonth=last_contract_month,
                                exchange=exchange,
                                multiplier="37500",
                                localSymbol=future.futures_code,
                                currency="USD")

        # COTTON, TT, NYMEX, USD, 50000, 1, FALSE
        # COFFEE, KC, NYBOT, USD, 37500, 100, FALSE

        return self.fetch_historical_data_for_symbol(ib_contract, freq_attrs)

    @_fetch_historical_data.register
    def _(self, forex: Forex, freq_attrs: FrequencyAttributes, start, end) -> DataFrame:
        ib_contract = IB_Forex(pair=forex.get_symbol())
        return self.fetch_historical_data_for_symbol(ib_contract, freq_attrs, "MIDPOINT")

    def fetch_historical_data_for_symbol(self, contract, freq_attrs: FrequencyAttributes,
                                         what_to_show="TRADES") -> DataFrame:
        # If live data is available a request for delayed data would be ignored by TWS.
        self.ib.reqMarketDataType(3)

        bars = self.ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=freq_attrs.properties['duration'],
            barSizeSetting=freq_attrs.properties['bar_size'],
            whatToShow=what_to_show,
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

        if not freq_attrs.frequency.is_intraday():
            df[DATE_TIME_COLUMN] = (pd.to_datetime(df[DATE_TIME_COLUMN], format='%Y-%m-%d', errors='coerce')
                                    .dt.tz_localize(FUTURES_SOURCE_TIME_ZONE).dt.tz_convert('UTC'))

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
