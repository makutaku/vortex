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
from vortex.models.period import Period, FrequencyAttributes


@runtime_checkable
class DataProviderProtocol(Protocol):
    """Protocol defining the interface for all data providers.
    
    This protocol ensures consistent implementation across all providers
    and enables better type checking and dependency injection.
    """
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the provider name."""
        ...
    
    @abstractmethod
    def login(self) -> None:
        """Authenticate with the data provider."""
        ...
    
    @abstractmethod
    def logout(self) -> None:
        """End the session with the data provider."""
        ...
    
    @abstractmethod
    def get_supported_timeframes(self) -> List[Period]:
        """Get list of supported time periods."""
        ...
    
    @abstractmethod
    def get_max_range(self, period: Period) -> Optional[timedelta]:
        """Get maximum date range for a given period."""
        ...
    
    @abstractmethod
    def get_min_start(self, period: Period) -> Optional[datetime]:
        """Get minimum start date for a given period."""
        ...
    
    @abstractmethod
    def fetch_historical_data(
        self,
        instrument: Instrument,
        period: Period,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[DataFrame]:
        """Fetch historical data for an instrument."""
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