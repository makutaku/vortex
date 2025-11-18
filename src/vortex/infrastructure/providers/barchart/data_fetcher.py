"""
Barchart data fetching strategies.

Extracted from BarchartProvider to implement single responsibility principle.
Handles different strategies for fetching data (bc-utils style download).
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
from pandas import DataFrame

from vortex.models.period import FrequencyAttributes
from vortex.models.forex import Forex
from vortex.models.future import Future
from vortex.models.stock import Stock
from vortex.models.price_series import FUTURES_SOURCE_TIME_ZONE, STOCK_SOURCE_TIME_ZONE
from vortex.exceptions.providers import DataNotFoundError, DataProviderError
from vortex.constants import NetworkConstants, ProviderConstants

from .auth import BarchartAuth
from .client import BarchartClient
from .parser import BarchartParser


class BarchartDataFetcher:
    """Handles data fetching strategies for Barchart provider."""
    
    def __init__(self, auth: BarchartAuth, client: BarchartClient, parser: BarchartParser):
        self.auth = auth
        self.client = client
        self.parser = parser
        self.logger = logging.getLogger(__name__)
    
    def fetch_historical_data(self, instrument, frequency_attributes: FrequencyAttributes,
                            start_date: datetime, end_date: datetime) -> Optional[DataFrame]:
        """Fetch historical data using appropriate strategy based on instrument type."""
        if isinstance(instrument, Future):
            return self._fetch_future_data(instrument, frequency_attributes, start_date, end_date)
        elif isinstance(instrument, Stock):
            return self._fetch_stock_data(instrument, frequency_attributes, start_date, end_date)
        elif isinstance(instrument, Forex):
            return self._fetch_forex_data(instrument, frequency_attributes, start_date, end_date)
        else:
            return self._fetch_generic_data(str(instrument), frequency_attributes, start_date, end_date)
    
    def _fetch_future_data(self, instrument: Future, frequency_attributes: FrequencyAttributes,
                          start_date: datetime, end_date: datetime) -> Optional[DataFrame]:
        """Fetch data for futures instruments."""
        symbol = instrument.get_symbol() if hasattr(instrument, 'get_symbol') else str(instrument)
        return self._fetch_via_bc_utils_download(
            symbol, frequency_attributes, start_date, end_date, FUTURES_SOURCE_TIME_ZONE
        )
    
    def _fetch_stock_data(self, instrument: Stock, frequency_attributes: FrequencyAttributes,
                         start_date: datetime, end_date: datetime) -> Optional[DataFrame]:
        """Fetch data for stock instruments."""
        symbol = instrument.get_symbol() if hasattr(instrument, 'get_symbol') else str(instrument)
        return self._fetch_via_bc_utils_download(
            symbol, frequency_attributes, start_date, end_date, STOCK_SOURCE_TIME_ZONE
        )
    
    def _fetch_forex_data(self, instrument: Forex, frequency_attributes: FrequencyAttributes,
                         start_date: datetime, end_date: datetime) -> Optional[DataFrame]:
        """Fetch data for forex instruments."""
        symbol = instrument.get_symbol() if hasattr(instrument, 'get_symbol') else str(instrument)
        return self._fetch_via_bc_utils_download(
            symbol, frequency_attributes, start_date, end_date, STOCK_SOURCE_TIME_ZONE
        )
    
    def _fetch_generic_data(self, instrument: str, frequency_attributes: FrequencyAttributes,
                           start_date: datetime, end_date: datetime) -> Optional[DataFrame]:
        """Fetch data for generic instrument strings."""
        return self._fetch_via_bc_utils_download(
            instrument, frequency_attributes, start_date, end_date, STOCK_SOURCE_TIME_ZONE
        )
    
    def _fetch_via_bc_utils_download(self, instrument: str, frequency_attributes: FrequencyAttributes,
                                   start_date: datetime, end_date: datetime, tz: str) -> Optional[DataFrame]:
        """Fetch data using bc-utils methodology (GET home, POST with onlyCheckPermissions)."""
        try:
            # Use exact bc-utils approach: GET home page for CSRF token, then POST with onlyCheckPermissions
            url = ProviderConstants.Barchart.BASE_URL
            home_response = self.auth.session.get(url, timeout=NetworkConstants.DEFAULT_REQUEST_TIMEOUT)
            
            if home_response.status_code != NetworkConstants.HTTP_OK:
                self.logger.error(
                    f"Cannot access home page for CSRF token: {home_response.status_code}",
                    extra={'instrument': instrument, 'url': url}
                )
                return None
            
            # Extract CSRF token using shared method
            csrf_token = self._extract_csrf_token(home_response)
            if not csrf_token:
                self.logger.warning(
                    "No CSRF token found on home page - authentication may have failed",
                    extra={'instrument': instrument}
                )
                return None
            
            # Perform actual download with bc-utils methodology
            return self._perform_bc_utils_download(instrument, frequency_attributes, start_date, end_date, csrf_token)
            
        except DataNotFoundError:
            # Re-raise DataNotFoundError to be handled by caller
            raise
        except Exception as e:
            self.logger.error(f"Error in bc-utils download for {instrument}: {e}")
            raise DataProviderError("barchart", f"Failed to fetch data for {instrument}: {e}")
    
    def _perform_bc_utils_download(self, instrument: str, frequency_attributes: FrequencyAttributes,
                                 start_date: datetime, end_date: datetime, csrf_token: str) -> Optional[DataFrame]:
        """Perform the actual bc-utils style download."""
        # Use the correct payload format from the original working implementation
        from vortex.models.period import Period
        
        # Determine appropriate file name based on frequency  
        file_suffix = "Daily_Historical+Data" if frequency_attributes.frequency == Period('1d') else "Intraday_Historical+Data"
        
        payload = {
            '_token': csrf_token,
            'fileName': f'{instrument}_{file_suffix}',
            'symbol': instrument,
            'startDate': start_date.strftime('%Y-%m-%d'),  # ISO format
            'endDate': end_date.strftime('%Y-%m-%d'),      # ISO format
            'type': 'eod',  # end of day
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
        
        headers = {
            'User-Agent': NetworkConstants.DEFAULT_USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': ProviderConstants.Barchart.BASE_URL,
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'X-CSRF-TOKEN': csrf_token
        }
        
        download_url = ProviderConstants.Barchart.BASE_URL + ProviderConstants.Barchart.DOWNLOAD_ENDPOINT
        
        self.logger.info(f"Using /my/download endpoint with meta CSRF token for {instrument}")
        
        try:
            resp = self.auth.session.post(download_url, headers=headers, data=payload, 
                                        timeout=NetworkConstants.LONG_REQUEST_TIMEOUT)
            
            if resp.status_code != NetworkConstants.HTTP_OK:
                if resp.status_code == NetworkConstants.HTTP_NOT_FOUND:
                    self.logger.info(f"Data not found for {instrument} (404)")
                    raise DataNotFoundError("barchart", instrument, frequency_attributes.frequency, 
                                           start_date, end_date, resp.status_code)
                else:
                    self.logger.error(f"Download failed for {instrument}: {resp.status_code}")
                    return None
            
            # Process CSV response
            frequency = self._get_barchart_period(frequency_attributes.frequency)
            return self._process_bc_utils_csv_response(resp.text, frequency, STOCK_SOURCE_TIME_ZONE)
            
        except DataNotFoundError:
            # Re-raise DataNotFoundError to be handled by caller
            raise
        except Exception as e:
            self.logger.error(f"Error downloading {instrument}: {e}")
            return None
    
    def _extract_csrf_token(self, home_response) -> Optional[str]:
        """Extract CSRF token from Barchart home page response."""
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(home_response.text, 'html.parser')
            
            # Look for meta CSRF token (the correct token type)
            meta_token = soup.find('meta', {'name': 'csrf-token'})
            if meta_token:
                csrf_token = meta_token.get('content')
                self.logger.debug(f"Found meta CSRF token: {csrf_token[:20]}...")
                return csrf_token
            else:
                self.logger.debug("No meta CSRF token found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting CSRF token: {e}")
            return None
    
    def _get_bc_utils_frequency(self, period) -> str:
        """Convert Period to bc-utils frequency string."""
        period_mapping = {
            'daily': 'daily',
            '1d': 'daily',
            'hourly': 'hourly',
            '1h': 'hourly',
            'weekly': 'weekly',
            '1w': 'weekly',
            'monthly': 'monthly',
            '1m': 'monthly'
        }
        
        if hasattr(period, 'value'):
            period_str = period.value
        else:
            period_str = str(period)
        
        return period_mapping.get(period_str.lower(), 'daily')
    
    def _get_barchart_period(self, period) -> str:
        """Convert Period to Barchart period string."""
        if hasattr(period, 'value'):
            period_str = period.value
        else:
            period_str = str(period)
        
        period_mapping = {
            'daily': 'daily',
            '1d': 'daily',
            'hourly': 'hourly', 
            '1h': 'hourly',
            'weekly': 'weekly',
            '1w': 'weekly',
            'monthly': 'monthly',
            '1m': 'monthly'
        }
        
        return period_mapping.get(period_str.lower(), 'daily')
    
    def _process_bc_utils_csv_response(self, csv_data: str, frequency: str, tz: str) -> Optional[DataFrame]:
        """Process CSV response from bc-utils download."""
        try:
            # Convert frequency string back to Period enum for parser
            from vortex.models.period import Period
            period_mapping = {
                'daily': Period.Daily,
                'hourly': Period.Hourly,
                'weekly': Period.Weekly,
                'monthly': Period.Monthly
            }
            period = period_mapping.get(frequency, Period.Daily)
            return self.parser.convert_downloaded_csv_to_df(period, csv_data, tz)
        except Exception as e:
            self.logger.error(f"Error processing CSV response: {e}")
            return None