import os
import tempfile
from datetime import timedelta, datetime
from typing import List, Optional

import pandas as pd
import yfinance as yf
from pandas import DataFrame

from ..base import DataProvider
from ..interfaces import CacheManagerProtocol, DataFetcherProtocol, YahooCacheManager, YahooDataFetcher
from ..config import YahooProviderConfig, CircuitBreakerConfig
from vortex.models.columns import DATETIME_INDEX_NAME, validate_required_columns, get_provider_expected_columns, standardize_dataframe_columns
from vortex.exceptions.providers import DataNotFoundError, VortexConnectionError as ConnectionError
from vortex.core.error_handling.strategies import ErrorHandlingStrategy
from vortex.models.instrument import Instrument
from vortex.models.period import Period, FrequencyAttributes
from vortex.core.constants import ProviderConstants, TimeConstants


class YahooDataProvider(DataProvider):

    YAHOO_DATE_TIME_COLUMN = "Date"
    PROVIDER_NAME = "YahooFinance"

    def __init__(self, 
                 config: Optional[YahooProviderConfig] = None,
                 cache_manager: Optional[CacheManagerProtocol] = None, 
                 data_fetcher: Optional[DataFetcherProtocol] = None,
                 circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
                 raw_storage: Optional['RawDataStorage'] = None) -> None:
        """Initialize Yahoo provider with configuration and dependency injection.
        
        Args:
            config: Provider configuration (uses defaults if not provided)
            cache_manager: Optional cache manager (will be created if not provided)
            data_fetcher: Optional data fetcher (will be created if not provided)
            circuit_breaker_config: Optional circuit breaker configuration
            raw_storage: Optional raw data storage for raw data trail
        """
        # Initialize base with circuit breaker config and raw data storage
        super().__init__(circuit_breaker_config, raw_storage)
        
        # Store configuration  
        self.config = config or YahooProviderConfig()
        if not self.config.validate():
            raise ValueError("Invalid Yahoo provider configuration")
        
        # Inject dependencies with sensible defaults
        self._cache_manager = cache_manager or (
            self._create_default_cache_manager() if self.config.cache_enabled else None
        )
        self._data_fetcher = data_fetcher or YahooDataFetcher()
        
        # Initialize cache on first use, not in constructor
        self._cache_initialized = False
        
        self.logger.info(
            f"Initialized {self.PROVIDER_NAME} provider",
            extra={
                'provider': self.PROVIDER_NAME,
                'cache_enabled': self.config.cache_enabled,
                'validate_data_types': self.config.validate_data_types
            }
        )

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

    def validate_configuration(self) -> bool:
        """Validate Yahoo Finance provider configuration.
        
        Validates that cache directory is accessible and writable.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            # Ensure cache is initialized
            self._ensure_cache_initialized()
            
            # Check if cache directory is accessible and writable
            cache_dir = os.path.join(tempfile.gettempdir(), '.cache', 'py-yfinance')
            
            # Create directory if it doesn't exist
            os.makedirs(cache_dir, exist_ok=True)
            
            # Test write access
            test_file = os.path.join(cache_dir, '.vortex_test')
            try:
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                return True
            except (OSError, IOError):
                return False
                
        except Exception as e:
            logger.warning(f"Yahoo provider validation failed: {e}")
            return False

    def get_required_config_fields(self) -> list[str]:
        """Get list of required configuration fields for Yahoo Finance provider.
        
        Yahoo Finance doesn't require explicit credentials but needs cache access.
        
        Returns:
            List of required configuration field names (empty for Yahoo)
        """
        return []  # Yahoo Finance doesn't require explicit configuration fields

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
            
            # Apply standardized validation - this is handled by the base class wrapper
            # No need for provider-specific validation here
            
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
        """Fetch data using the injected data fetcher with basic processing."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Use injected data fetcher
            df = self._data_fetcher.fetch_historical_data(symbol, interval, start_date, end_date)

            # Save raw data for data trail before any processing
            if self._raw_storage and not df.empty:
                try:
                    # Convert DataFrame to CSV string for raw data storage
                    raw_csv = df.to_csv()
                    
                    # Create instrument for raw data storage
                    from vortex.models.stock import Stock
                    raw_instrument = Stock(id=symbol, symbol=symbol)
                    
                    request_metadata = {
                        'data_source': 'yfinance',
                        'interval': interval,
                        'start_date': start_date.isoformat(),
                        'end_date': end_date.isoformat(),
                        'original_columns': list(df.columns),
                        'data_shape': list(df.shape)
                    }
                    
                    self._save_raw_data(
                        instrument=raw_instrument,
                        raw_response=raw_csv,
                        request_metadata=request_metadata
                    )
                except Exception as raw_error:
                    logger.warning(f"Failed to save Yahoo data trail: {raw_error}")

            # Return raw data - validation will be handled by _validate_fetched_data()
            if df.empty:
                logger.debug(f"Yahoo Finance returned empty data for {symbol} ({interval}) from {start_date.date()} to {end_date.date()}")
                return df  # Return empty DataFrame, let validation handle it properly

            # Standardize columns using the centralized mapping system (for consistency)
            df = standardize_dataframe_columns(df, 'yahoo')
            
            df.index.name = DATETIME_INDEX_NAME
            df.index = pd.to_datetime(df.index, utc=True)
            
            logger.debug(f"Successfully fetched {len(df)} rows for {symbol} ({interval})")
            return df
            
        except Exception as e:
            # Provide better error context for debugging
            logger.error(f"Yahoo Finance API error for {symbol} ({interval}): {type(e).__name__}: {e}")
            raise ConnectionError("yahoo", f"Failed to fetch data for {symbol}: {e}") from e

