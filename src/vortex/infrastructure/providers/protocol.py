"""
Provider protocol definition for consistent provider interfaces.

This module defines the protocol (interface) that all data providers must implement,
ensuring consistency and enabling better dependency injection.
"""

from abc import abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional, Protocol, runtime_checkable

from pandas import DataFrame

from vortex.models.instrument import Instrument
from vortex.models.period import FrequencyAttributes, Period


@runtime_checkable
class DataProviderProtocol(Protocol):
    """Protocol defining the interface for all data providers.

    This protocol ensures consistent implementation across all providers
    and enables better type checking and dependency injection.

    Note: This protocol is aligned with the DataProvider base class to ensure
    consistency between interface definition and implementation.
    """

    def __str__(self) -> str:
        """String representation of the provider."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Get the provider name."""
        ...

    def login(self) -> None:
        """Authenticate with the data provider.

        Default implementation is a no-op for providers that don't require authentication.
        Providers requiring authentication should override this method.
        """
        ...

    def logout(self) -> None:
        """End the session with the data provider.

        Default implementation is a no-op for providers that don't require session management.
        Providers with sessions should override this method.
        """
        ...

    def get_supported_timeframes(self) -> List[Period]:
        """Get list of supported time periods.

        Default implementation extracts periods from frequency attributes.
        """
        ...

    def get_max_range(self, period: Period) -> Optional[timedelta]:
        """Get maximum date range for a given period.

        Args:
            period: The time period to check

        Returns:
            Maximum timedelta for the period, or None if unlimited
        """
        ...

    def get_min_start(self, period: Period) -> Optional[datetime]:
        """Get minimum start date for a given period.

        Args:
            period: The time period to check

        Returns:
            Minimum start datetime for the period, or None if no limit
        """
        ...

    def fetch_historical_data(
        self,
        instrument: Instrument,
        period: Period,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[DataFrame]:
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
        ...

    @abstractmethod
    def _get_frequency_attributes(self) -> List[FrequencyAttributes]:
        """Get the frequency attributes supported by this provider.

        This is an internal method that subclasses must implement to define
        the time periods and their properties supported by the provider.

        Returns:
            List of FrequencyAttributes defining supported periods
        """
        ...

    @abstractmethod
    def _fetch_historical_data(
        self,
        instrument: Instrument,
        frequency_attributes: FrequencyAttributes,
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[DataFrame]:
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
        ...


class ConfigurableProviderProtocol(DataProviderProtocol, Protocol):
    """Extended protocol for providers that require configuration."""

    @abstractmethod
    def validate_configuration(self) -> bool:
        """Validate provider configuration."""
        ...

    @abstractmethod
    def get_required_config_fields(self) -> List[str]:
        """Get list of required configuration fields."""
        ...
