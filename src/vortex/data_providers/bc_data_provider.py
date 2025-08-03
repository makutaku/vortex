import io
import json
import logging
import urllib.parse
from datetime import datetime, timedelta, timezone
from functools import singledispatchmethod

import pandas as pd
import requests
from bs4 import BeautifulSoup
from pandas import DataFrame

from .data_provider import DataProvider, NotFoundError, AllowanceLimitExceeded, DownloadError, \
    LowDataError
from ..instruments.columns import CLOSE_COLUMN, DATE_TIME_COLUMN
from ..instruments.forex import Forex
from ..instruments.future import Future
from ..instruments.period import Period, FrequencyAttributes
from ..instruments.price_series import FUTURES_SOURCE_TIME_ZONE, STOCK_SOURCE_TIME_ZONE, LOW_DATA_THRESHOLD
from ..instruments.stock import Stock
from ..utils.logging_utils import LoggingContext


class BarchartDataProvider(DataProvider):
    PROVIDER_NAME = "Barchart"
    DEFAULT_SELF_IMPOSED_DOWNLOAD_DAILY_LIMIT = 150
    MAX_BARS_PER_DOWNLOAD: int = 20000
    BARCHART_URL = 'https://www.barchart.com'
    BARCHART_LOGIN_URL = BARCHART_URL + '/login'
    BARCHART_LOGOUT_URL = BARCHART_URL + '/logout'
    BARCHART_DOWNLOAD_URL = BARCHART_URL + '/my/download'
    BARCHART_ALLOWANCE_URL = BARCHART_DOWNLOAD_URL
    BARCHART_DATE_TIME_COLUMN = 'Time'
    BARCHART_CLOSE_COLUMN = "Last"

    def __init__(self, username, password, daily_download_limit=DEFAULT_SELF_IMPOSED_DOWNLOAD_DAILY_LIMIT):

        if not username or not password:
            raise Exception('Barchart credentials are required')

        self.username = username
        self.password = password
        self.max_allowance = daily_download_limit
        session = BarchartDataProvider._create_bc_session()
        self.session = session
        self.login()

    def get_name(self) -> str:
        return BarchartDataProvider.PROVIDER_NAME

    def _get_frequency_attributes(self) -> list[FrequencyAttributes]:

        def get_min_start_date(period):
            return datetime(year=2000, month=1, day=1, tzinfo=timezone.utc) if period.is_intraday() else None

        def get_max_range(period: Period) -> timedelta:
            return period.get_delta_time() * BarchartDataProvider.MAX_BARS_PER_DOWNLOAD

        return [
            FrequencyAttributes(Period.Monthly,
                                min_start=get_min_start_date(Period.Monthly),
                                max_window=get_max_range(Period.Monthly),
                                properties={'type': 'eod', 'period': 'monthly'}),
            FrequencyAttributes(Period.Weekly,
                                min_start=get_min_start_date(Period.Weekly),
                                max_window=get_max_range(Period.Weekly),
                                properties={'type': 'eod', 'period': 'weekly'}),
            FrequencyAttributes(Period.Daily,
                                min_start=get_min_start_date(Period.Daily),
                                max_window=get_max_range(Period.Daily),
                                properties={'type': 'eod', 'period': 'daily'}),
            FrequencyAttributes(Period.Hourly,
                                min_start=get_min_start_date(Period.Hourly),
                                max_window=get_max_range(Period.Hourly),
                                properties={'type': 'minutes', 'interval': 60}),
            FrequencyAttributes(Period.Minute_30,
                                min_start=get_min_start_date(Period.Minute_30),
                                max_window=get_max_range(Period.Minute_30),
                                properties={'type': 'minutes', 'interval': 30}),
            FrequencyAttributes(Period.Minute_15,
                                min_start=get_min_start_date(Period.Minute_15),
                                max_window=get_max_range(Period.Minute_15),
                                properties={'type': 'minutes', 'interval': 15}),
            FrequencyAttributes(Period.Minute_5,
                                min_start=get_min_start_date(Period.Minute_5),
                                max_window=get_max_range(Period.Minute_5),
                                properties={'type': 'minutes', 'interval': 5}),
            FrequencyAttributes(Period.Minute_1,
                                min_start=get_min_start_date(Period.Minute_1),
                                max_window=get_max_range(Period.Minute_1),
                                properties={'type': 'minutes', 'interval': 1}),
        ]

    def login(self):
        with LoggingContext(entry_msg=f"Logging in ...", success_msg=f"Logged in."):
            # GET the login page, scrape to get CSRF token
            resp = self.session.get(BarchartDataProvider.BARCHART_LOGIN_URL)
            soup = BeautifulSoup(resp.text, 'html.parser')
            tag = soup.find(type='hidden')
            csrf_token = tag.attrs['value']
            # login to site
            payload = BarchartDataProvider.build_login_payload(csrf_token, self.username, self.password)
            resp = self.session.post(BarchartDataProvider.BARCHART_LOGIN_URL, data=payload)
            if resp.url == BarchartDataProvider.BARCHART_LOGIN_URL:
                raise Exception('Invalid Barchart credentials')

    def logout(self):
        with LoggingContext(entry_msg=f"Logging out ...", success_msg=f"Logged out."):
            self.session.get(BarchartDataProvider.BARCHART_LOGOUT_URL, timeout=10)

    @singledispatchmethod
    def _fetch_historical_data(self,
                               instrument: Future,
                               frequency_attributes: FrequencyAttributes,
                               start_date, end_date) -> DataFrame | None:
        url = self.get_historical_quote_url(instrument)
        return self._fetch_historical_data_(instrument.get_symbol(), frequency_attributes,
                                            start_date, end_date, url, FUTURES_SOURCE_TIME_ZONE)

    @_fetch_historical_data.register
    def _(self,
          instrument: Stock,
          frequency_attributes: FrequencyAttributes,
          start_date, end_date) -> DataFrame | None:
        url = self.get_historical_quote_url(instrument)
        return self._fetch_historical_data_(instrument.get_symbol(), frequency_attributes,
                                            start_date, end_date, url, STOCK_SOURCE_TIME_ZONE)

    @_fetch_historical_data.register
    def _(self,
          instrument: Forex,
          frequency_attributes: FrequencyAttributes,
          start_date, end_date) -> DataFrame | None:
        url = self.get_historical_quote_url(instrument)
        return self._fetch_historical_data_(instrument.get_symbol(), frequency_attributes,
                                            start_date, end_date, url, FUTURES_SOURCE_TIME_ZONE)

    def _fetch_historical_data_(self, instrument: str,
                                freq_attrs: FrequencyAttributes,
                                start_date: datetime,
                                end_date: datetime,
                                url: str,
                                tz: str) -> DataFrame | None:
        with LoggingContext(entry_msg=f"Fetching historical {freq_attrs.frequency} data from Barchart for {instrument} "
                                      f"from {start_date.strftime('%Y-%m-%d')} "
                                      f"to {end_date.strftime('%Y-%m-%d')} ...",
                            success_msg=f"Fetched historical data from Barchart",
                            failure_msg=f"Failed to fetch historical data from Barchart"):
            hist_resp = self.session.get(url)
            if hist_resp.status_code != 200:
                raise NotFoundError(instrument, freq_attrs.frequency, start_date, end_date, hist_resp.status_code)

            # check allowance
            xsf_token = BarchartDataProvider.extract_xsrf_token(hist_resp)
            xsf_token = self._fetch_download_token(url, xsf_token)

            hist_csrf_token = BarchartDataProvider.scrape_csrf_token(hist_resp)
            df = self._download_data(xsf_token, hist_csrf_token, instrument, freq_attrs, start_date, end_date, url, tz)
            return df

    def request_download(self, xsrf_token: str, hist_csrf_token: str, symbol: str,
                         freq_attrs: FrequencyAttributes, url: str,
                         start_date: datetime, end_date: datetime) -> requests.Response:
        headers = BarchartDataProvider.build_download_request_headers(xsrf_token, url)
        payload = BarchartDataProvider.build_download_request_payload(hist_csrf_token, symbol, freq_attrs,
                                                                      start_date, end_date)
        resp = self.session.post(BarchartDataProvider.BARCHART_DOWNLOAD_URL, headers=headers, data=payload)
        logging.debug(f"POST {BarchartDataProvider.BARCHART_DOWNLOAD_URL}, "
                      f"status: {resp.status_code}, "
                      f"data length: {len(resp.content)}")
        return resp

    def _download_data(self, xsrf_token: str, hist_csrf_token: str, symbol: str, freq_attrs: FrequencyAttributes,
                       start_date: datetime, end_date: datetime, url: str, tz: str) -> pd.DataFrame:

        resp = self.request_download(xsrf_token, hist_csrf_token, symbol, freq_attrs, url, start_date, end_date)

        if resp.status_code != 200 or 'Error retrieving data' in resp.text:
            raise DownloadError(resp.status_code, "Barchart error retrieving data")

        df = self.convert_downloaded_csv_to_df(freq_attrs.frequency, resp.text, tz)
        if len(df) <= 3:
            raise LowDataError()

        return df

    def _fetch_download_token(self, url, xsf_token):
        allowance, xsf_token = self._fetch_allowance(url, xsf_token)
        if allowance.get('error') is not None:
            raise AllowanceLimitExceeded(250, self.max_allowance)

        if not allowance['success']:
            # TODO: pick better exception
            raise Exception("Neither 'error' nor 'success' key was present in fetch allowance response.")

        current_allowance = int(allowance.get('count', '0'))
        if self.max_allowance is not None and current_allowance > self.max_allowance:
            raise AllowanceLimitExceeded(current_allowance, self.max_allowance)

        logging.info(f"Allowance: {current_allowance}")

        return xsf_token

    def _fetch_allowance(self, url, xsf_token):
        with LoggingContext(entry_msg="Checking allowance",
                            exit_msg="Checked allowance"):
            headers = BarchartDataProvider.build_allowance_request_headers(url, xsf_token)
            payload = BarchartDataProvider.build_allowance_payload()
            resp = self.session.post(BarchartDataProvider.BARCHART_ALLOWANCE_URL, headers=headers, data=payload)
            xsf_token = BarchartDataProvider.extract_xsrf_token(resp)
            allowance = json.loads(resp.text)
            logging.debug(f"allowance: {allowance}")
            return allowance, xsf_token

    @singledispatchmethod
    def get_historical_quote_url(self, future: Future) -> str:
        symbol = future.get_symbol()
        return f"{BarchartDataProvider.BARCHART_URL}/futures/quotes/{symbol}/historical-download"

    @get_historical_quote_url.register
    def _(self, stock: Stock) -> str:
        symbol = stock.get_symbol()
        return f"{BarchartDataProvider.BARCHART_URL}/stocks/quotes/{symbol}/historical-download"

    @get_historical_quote_url.register
    def _(self, forex: Forex) -> str:
        symbol = forex.get_symbol()
        return f"{BarchartDataProvider.BARCHART_URL}/forex/quotes/{symbol}/historical-download"

    @staticmethod
    def build_login_payload(csrf_token, username, password):
        payload = {
            'email': username,
            'password': password,
            '_token': csrf_token
        }
        return payload

    @staticmethod
    def build_allowance_request_headers(url, xsf_token):
        headers = BarchartDataProvider.build_download_request_headers(xsf_token, url)
        return headers

    @staticmethod
    def build_allowance_payload():
        payload = {'onlyCheckPermissions': 'true'}
        return payload

    @staticmethod
    def build_download_request_payload(hist_csrf_token, symbol, freq_attrs: FrequencyAttributes, start_date, end_date):

        freq_type = freq_attrs.properties.get('type')
        key = 'interval' if freq_attrs.frequency.is_intraday() else 'period'
        value = freq_attrs.properties.get(key)

        payload = {
            '_token': hist_csrf_token,
            'fileName': symbol + '_Daily_Historical Data',
            'symbol': symbol,
            'fields': 'tradeTime.format(Y-m-d),openPrice,highPrice,lowPrice,lastPrice,volume',
            'startDate': start_date.strftime("%Y-%m-%d"),
            'endDate': end_date.strftime("%Y-%m-%d"),
            'orderBy': 'tradeTime',
            'orderDir': 'asc',
            'method': 'historical',
            'limit': ('%d' % BarchartDataProvider.MAX_BARS_PER_DOWNLOAD),
            key: value,
            'customView': 'true',
            'pageTitle': 'Historical Data',
            'type': freq_type
        }

        return payload

    @staticmethod
    def build_download_request_headers(xsrf_token, url):
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': url,
            'x-xsrf-token': xsrf_token
        }
        return headers

    @staticmethod
    def extract_xsrf_token(hist_resp):
        return urllib.parse.unquote(hist_resp.cookies['XSRF-TOKEN'])

    @staticmethod
    def scrape_csrf_token(hist_resp):
        hist_soup = BeautifulSoup(hist_resp.text, 'html.parser')
        hist_tag = hist_soup.find(name='meta', attrs={'name': 'csrf-token'})
        hist_csrf_token = hist_tag.attrs['content']
        return hist_csrf_token

    @staticmethod
    def _create_bc_session():
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0'})
        return session

    def convert_downloaded_csv_to_df(self, period, data, tz):
        iostr = io.StringIO(data)
        date_format = '%m/%d/%Y %H:%M' if period.is_intraday() else '%Y-%m-%d'
        df = pd.read_csv(iostr, skipfooter=1, engine='python')
        logging.debug(f"Received data {df.shape} from {self.get_name()}")

        columns = {
            BarchartDataProvider.BARCHART_DATE_TIME_COLUMN: DATE_TIME_COLUMN,
            BarchartDataProvider.BARCHART_CLOSE_COLUMN: CLOSE_COLUMN,
        }
        df = df.rename(columns=columns)
        df[DATE_TIME_COLUMN] = (pd.to_datetime(df[DATE_TIME_COLUMN], format=date_format, errors='coerce')
                                .dt.tz_localize(tz).dt.tz_convert('UTC'))
        df.set_index(DATE_TIME_COLUMN, inplace=True)
        return df
