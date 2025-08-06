import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

from pandas import DataFrame

from vortex.models.instrument import Instrument
from vortex.models.period import Period, FrequencyAttributes
from vortex.exceptions.providers import (
    DataProviderError, DataNotFoundError, AllowanceLimitExceededError,
    VortexConnectionError as ConnectionError, AuthenticationError, RateLimitError
)
from retrying import retry


# Legacy exception aliases removed - use direct imports from vortex.exceptions instead


class HistoricalDataResult(enum.Enum):
    NONE = 1
    OK = 2
    EXISTS = 3
    EXCEED = 4
    LOW = 5


def should_retry(exception):
    """Determine if an exception should trigger a retry.
    
    Do not retry for:
    - Data not found (permanent condition)
    - Allowance limits exceeded (need to wait or upgrade)
    - Authentication failures (need credential fix)
    
    Do retry for:
    - Connection errors (transient network issues)
    - Rate limit errors (temporary API throttling)
    - General data provider errors (may be transient)
    """
    return not isinstance(exception, (
        DataNotFoundError, 
        AllowanceLimitExceededError, 
        AuthenticationError
    ))


class DataProvider(ABC):

    def __str__(self):
        return self.get_name()

    @abstractmethod
    def get_name(self) -> str:
        pass

    def login(self):
        pass

    def logout(self):
        pass

    def get_supported_timeframes(self) -> list[Period]:
        freq_dict = self._get_frequency_attr_dict()
        return list(freq_dict.keys())

    def get_max_range(self, period: Period) -> timedelta | None:
        freq_dict = self._get_frequency_attr_dict()
        return freq_dict.get(period).max_window

    def get_min_start(self, period: Period) -> datetime | None:
        freq_dict = self._get_frequency_attr_dict()
        return freq_dict.get(period).get_min_start()

    @retry(wait_exponential_multiplier=2000,
           stop_max_attempt_number=5,
           retry_on_exception=should_retry)
    def fetch_historical_data(self,
                              instrument: Instrument,
                              period,
                              start_date, end_date) -> DataFrame | None:
        freq_dict = self._get_frequency_attr_dict()
        freq_attr = freq_dict.get(period)
        return self._fetch_historical_data(instrument, freq_attr, start_date, end_date)

    def _get_frequency_attr_dict(self):
        freq_dict = {attr.frequency: attr for attr in self._get_frequency_attributes()}
        return freq_dict

    @abstractmethod
    def _get_frequency_attributes(self) -> list[FrequencyAttributes]:
        pass

    @abstractmethod
    def _fetch_historical_data(self,
                               instrument: Instrument,
                               frequency_attributes: FrequencyAttributes,
                               start_date, end_date) -> DataFrame | None:
        pass
