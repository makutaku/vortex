import os
import tempfile
from datetime import timedelta, datetime
from typing import List, Optional

import pandas as pd
import yfinance as yf
from pandas import DataFrame

from ..base import DataProvider
from ..interfaces import CacheManagerProtocol, DataFetcherProtocol, YahooCacheManager, YahooDataFetcher
from vortex.models.columns import DATETIME_INDEX_NAME, validate_required_columns, get_provider_expected_columns, standardize_dataframe_columns
from vortex.exceptions.providers import DataNotFoundError, VortexConnectionError as ConnectionError
from vortex.core.error_handling.strategies import ErrorHandlingStrategy
from vortex.models.instrument import Instrument
from vortex.models.period import Period, FrequencyAttributes
from vortex.core.constants import ProviderConstants, TimeConstants


class YahooDataProvider(DataProvider):

    YAHOO_DATE_TIME_COLUMN = "Date"
    PROVIDER_NAME = "YahooFinance"

    def __init__(self, cache_manager: Optional[CacheManagerProtocol] = None, 
                 data_fetcher: Optional[DataFetcherProtocol] = None) -> None:
        super().__init__()  # Initialize standardized error handling
        
        # Inject dependencies with sensible defaults
        self._cache_manager = cache_manager or self._create_default_cache_manager()
        self._data_fetcher = data_fetcher or YahooDataFetcher()
        
        # Initialize cache on first use, not in constructor
        self._cache_initialized = False

    def get_name(self) -> str:
        return YahooDataProvider.PROVIDER_NAME
    
    def _create_default_cache_manager(self) -> YahooCacheManager:
        """Create default cache manager with standard cache directory."""
        cache_manager = YahooCacheManager()
        
        # Get the temporary folder for the current user
        temp_folder = tempfile.gettempdir()
        cache_folder = os.path.join(temp_folder, '.cache', 'py-yfinance')
        cache_manager.configure_cache(cache_folder)
        
        return cache_manager
    
    def _ensure_cache_initialized(self) -> None:
        """Ensure cache is initialized before data operations."""
        if not self._cache_initialized:
            self._cache_manager.configure_cache(
                os.path.join(tempfile.gettempdir(), '.cache', 'py-yfinance')
            )
            self._cache_initialized = True

    def _get_frequency_attributes(self) -> List[FrequencyAttributes]:

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
                                min_start=timedelta(days=TimeConstants.MIN_INTRADAY_DATA_DAYS),
                                properties={'interval': '1h'}),
            FrequencyAttributes(Period.Minute_30,
                                min_start=timedelta(days=ProviderConstants.Yahoo.INTRADAY_30MIN_DAYS_LIMIT),
                                properties={'interval': '30m'}),
            FrequencyAttributes(Period.Minute_15,
                                min_start=timedelta(days=ProviderConstants.Yahoo.INTRADAY_15MIN_DAYS_LIMIT),
                                properties={'interval': '15m'}),
            FrequencyAttributes(Period.Minute_5,
                                min_start=timedelta(days=ProviderConstants.Yahoo.INTRADAY_5MIN_DAYS_LIMIT),
                                properties={'interval': '5m'}),
            FrequencyAttributes(Period.Minute_1,
                                min_start=timedelta(days=ProviderConstants.Yahoo.INTRADAY_1MIN_DAYS_LIMIT),
                                properties={'interval': '1m'}),
        ]

    def _fetch_historical_data(self, instrument: Instrument,
                               frequency_attributes: FrequencyAttributes,
                               start: datetime, end: datetime) -> Optional[DataFrame]:
        """Fetch historical data with standardized error handling."""
        try:
            # Ensure cache is initialized before data operations
            self._ensure_cache_initialized()
            
            interval = frequency_attributes.properties.get('interval')
            df = self._fetch_data_using_injected_fetcher(
                instrument.get_symbol(), interval, start, end
            )
            
            # Check if data is empty and raise appropriate error
            if df is None or df.empty:
                raise self._create_data_not_found_error(
                    instrument, frequency_attributes.frequency, start, end,
                    "Yahoo Finance returned empty dataset"
                )
            
            return df
            
        except Exception as e:
            if isinstance(e, DataNotFoundError):
                raise  # Re-raise our standardized error
            
            # Handle other exceptions with standardized error handling
            return self._handle_provider_error(
                e, 
                "fetch_historical_data",
                strategy=ErrorHandlingStrategy.FAIL_FAST,
                instrument=instrument.get_symbol(),
                period=frequency_attributes.frequency,
                start_date=start,
                end_date=end
            )
    
    def _fetch_data_using_injected_fetcher(self, symbol: str, interval: str, start_date: datetime, end_date: datetime) -> DataFrame:
        """Fetch data using the injected data fetcher."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Use injected data fetcher
            df = self._data_fetcher.fetch_historical_data(symbol, interval, start_date, end_date)

            # Check for empty data immediately
            if df.empty:
                logger.warning(f"Yahoo Finance returned empty data for {symbol} ({interval}) from {start_date.date()} to {end_date.date()}")
                return df  # Return empty DataFrame, let calling method handle

            # Standardize columns using the centralized mapping system (for consistency)
            df = standardize_dataframe_columns(df, 'yahoo')
            
            df.index.name = DATETIME_INDEX_NAME
            df.index = pd.to_datetime(df.index, utc=True)
            
            # Validate expected Yahoo Finance columns (only data columns, not index)
            required_cols, optional_cols = get_provider_expected_columns('yahoo')
            missing_cols, found_cols = validate_required_columns(df.columns, required_cols, case_insensitive=True)
            if missing_cols:
                logger.warning(f"Missing expected Yahoo Finance columns: {missing_cols}. Found columns: {list(df.columns)}")
            
            logger.debug(f"Successfully fetched {len(df)} rows for {symbol} ({interval})")
            return df
            
        except Exception as e:
            # Provide better error context for debugging
            logger.error(f"Yahoo Finance API error for {symbol} ({interval}): {type(e).__name__}: {e}")
            raise ConnectionError("yahoo", f"Failed to fetch data for {symbol}: {e}") from e

