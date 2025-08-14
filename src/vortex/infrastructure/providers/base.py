import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List

from pandas import DataFrame

from vortex.models.instrument import Instrument
from vortex.models.period import Period, FrequencyAttributes
from vortex.exceptions.providers import (
    DataProviderError, DataNotFoundError, AllowanceLimitExceededError,
    VortexConnectionError as ConnectionError, AuthenticationError, RateLimitError
)
from retrying import retry




class HistoricalDataResult(enum.Enum):
    NONE = 1
    OK = 2
    EXISTS = 3
    EXCEED = 4
    LOW = 5


def should_retry(exception: Exception) -> bool:
    """Determine if an exception should trigger a retry.
    
    Do not retry for:
    - Data not found (permanent condition)
    - Allowance limits exceeded (need to wait or upgrade)
    - Authentication failures (need credential fix)
    - Configuration/validation errors (permanent condition)
    
    Do retry for:
    - Connection errors (transient network issues)
    - Rate limit errors (temporary API throttling)
    - General data provider errors (may be transient)
    """
    return not isinstance(exception, (
        DataNotFoundError, 
        AllowanceLimitExceededError, 
        AuthenticationError,
        ValueError  # Configuration/validation errors should not be retried
    ))


class DataProvider(ABC):
    """Abstract base class for all data providers.
    
    This class provides default implementations for common provider functionality
    and defines the interface that all providers must implement.
    
    Note: This class is aligned with the DataProviderProtocol to ensure
    consistency between interface definition and implementation.
    """

    def __str__(self) -> str:
        """String representation of the provider."""
        return self.get_name()

    @abstractmethod
    def get_name(self) -> str:
        """Get the provider name.
        
        Returns:
            The name of this data provider
        """
        pass

    def login(self) -> None:
        """Authenticate with the data provider.
        
        Default implementation is a no-op for providers that don't require authentication.
        Providers requiring authentication should override this method.
        """
        pass

    def logout(self) -> None:
        """End the session with the data provider.
        
        Default implementation is a no-op for providers that don't require session management.
        Providers with sessions should override this method.
        """
        pass

    def get_supported_timeframes(self) -> List[Period]:
        """Get list of supported time periods.
        
        Default implementation extracts periods from frequency attributes.
        
        Returns:
            List of Period objects supported by this provider
        """
        freq_dict = self._get_frequency_attr_dict()
        return list(freq_dict.keys())

    def get_max_range(self, period: Period) -> Optional[timedelta]:
        """Get maximum date range for a given period.
        
        Args:
            period: The time period to check
            
        Returns:
            Maximum timedelta for the period, or None if unlimited
        """
        freq_dict = self._get_frequency_attr_dict()
        freq_attr = freq_dict.get(period)
        return freq_attr.max_window if freq_attr else None

    def get_min_start(self, period: Period) -> Optional[datetime]:
        """Get minimum start date for a given period.
        
        Args:
            period: The time period to check
            
        Returns:
            Minimum start datetime for the period, or None if no limit
        """
        freq_dict = self._get_frequency_attr_dict()
        freq_attr = freq_dict.get(period)
        return freq_attr.get_min_start() if freq_attr else None

    @retry(wait_exponential_multiplier=2000,
           stop_max_attempt_number=5,
           retry_on_exception=should_retry)
    def fetch_historical_data(self,
                              instrument: Instrument,
                              period: Period,
                              start_date: datetime, end_date: datetime) -> Optional[DataFrame]:
        """Fetch historical data for an instrument.
        
        This method includes retry logic and error handling.
        
        Args:
            instrument: The financial instrument to fetch data for
            period: The time period/frequency for the data
            start_date: Start date for the data range
            end_date: End date for the data range
            
        Returns:
            DataFrame with OHLCV data, or None if no data available
        """
        freq_dict = self._get_frequency_attr_dict()
        freq_attr = freq_dict.get(period)
        if freq_attr is None:
            raise ValueError(f"Period {period} is not supported by provider {self.get_name()}")
        return self._fetch_historical_data(instrument, freq_attr, start_date, end_date)

    def validate_configuration(self) -> bool:
        """Validate provider configuration.
        
        Default implementation returns True for providers that don't require configuration.
        Providers with specific configuration requirements should override this method.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        return True

    def get_required_config_fields(self) -> List[str]:
        """Get list of required configuration fields.
        
        Default implementation returns empty list for providers that don't require configuration.
        Providers with configuration requirements should override this method.
        
        Returns:
            List of required configuration field names
        """
        return []

    def _get_frequency_attr_dict(self) -> dict:
        """Build a dictionary mapping periods to their frequency attributes.
        
        Returns:
            Dictionary with Period objects as keys and FrequencyAttributes as values
        """
        freq_dict = {attr.frequency: attr for attr in self._get_frequency_attributes()}
        return freq_dict

    @abstractmethod
    def _get_frequency_attributes(self) -> List[FrequencyAttributes]:
        """Get the frequency attributes supported by this provider.
        
        This is an internal method that subclasses must implement to define
        the time periods and their properties supported by the provider.
        
        Returns:
            List of FrequencyAttributes defining supported periods
        """
        pass

    @abstractmethod
    def _fetch_historical_data(self,
                               instrument: Instrument,
                               frequency_attributes: FrequencyAttributes,
                               start_date: datetime, end_date: datetime) -> Optional[DataFrame]:
        """Internal method to fetch historical data.
        
        This is the actual implementation method that subclasses must implement.
        It receives frequency attributes instead of just the period for more context.
        
        Args:
            instrument: The financial instrument to fetch data for
            frequency_attributes: Detailed frequency information including properties
            start_date: Start date for the data range
            end_date: End date for the data range
            
        Returns:
            DataFrame with OHLCV data, or None if no data available
        """
        pass
