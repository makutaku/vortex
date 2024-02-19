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

from data_providers.data_provider import DataProvider, NotFoundError, AllowanceLimitExceeded, DownloadError, \
    LowDataError
from instruments.columns import CLOSE_COLUMN, DATE_TIME_COLUMN
from instruments.forex import Forex
from instruments.future import Future
from instruments.instrument import Instrument
from instruments.period import Period
from instruments.price_series import SOURCE_TIME_ZONE
from instruments.stock import Stock
from utils.logging_utils import LoggingContext
from utils.utils import random_sleep


class BarchartDataProvider(DataProvider):
    PROVIDER_NAME = "Barchart"
    SELF_IMPOSED_DOWNLOAD_DAILY_LIMIT = 150
    MAX_BARS_PER_DOWNLOAD: int = 20000
    BARCHART_URL = 'https://www.barchart.com'
    BARCHART_LOGIN_URL = BARCHART_URL + '/login'
    BARCHART_LOGOUT_URL = BARCHART_URL + '/logout'
    BARCHART_DOWNLOAD_URL = BARCHART_URL + '/my/download'
    BARCHART_ALLOWANCE_URL = BARCHART_DOWNLOAD_URL
    BARCHART_DATE_TIME_COLUMN = 'Time'
    BARCHART_CLOSE_COLUMN = "Last"

    def __init__(self, username, password, dry_run,
                 daily_download_limit=SELF_IMPOSED_DOWNLOAD_DAILY_LIMIT, random_sleep_in_sec=None):
        self.sleep_random_seconds = random_sleep_in_sec if random_sleep_in_sec > 0 else None
        self.dry_run = dry_run
        self.max_allowance = daily_download_limit
        session = BarchartDataProvider._create_bc_session()
        self.session = session
        if not username or not password:
            raise Exception('Barchart credentials are required')
        self.login(username, password)

    def get_name(self) -> str:
        return BarchartDataProvider.PROVIDER_NAME

    def get_max_range(self, period: Period) -> timedelta:
        return period.get_delta_time() * BarchartDataProvider.MAX_BARS_PER_DOWNLOAD

    def get_min_start(self, period: Period) -> datetime | None:
        return datetime(year=2000, month=1, day=1, tzinfo=timezone.utc) if period.is_intraday() else None

    def get_supported_timeframes(self, instrument: Instrument) -> list[Period]:
        return [
            Period.Minute_1,
            Period.Minute_2,
            Period.Minute_5,
            Period.Minute_10,
            Period.Minute_15,
            Period.Minute_20,
            Period.Minute_30,
            Period.Hourly,
            Period.Daily,
            Period.Weekly,
            Period.Monthly
        ]

    def login(self, username, password):
        with LoggingContext(entry_msg=f"Logging in ...", success_msg=f"Logged in."):
            # GET the login page, scrape to get CSRF token
            resp = self.session.get(BarchartDataProvider.BARCHART_LOGIN_URL)
            soup = BeautifulSoup(resp.text, 'html.parser')
            tag = soup.find(type='hidden')
            csrf_token = tag.attrs['value']
            # login to site
            payload = BarchartDataProvider.build_login_payload(csrf_token, username, password)
            resp = self.session.post(BarchartDataProvider.BARCHART_LOGIN_URL, data=payload)
            if resp.url == BarchartDataProvider.BARCHART_LOGIN_URL:
                raise Exception('Invalid Barchart credentials')

    def logout(self):
        with LoggingContext(entry_msg=f"Logging out ...", success_msg=f"Logged out."):
            self.session.get(BarchartDataProvider.BARCHART_LOGOUT_URL, timeout=10)

    def fetch_historical_data(self,
                              instrument: Instrument,
                              period,
                              start_date, end_date) -> DataFrame | None:
        url = self.get_historical_quote_url(instrument)
        return self._fetch_historical_data(instrument.get_symbol(), period, start_date, end_date, url)

    def _fetch_historical_data(self, instrument: str, period: Period, start_date: datetime,
                               end_date: datetime, url: str) -> DataFrame | None:
        with LoggingContext(entry_msg=f"Fetching historical {period} data from Barchart for {instrument} "
                                      f"from {start_date.strftime('%Y-%m-%d')} "
                                      f"to {end_date.strftime('%Y-%m-%d')} ...",
                            success_msg=f"{'(dryrun) ' if self.dry_run else ''}Fetched historical data from Barchart",
                            failure_msg=f"Failed to fetch historical data from Barchart"):

            hist_resp = self.session.get(url)
            if hist_resp.status_code != 200:
                raise NotFoundError(instrument, period, start_date, end_date, hist_resp.status_code)

            # check allowance
            xsf_token = BarchartDataProvider.extract_xsrf_token(hist_resp)
            xsf_token = self._fetch_download_token(url, xsf_token)

            if self.dry_run:
                return None

            hist_csrf_token = BarchartDataProvider.scrape_csrf_token(hist_resp)
            df = self._download_data(xsf_token, hist_csrf_token, instrument, period, start_date, end_date, url)
            return df

    def request_download(self, xsrf_token: str, hist_csrf_token: str, symbol: str, period: Period, url: str,
                         start_date: datetime, end_date: datetime) -> requests.Response:
        headers = BarchartDataProvider.build_download_request_headers(xsrf_token, url)
        payload = BarchartDataProvider.build_download_request_payload(hist_csrf_token, symbol, period,
                                                                      start_date, end_date)
        resp = self.session.post(BarchartDataProvider.BARCHART_DOWNLOAD_URL, headers=headers, data=payload)
        logging.debug(f"POST {BarchartDataProvider.BARCHART_DOWNLOAD_URL}, "
                      f"status: {resp.status_code}, "
                      f"data length: {len(resp.content)}")
        return resp

    def _download_data(self, xsrf_token: str, hist_csrf_token: str, symbol: str, period: Period,
                       start_date: datetime, end_date: datetime, url: str) -> pd.DataFrame:

        self.pretend_not_a_bot()
        resp = self.request_download(xsrf_token, hist_csrf_token, symbol, period, url, start_date, end_date)

        if resp.status_code != 200 or 'Error retrieving data' in resp.text:
            raise DownloadError(resp.status_code, "Barchart error retrieving data")

        df = self.convert_downloaded_csv_to_df(period, resp.text)
        if len(df) < 3:
            raise LowDataError()

        return df

    def pretend_not_a_bot(self):
        if self.sleep_random_seconds is not None:
            # cursory attempt to not appear like a bot
            random_sleep(self.sleep_random_seconds)
        else:
            logging.warning("Random sleep is disabled. Enable to avoid bot detection.")

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
    def build_download_request_payload(hist_csrf_token, symbol, period, start_date, end_date):
        payload = {'_token': hist_csrf_token,
                   'fileName': symbol + '_Daily_Historical Data',
                   'symbol': symbol,
                   'fields': 'tradeTime.format(Y-m-d),openPrice,highPrice,lowPrice,lastPrice,volume',
                   'startDate': start_date.strftime("%Y-%m-%d"),
                   'endDate': end_date.strftime("%Y-%m-%d"),
                   'orderBy': 'tradeTime',
                   'orderDir': 'asc',
                   'method': 'historical',
                   'limit': '10000',
                   'customView': 'true',
                   'pageTitle': 'Historical Data'}
        if period == Period.Daily:
            payload['type'] = 'eod'
            payload['period'] = Period.Daily
        elif period == Period.Hourly:
            payload['type'] = 'minutes'
            payload['interval'] = 60
        elif period == Period.Minute_30:
            payload['type'] = 'minutes'
            payload['interval'] = 30
        elif period == Period.Minute_15:
            payload['type'] = 'minutes'
            payload['interval'] = 15
        elif period == Period.Minute_5:
            payload['type'] = 'minutes'
            payload['interval'] = 5
        else:
            raise NotImplemented
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

    def convert_downloaded_csv_to_df(self, period, data):
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
                                .dt.tz_localize(SOURCE_TIME_ZONE).dt.tz_convert('UTC'))
        df.set_index(DATE_TIME_COLUMN, inplace=True)
        return df
