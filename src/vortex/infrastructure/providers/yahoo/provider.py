import os
import tempfile
from datetime import timedelta, datetime
from typing import List, Optional

import pandas as pd
import yfinance as yf
from pandas import DataFrame

from ..base import DataProvider
from vortex.models.columns import DATETIME_INDEX_NAME, validate_required_columns, get_provider_expected_columns, standardize_dataframe_columns
from vortex.exceptions.providers import DataNotFoundError, VortexConnectionError as ConnectionError
from vortex.core.error_handling.strategies import ErrorHandlingStrategy
from vortex.models.instrument import Instrument
from vortex.models.period import Period, FrequencyAttributes
from vortex.core.constants import ProviderConstants, TimeConstants


class YahooDataProvider(DataProvider):

    YAHOO_DATE_TIME_COLUMN = "Date"
    PROVIDER_NAME = "YahooFinance"

    def __init__(self) -> None:
        super().__init__()  # Initialize standardized error handling
        YahooDataProvider.set_yf_tz_cache()

    def get_name(self) -> str:
        return YahooDataProvider.PROVIDER_NAME

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
            interval = frequency_attributes.properties.get('interval')
            df = YahooDataProvider.fetch_historical_data_for_symbol(
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

    @staticmethod
    def fetch_historical_data_for_symbol(symbol: str, interval: str, start_date: datetime, end_date: datetime) -> DataFrame:
        """Fetch data from Yahoo Finance with improved error handling."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval,
                back_adjust=True,
                repair=True,
                raise_errors=True
            )

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

    @staticmethod
    def set_yf_tz_cache() -> None:
        # Get the temporary folder for the current user
        temp_folder = tempfile.gettempdir()

        # Create the subfolder "/.cache/py-yfinance" under the temporary folder
        cache_folder = os.path.join(temp_folder, '.cache', 'py-yfinance')
        os.makedirs(cache_folder, exist_ok=True)

        # Set the cache location for timezone data
        yf.set_tz_cache_location(cache_folder)
