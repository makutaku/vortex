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
from vortex.core.constants import ProviderConstants

from .auth import BarchartAuth
from .client import BarchartClient  
from .parser import BarchartParser


class BarchartDataProvider(DataProvider):
    """Barchart data provider with modular architecture."""
    
    PROVIDER_NAME = "Barchart"
    DEFAULT_SELF_IMPOSED_DOWNLOAD_DAILY_LIMIT = ProviderConstants.Barchart.DEFAULT_DAILY_DOWNLOAD_LIMIT
    MAX_BARS_PER_DOWNLOAD: int = ProviderConstants.Barchart.MAX_BARS_PER_DOWNLOAD
    BARCHART_URL = ProviderConstants.Barchart.BASE_URL
    
    def __init__(self, username: str, password: str, 
                 daily_download_limit: int = DEFAULT_SELF_IMPOSED_DOWNLOAD_DAILY_LIMIT):
        
        # Store daily limit for informational purposes (not enforced client-side)
        # bc-utils relies on server-side enforcement: 250 for paid, 5 for free users
        self.daily_limit = daily_download_limit
        self.auth = BarchartAuth(username, password)
        self.client = BarchartClient(self.auth)
        self.parser = BarchartParser()
        
        # Login on initialization
        self.auth.login()
    
    def _extract_csrf_token(self, home_response) -> Optional[str]:
        """Extract CSRF token from Barchart home page response.
        
        Args:
            home_response: HTTP response from Barchart home page
            
        Returns:
            CSRF token string if found, None otherwise
        """
        import logging
        from bs4 import BeautifulSoup
        
        logger = logging.getLogger(__name__)
        
        soup = BeautifulSoup(home_response.text, 'html.parser')
        
        # Look for meta CSRF token (the correct token type)
        meta_token = soup.find('meta', {'name': 'csrf-token'})
        if meta_token:
            csrf_token = meta_token.get('content')
            logger.debug(f"Found meta CSRF token: {csrf_token[:20]}...")
            return csrf_token
        else:
            logger.debug("No meta CSRF token found")
            return None

    def get_name(self) -> str:
        return self.PROVIDER_NAME

    def login(self):
        """Login to Barchart (delegated to auth module)."""
        self.auth.login()

    def logout(self):
        """Logout from Barchart (delegated to auth module)."""
        self.auth.logout()

    def _fetch_usage(self, url: str, xsrf_token: str) -> tuple[dict, str]:
        """Check download usage count (delegated to client)."""
        return self.client.fetch_usage(url, xsrf_token)

    def get_daily_limit(self) -> int:
        """Get the configured daily download limit for informational purposes."""
        return self.daily_limit

    def _check_server_usage(self) -> Optional[int]:
        """Check current download usage count using exact bc-utils methodology."""
        import logging
        import json
        logger = logging.getLogger(__name__)
        
        try:
            # Use exact bc-utils approach: GET home page for CSRF token, then POST with onlyCheckPermissions
            home_response = self.auth.session.get(self.BARCHART_URL)
            
            if home_response.status_code != 200:
                logger.debug(f"Cannot access home page for usage check: {home_response.status_code}")
                return None
            
            # Extract CSRF token using shared method
            csrf_token = self._extract_csrf_token(home_response)
            if not csrf_token:
                logger.debug("No CSRF token found for usage check")
                return None
            
            # Prepare bc-utils usage check payload
            payload = {
                'onlyCheckPermissions': 'true'  # This is the bc-utils secret!
            }
            
            # Prepare headers (same as working download)
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.BARCHART_URL,
                'Referer': self.BARCHART_URL,
                'X-CSRF-TOKEN': csrf_token
            }
            
            # Use bc-utils /my/download endpoint with onlyCheckPermissions
            download_url = f"{self.BARCHART_URL}/my/download"
            logger.debug(f"bc-utils usage check payload: {payload}")
            response = self.auth.session.post(download_url, data=payload, headers=headers)
            
            logger.debug(f"Usage check response status: {response.status_code}")
            logger.debug(f"Usage check response: {response.text[:200]}...")
            
            if response.status_code == 200:
                try:
                    usage_data = json.loads(response.text)
                    logger.debug(f"Parsed usage data: {usage_data}")
                    
                    # Check for error (bc-utils approach)
                    if usage_data.get("error") is not None:
                        logger.debug(f"Usage check error: {usage_data.get('error')}")
                        return None
                    
                    # Check for success and count (bc-utils approach)
                    if usage_data.get("success"):
                        current_count = int(usage_data.get('count', '0'))
                        logger.debug(f"bc-utils usage success: {usage_data['success']}, count: {current_count}")
                        return current_count
                    else:
                        logger.debug(f"Usage check unsuccessful: {usage_data}")
                        return None
                        
                except (json.JSONDecodeError, ValueError) as e:
                    logger.debug(f"Failed to parse usage response: {e}")
                    return None
            else:
                logger.debug(f"Usage check failed with status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.debug(f"Usage check error: {e}")
            return None

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

    def _fetch_historical_data_(self, instrument: str, frequency_attributes: FrequencyAttributes,
                               start_date, end_date, url: str, tz: str) -> Optional[DataFrame]:
        """Internal method to fetch historical data using exact bc-utils methodology."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Check server usage using exact bc-utils methodology
            current_usage = self._check_server_usage()
            if current_usage is not None:
                logger.info(f"bc-utils server usage: {current_usage} downloads used today (configured limit: {self.daily_limit})")
            else:
                logger.info(f"bc-utils usage check unavailable (configured limit: {self.daily_limit})")
            
            # Use exact bc-utils approach: /my/download endpoint
            # Note: bc-utils relies on server-side usage enforcement (250 paid/5 free per day)
            logger.info(f"Attempting bc-utils download for {instrument}")
            df = self._fetch_via_bc_utils_download(instrument, frequency_attributes, start_date, end_date, tz)
            if df is not None:
                return self._validate_data_availability(df, instrument, frequency_attributes, start_date, end_date)
            
            # No data found
            from vortex.exceptions.providers import DataNotFoundError
            raise DataNotFoundError(
                provider="barchart",
                symbol=instrument,
                period=frequency_attributes.frequency,
                start_date=start_date,
                end_date=end_date
            )
            
        except Exception as e:
            logger.error(f"bc-utils download failed for {instrument}: {e}")
            raise

    def _fetch_via_bc_utils_download(self, instrument: str, frequency_attributes: FrequencyAttributes,
                                    start_date, end_date, tz: str) -> Optional[DataFrame]:
        """Fetch data using exact bc-utils /my/download methodology."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Note: Using actual working API format from network capture (ISO dates)
        
        # Use the /my/download endpoint directly
        download_url = f"{self.BARCHART_URL}/my/download"
        
        try:
            logger.info(f"Using bc-utils /my/download endpoint for {instrument}")
            
            # Get CSRF token from home page (the only request we actually need)
            home_response = self.auth.session.get(self.BARCHART_URL)
            
            if home_response.status_code != 200:
                logger.error(f"Cannot access home page for CSRF token: {home_response.status_code}")
                return None
            
            # Extract CSRF token using shared method
            csrf_token = self._extract_csrf_token(home_response)
            if not csrf_token:
                logger.error("No CSRF token found on home page")
                return None
            
            # Prepare payload using actual working format from network capture
            payload = {
                '_token': csrf_token,
                'fileName': f'{instrument}_Daily_Historical+Data',
                'symbol': instrument,
                'fields': 'tradeTime.format(m/d/Y),openPrice,highPrice,lowPrice,lastPrice,priceChange,percentChange,volume',
                'startDate': start_date.strftime('%Y-%m-%d'),  # ISO format: 2025-01-01
                'endDate': end_date.strftime('%Y-%m-%d'),      # ISO format: 2025-06-30
                'type': 'eod',  # end of day (not 'daily')
                'orderBy': 'tradeTime',
                'orderDir': 'desc',
                'method': 'historical',  # This is crucial!
                'limit': '10000',
                'period': self._get_barchart_period(frequency_attributes.frequency),
                'customView': 'true',
                'exclude': '',
                'customGetParameters': '',
                'pageTitle': 'Historical+Data'
            }
            
            # For intraday data, update the type parameter
            if frequency_attributes.frequency != Period('1d'):
                payload['type'] = 'minutes'  # Override type for intraday
            
            logger.debug(f"bc-utils payload: {payload}")
            
            # Prepare headers for POST request  
            headers = {
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': self.BARCHART_URL,
                'Referer': self.BARCHART_URL,
                'X-CSRF-TOKEN': csrf_token
            }
            
            # Use the /my/download endpoint directly (this is what works!)
            logger.info(f"Using /my/download endpoint with meta CSRF token for {instrument}")
            response = self.auth.session.post(download_url, data=payload, headers=headers)
            
            logger.debug(f"Download response status: {response.status_code}")
            logger.debug(f"Download response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                logger.error(f"Download failed with status: {response.status_code}")
                logger.debug(f"Response content: {response.text[:300]}...")
                return None
            
            # Check if response contains CSV data
            logger.debug(f"Response content preview: {response.text[:300]}...")
            
            # Barchart CSV may use 'Time' instead of 'tradeTime'
            csv_indicators = ['tradeTime', 'Time', 'Open,High,Low', 'Last']
            has_csv_data = any(indicator in response.text for indicator in csv_indicators)
            
            if response.text and has_csv_data:
                logger.info(f"bc-utils download successful for {instrument}")
                return self._process_bc_utils_csv_response(response.text, frequency_attributes.frequency, tz)
            else:
                logger.warning(f"bc-utils download returned no CSV data for {instrument}")
                logger.debug(f"Full response content: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"bc-utils download failed for {instrument}: {e}")
            return None

    
    def _get_bc_utils_frequency(self, period) -> str:
        """Convert Period to bc-utils frequency parameter."""
        from vortex.models.period import Period
        
        # bc-utils uses 'daily' or 'minutes'
        if period == Period('1d'):
            return 'daily'
        else:
            return 'minutes'  # All intraday periods use 'minutes'
    
    def _get_barchart_period(self, period) -> str:
        """Convert Period to Barchart period parameter (for actual API)."""
        from vortex.models.period import Period
        
        # Map to Barchart period values
        period_mapping = {
            Period('1d'): 'daily',
            Period('1h'): 'hourly',
            Period('30m'): '30minute',
            Period('15m'): '15minute',
            Period('5m'): '5minute',
            Period('1m'): 'minute'
        }
        
        return period_mapping.get(period, 'daily')

    def _process_bc_utils_csv_response(self, csv_data: str, frequency, tz: str) -> Optional[DataFrame]:
        """Process CSV response from bc-utils /my/download endpoint."""
        import pandas as pd
        import io
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # bc-utils CSV format has different column names
            iostr = io.StringIO(csv_data)
            
            # Read CSV and check if it has data
            df = pd.read_csv(iostr)
            
            if df.empty:
                logger.warning("bc-utils returned empty CSV")
                return None
                
            logger.debug(f"bc-utils CSV columns: {list(df.columns)}")
            logger.debug(f"bc-utils CSV shape: {df.shape}")
            
            # Map bc-utils columns to standard format
            column_mapping = {
                'tradeTime': 'Time',
                'openPrice': 'Open', 
                'highPrice': 'High',
                'lowPrice': 'Low',
                'lastPrice': 'Last',
                'volume': 'Volume',
                'openInterest': 'Open Interest'
            }
            
            # Rename columns
            df.rename(columns=column_mapping, inplace=True)
            
            # Process with our standard parser (which expects Time, Last, etc.)
            from .parser import BarchartParser
            
            # Convert back to CSV string for parser
            csv_output = io.StringIO()
            df.to_csv(csv_output, index=False)
            csv_string = csv_output.getvalue()
            
            # Use our standard parser
            return BarchartParser.convert_downloaded_csv_to_df(frequency, csv_string, tz)
            
        except Exception as e:
            logger.error(f"Failed to process bc-utils CSV response: {e}")
            return None

    def _validate_data_availability(self, df: DataFrame, symbol: str, frequency_attributes: FrequencyAttributes = None, 
                                   start_date=None, end_date=None) -> DataFrame:
        """Validate downloaded data meets minimum requirements."""
        if df is None or df.empty:
            from vortex.exceptions.providers import DataNotFoundError
            if frequency_attributes and start_date and end_date:
                raise DataNotFoundError(
                    provider="barchart",
                    symbol=symbol,
                    period=frequency_attributes.frequency,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                # Fallback for cases where we don't have all parameters
                from vortex.exceptions.providers import DataProviderError
                raise DataProviderError("barchart", f"No data available for {symbol}")
        
        if len(df) < ProviderConstants.Barchart.MIN_REQUIRED_DATA_POINTS:
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