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
        """Internal method to fetch historical data using bc-utils methodology."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Use bc-utils approach: try JSON API endpoints first
            df = self._fetch_via_json_api(instrument, freq_attrs, start_date, end_date, tz)
            if df is not None:
                return self._validate_data_availability(df, instrument, freq_attrs, start_date, end_date)
            
            # Fallback: try CSV download method
            logger.info(f"JSON API failed, attempting CSV download for {instrument}")
            df = self._fetch_via_csv_download(instrument, freq_attrs, start_date, end_date, tz)
            if df is not None:
                return self._validate_data_availability(df, instrument, freq_attrs, start_date, end_date)
            
            # No data found with any method
            from vortex.exceptions.providers import DataNotFoundError
            raise DataNotFoundError(
                provider="barchart",
                symbol=instrument,
                period=freq_attrs.frequency,
                start_date=start_date,
                end_date=end_date
            )
            
        except Exception as e:
            logger.error(f"All download methods failed for {instrument}: {e}")
            raise

    def _fetch_via_json_api(self, instrument: str, freq_attrs: FrequencyAttributes,
                           start_date, end_date, tz: str) -> Optional[DataFrame]:
        """Fetch data using Barchart JSON API (bc-utils methodology)."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Format dates for API
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Determine frequency parameter
        frequency = self._get_api_frequency(freq_attrs.frequency)
        
        # Primary JSON API endpoints (based on bc-utils pattern)
        api_endpoints = [
            # Core API endpoint (most reliable)
            {
                'url': 'https://www.barchart.com/proxies/core-api/v1/quotes/get',
                'params': {
                    'symbol': instrument,
                    'start': start_str,
                    'end': end_str,
                    'type': 'historical',
                    'interval': frequency
                }
            },
            # Alternative endpoints
            {
                'url': f'https://www.barchart.com/proxies/timeseries/queryeod.ashx',
                'params': {
                    'symbol': instrument,
                    'start': start_str,
                    'end': end_str,
                    'frequency': frequency,
                    'volume': 'contract',
                    'order': 'asc'
                }
            }
        ]
        
        for endpoint in api_endpoints:
            try:
                logger.info(f"Attempting JSON API: {endpoint['url']}")
                
                # Make authenticated API request
                response_data = self.auth.make_api_request(endpoint['url'], endpoint['params'])
                
                if response_data and 'data' in response_data:
                    # Check if this is actually CSV data disguised as JSON
                    if 'content_type' in response_data and 'csv' in response_data.get('content_type', '').lower():
                        logger.info(f"CSV response received from JSON API for {instrument}")
                        return self._process_csv_response(response_data['data'], freq_attrs.frequency, tz)
                    elif isinstance(response_data['data'], str):
                        # Data is a string, likely CSV
                        logger.info(f"String data received from JSON API for {instrument}")
                        return self._process_csv_response(response_data['data'], freq_attrs.frequency, tz)
                    else:
                        # Actual JSON data
                        logger.info(f"JSON API successful for {instrument}")
                        return self._process_json_response(response_data, tz)
                    
            except Exception as e:
                logger.debug(f"JSON API endpoint failed: {e}")
                continue
        
        logger.warning(f"All JSON API endpoints failed for {instrument}")
        return None

    def _process_json_response(self, json_data: dict, tz: str) -> Optional[DataFrame]:
        """Process JSON response from Barchart API."""
        import pandas as pd
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Debug: log the JSON structure
            logger.debug(f"Processing JSON response keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'Not a dict'}")
            
            # Extract data array from various JSON structures
            data_array = None
            if isinstance(json_data, dict):
                if 'data' in json_data:
                    data_array = json_data['data']
                elif 'history' in json_data:
                    data_array = json_data['history']
                elif 'results' in json_data:
                    data_array = json_data['results']
                else:
                    # Try to use the whole dict if it looks like data
                    if any(key in json_data for key in ['open', 'high', 'low', 'close', 'date', 'time']):
                        data_array = [json_data]  # Wrap single record
            elif isinstance(json_data, list):
                data_array = json_data
            
            if not data_array:
                logger.warning(f"No data found in JSON response. Response structure: {json_data}")
                return None
            
            # Validate data_array is suitable for DataFrame
            if not isinstance(data_array, list):
                logger.error(f"Data array is not a list: {type(data_array)}")
                return None
                
            if not data_array:
                logger.warning("Data array is empty")
                return None
                
            # Log first item structure for debugging
            logger.debug(f"First data item: {data_array[0] if data_array else 'Empty'}")
            
            # Create DataFrame from JSON data
            df = pd.DataFrame(data_array)
            
            if df.empty:
                logger.warning("Empty DataFrame from JSON data")
                return None
            
            # Standardize column names
            column_mapping = {
                'date': 'Datetime', 'time': 'Datetime', 'timestamp': 'Datetime',
                'dateTime': 'Datetime', 'tradingDay': 'Datetime',
                'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close',
                'volume': 'Volume', 'openInterest': 'Open Interest'
            }
            
            # Rename columns
            df.rename(columns=column_mapping, inplace=True)
            
            # Process datetime column
            if 'Datetime' in df.columns:
                df['Datetime'] = pd.to_datetime(df['Datetime'])
                if df['Datetime'].dt.tz is None:
                    df['Datetime'] = df['Datetime'].dt.tz_localize(tz)
                df['Datetime'] = df['Datetime'].dt.tz_convert('UTC')
                df.set_index('Datetime', inplace=True)
                df.sort_index(inplace=True)
            
            logger.info(f"Successfully processed JSON data: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to process JSON response: {e}")
            return None

    def _fetch_via_csv_download(self, instrument: str, freq_attrs: FrequencyAttributes,
                               start_date, end_date, tz: str) -> Optional[DataFrame]:
        """Fetch data via CSV download (bc-utils methodology)."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Format dates for CSV download
            start_str = start_date.strftime('%m/%d/%Y')
            end_str = end_date.strftime('%m/%d/%Y')
            
            # CSV download endpoint
            csv_url = "https://www.barchart.com/proxies/timeseries/queryeod.ashx"
            
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
            
            logger.info(f"Attempting CSV download for {instrument}")
            response_data = self.auth.make_api_request(csv_url, params)
            
            if 'data' in response_data and response_data['data']:
                logger.info(f"CSV download successful for {instrument}")
                return self._process_csv_response(response_data['data'], freq_attrs.frequency, tz)
            
            logger.warning(f"CSV download failed for {instrument} - no data returned")
            return None
            
        except Exception as e:
            logger.error(f"CSV download failed for {instrument}: {e}")
            return None

    def _process_csv_response(self, csv_data: str, frequency, tz: str) -> Optional[DataFrame]:
        """Process CSV response data."""
        try:
            from .parser import BarchartParser
            return BarchartParser.convert_downloaded_csv_to_df(frequency, csv_data, tz)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to process CSV response: {e}")
            return None
    
    def _get_api_frequency(self, period) -> str:
        """Convert Period to Barchart API frequency parameter."""
        from vortex.models.period import Period
        
        frequency_mapping = {
            Period('1d'): 'daily',
            Period('1h'): 'hourly', 
            Period('30m'): '30minute',
            Period('15m'): '15minute',
            Period('5m'): '5minute',
            Period('1m'): 'minute'
        }
        
        return frequency_mapping.get(period, 'daily')

    def _validate_data_availability(self, df: DataFrame, symbol: str, freq_attrs: FrequencyAttributes = None, 
                                   start_date=None, end_date=None) -> DataFrame:
        """Validate downloaded data meets minimum requirements."""
        if df is None or df.empty:
            from vortex.exceptions.providers import DataNotFoundError
            if freq_attrs and start_date and end_date:
                raise DataNotFoundError(
                    provider="barchart",
                    symbol=symbol,
                    period=freq_attrs.frequency,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                # Fallback for cases where we don't have all parameters
                from vortex.exceptions.providers import DataProviderError
                raise DataProviderError("barchart", f"No data available for {symbol}")
        
        if len(df) <= 3:
            from vortex.exceptions.providers import DataProviderError
            raise DataProviderError(
                "barchart",
                f"Insufficient data for {symbol} - only {len(df)} records found",
                "This may indicate the symbol is delisted or has limited trading history"
            )
        
        return df

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