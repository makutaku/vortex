"""
Main Barchart data provider implementation.

Orchestrates authentication, data fetching, and parsing for Barchart.com financial data.
"""

import logging
from datetime import timedelta
from functools import singledispatchmethod
from typing import Optional

import pandas as pd
from pandas import DataFrame

from ..base import DataProvider
from vortex.exceptions.providers import DataNotFoundError, AllowanceLimitExceededError
from vortex.exceptions.providers import DataProviderError
from vortex.models.forex import Forex
from vortex.models.future import Future
from vortex.models.period import Period, FrequencyAttributes
from vortex.models.price_series import FUTURES_SOURCE_TIME_ZONE, STOCK_SOURCE_TIME_ZONE
from vortex.models.stock import Stock

from .auth import BarchartAuth
from .client import BarchartClient  
from .parser import BarchartParser


class BarchartDataProvider(DataProvider):
    """Barchart data provider with modular architecture."""
    
    PROVIDER_NAME = "Barchart"
    DEFAULT_SELF_IMPOSED_DOWNLOAD_DAILY_LIMIT = 150
    MAX_BARS_PER_DOWNLOAD: int = 20000
    BARCHART_URL = 'https://www.barchart.com'
    
    def __init__(self, username: str, password: str, 
                 daily_download_limit: int = DEFAULT_SELF_IMPOSED_DOWNLOAD_DAILY_LIMIT):
        
        self.max_allowance = daily_download_limit
        self.auth = BarchartAuth(username, password)
        self.client = BarchartClient(self.auth)
        self.parser = BarchartParser()
        
        # Login on initialization
        self.auth.login()

    def get_name(self) -> str:
        return self.PROVIDER_NAME

    def login(self):
        """Login to Barchart (delegated to auth module)."""
        self.auth.login()

    def logout(self):
        """Logout from Barchart (delegated to auth module)."""
        self.auth.logout()

    def _get_frequency_attributes(self) -> list[FrequencyAttributes]:
        """Get supported frequency attributes for this provider."""
        def get_min_start_date(period):
            return {
                Period('1d'): timedelta(days=365 * 25),  # 25 years
                Period('1h'): timedelta(days=365 * 2),   # 2 years  
                Period('30m'): timedelta(days=365 * 2),  # 2 years
                Period('15m'): timedelta(days=365 * 2),  # 2 years
                Period('5m'): timedelta(days=365 * 2),   # 2 years
                Period('1m'): timedelta(days=365 * 2),   # 2 years
            }.get(period, timedelta(days=365 * 25))

        def get_max_range(period: Period) -> timedelta:
            return {
                Period('1d'): timedelta(days=365 * 25),  # 25 years
                Period('1h'): timedelta(days=365 * 2),   # 2 years
                Period('30m'): timedelta(days=365 * 2),  # 2 years
                Period('15m'): timedelta(days=365 * 2),  # 2 years
                Period('5m'): timedelta(days=365 * 2),   # 2 years
                Period('1m'): timedelta(days=365 * 2),   # 2 years
            }.get(period, timedelta(days=365 * 25))

        return [
            FrequencyAttributes(Period('1d'), get_min_start_date(Period('1d')), 
                              get_max_range(Period('1d')), 
                              {'max_bars': self.MAX_BARS_PER_DOWNLOAD, 'frequency_name': 'daily'}),
            FrequencyAttributes(Period('1h'), get_min_start_date(Period('1h')), 
                              get_max_range(Period('1h')), 
                              {'max_bars': self.MAX_BARS_PER_DOWNLOAD, 'frequency_name': 'hourly'}),
            FrequencyAttributes(Period('30m'), get_min_start_date(Period('30m')), 
                              get_max_range(Period('30m')), 
                              {'max_bars': self.MAX_BARS_PER_DOWNLOAD, 'frequency_name': '30minute'}),
            FrequencyAttributes(Period('15m'), get_min_start_date(Period('15m')), 
                              get_max_range(Period('15m')), 
                              {'max_bars': self.MAX_BARS_PER_DOWNLOAD, 'frequency_name': '15minute'}),
            FrequencyAttributes(Period('5m'), get_min_start_date(Period('5m')), 
                              get_max_range(Period('5m')), 
                              {'max_bars': self.MAX_BARS_PER_DOWNLOAD, 'frequency_name': '5minute'}),
            FrequencyAttributes(Period('1m'), get_min_start_date(Period('1m')), 
                              get_max_range(Period('1m')), 
                              {'max_bars': self.MAX_BARS_PER_DOWNLOAD, 'frequency_name': 'minute'}),
        ]

    @singledispatchmethod
    def _fetch_historical_data(self, instrument: Future, frequency_attributes: FrequencyAttributes,
                              start_date, end_date) -> Optional[DataFrame]:
        """Fetch historical data for futures."""
        url = self.get_historical_quote_url(instrument)
        return self._fetch_historical_data_(instrument.get_symbol(), frequency_attributes,
                                           start_date, end_date, url, FUTURES_SOURCE_TIME_ZONE)

    @_fetch_historical_data.register
    def _(self, instrument: Stock, frequency_attributes: FrequencyAttributes,
          start_date, end_date) -> Optional[DataFrame]:
        """Fetch historical data for stocks."""
        url = self.get_historical_quote_url(instrument)
        return self._fetch_historical_data_(instrument.get_symbol(), frequency_attributes,
                                           start_date, end_date, url, STOCK_SOURCE_TIME_ZONE)

    @_fetch_historical_data.register
    def _(self, instrument: Forex, frequency_attributes: FrequencyAttributes,
          start_date, end_date) -> Optional[DataFrame]:
        """Fetch historical data for forex."""
        url = self.get_historical_quote_url(instrument)
        return self._fetch_historical_data_(instrument.get_symbol(), frequency_attributes,
                                           start_date, end_date, url, FUTURES_SOURCE_TIME_ZONE)

    def _fetch_historical_data_(self, instrument: str, freq_attrs: FrequencyAttributes,
                               start_date, end_date, url: str, tz: str) -> Optional[DataFrame]:
        """Internal method to fetch historical data."""
        try:
            # GET the historical download page to get tokens
            hist_resp = self.auth.session.get(url)
            xsf_token = self.auth.extract_xsrf_token(hist_resp)
            
            # Check allowance
            xsf_token = self._fetch_download_token(url, xsf_token)
            
            # Get CSRF token and download data
            hist_csrf_token = self.auth.scrape_csrf_token(hist_resp)
            df = self._download_data(xsf_token, hist_csrf_token, instrument, freq_attrs, 
                                    start_date, end_date, url, tz)
            
        except ValueError as e:
            if "CSRF token" in str(e) or "authentication system" in str(e):
                # Fallback: Try alternative download method without CSRF tokens
                import logging
                logging.warning(f"CSRF token extraction failed, attempting alternative download method: {e}")
                df = self._try_alternative_download(instrument, freq_attrs, start_date, end_date, url, tz)
            else:
                raise
        return df

    def _try_alternative_download(self, instrument: str, freq_attrs: FrequencyAttributes,
                                 start_date, end_date, url: str, tz: str) -> Optional[DataFrame]:
        """Alternative download method when CSRF tokens are not available."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Method 1: Try direct session-based download
            logger.info("Attempting direct session-based download")
            
            # Format dates for Barchart API
            start_str = start_date.strftime('%m/%d/%Y')
            end_str = end_date.strftime('%m/%d/%Y')
            
            # Try common Barchart download endpoints
            download_endpoints = [
                f"/api/getDownloadData/{instrument}",
                f"/getHistory.json", 
                f"/proxies/timeseries/queryeod.ashx"
            ]
            
            for endpoint in download_endpoints:
                try:
                    # Prepare download parameters
                    params = {
                        'symbol': instrument,
                        'start': start_str,
                        'end': end_str,
                        'frequency': 'daily',
                        'volume': 'contract',
                        'order': 'asc',
                        'dividends': 'false',
                        'backadjusted': 'false',
                        'daystoexpiration': 'false',
                        'contractroll': 'expiration'
                    }
                    
                    response = self.auth.session.get(f"https://www.barchart.com{endpoint}", params=params)
                    if response.status_code == 200 and response.text:
                        logger.info(f"Alternative download successful via {endpoint}")
                        
                        # Try to parse as CSV or JSON
                        if 'json' in endpoint.lower():
                            # Handle JSON response
                            import json
                            data = json.loads(response.text)
                            if 'data' in data:
                                # Convert JSON to DataFrame
                                import pandas as pd
                                df = pd.DataFrame(data['data'])
                                return self._process_alternative_data(df, tz)
                        else:
                            # Handle CSV response
                            from .parser import BarchartParser
                            return BarchartParser.convert_downloaded_csv_to_df(
                                freq_attrs.period, response.text, tz)
                            
                except Exception as e:
                    logger.debug(f"Alternative endpoint {endpoint} failed: {e}")
                    continue
            
            logger.warning("All alternative download methods failed")
            return None
            
        except Exception as e:
            logger.error(f"Alternative download method failed: {e}")
            return None

    def _process_alternative_data(self, df, tz: str):
        """Process data from alternative download methods."""
        # Basic processing to match expected format
        import pandas as pd
        
        if df.empty:
            return df
            
        # Try to identify and rename columns to standard format
        column_mappings = {
            'date': 'Datetime', 'time': 'Datetime', 'timestamp': 'Datetime',
            'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
            'volume': 'Volume', 'vol': 'Volume'
        }
        
        # Rename columns
        df.columns = [column_mappings.get(col.lower(), col) for col in df.columns]
        
        # Process datetime if available
        if 'Datetime' in df.columns:
            df['Datetime'] = pd.to_datetime(df['Datetime']).dt.tz_localize(tz).dt.tz_convert('UTC')
            df.set_index('Datetime', inplace=True)
        
        return df

    def _download_data(self, xsrf_token: str, hist_csrf_token: str, symbol: str, 
                      freq_attrs: FrequencyAttributes, start_date, end_date, url: str, tz: str) -> DataFrame:
        """Download and parse data."""
        resp = self.client.request_download(xsrf_token, hist_csrf_token, symbol, 
                                           freq_attrs, url, start_date, end_date)

        if resp.status_code != 200 or 'Error retrieving data' in resp.text:
            raise DownloadError(resp.status_code, "Barchart error retrieving data")

        df = self.parser.convert_downloaded_csv_to_df(freq_attrs.frequency, resp.text, tz)
        if len(df) <= 3:
            raise LowDataError()

        return df

    def _fetch_download_token(self, url: str, xsf_token: str) -> str:
        """Fetch and validate download token."""
        allowance, xsf_token = self.client.fetch_allowance(url, xsf_token)
        
        if allowance is None:
            raise DataProviderError(
                "barchart",
                "Failed to fetch allowance data - received None response",
                "This may indicate authentication failure or Barchart server issues. Please check credentials and try again."
            )
        
        if allowance.get('error') is not None:
            raise AllowanceLimitExceededError(250, self.max_allowance)

        if not allowance.get('success', False):
            raise DataProviderError(
                "barchart",
                "Invalid allowance response format - missing 'success' field",
                "This may indicate a temporary Barchart API issue. Please try again later."
            )

        current_allowance = int(allowance.get('count', '0'))
        if self.max_allowance is not None and current_allowance > self.max_allowance:
            raise AllowanceLimitExceededError(current_allowance, self.max_allowance)

        logging.info(f"Allowance: {current_allowance}")
        return xsf_token

    @singledispatchmethod
    def get_historical_quote_url(self, future: Future) -> str:
        """Get historical quote URL for futures."""
        symbol = future.get_symbol()
        return f"{self.BARCHART_URL}/futures/quotes/{symbol}/historical-download"

    @get_historical_quote_url.register
    def _(self, stock: Stock) -> str:
        """Get historical quote URL for stocks."""
        symbol = stock.get_symbol()
        return f"{self.BARCHART_URL}/stocks/quotes/{symbol}/historical-download"

    @get_historical_quote_url.register
    def _(self, forex: Forex) -> str:
        """Get historical quote URL for forex."""
        symbol = forex.get_symbol()
        return f"{self.BARCHART_URL}/forex/quotes/{symbol}/historical-download"