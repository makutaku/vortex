import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

from pandas import DataFrame

from instruments.instrument import Instrument
from instruments.period import Period, FrequencyAttributes
from retrying import retry


class HistoricalDataResult(enum.Enum):
    NONE = 1
    OK = 2
    EXISTS = 3
    EXCEED = 4
    LOW = 5


class DownloadError(Exception):
    def __init__(self, status, msg):
        self.status = status
        self.msg = msg


class LowDataError(Exception):
    pass


@dataclass
class NotFoundError(Exception):
    symbol: str
    period: Period
    start_date: datetime
    end_date: datetime
    http_code: int


class AllowanceLimitExceeded(Exception):
    def __init__(self, current_allowance, max_allowance):
        self.current_allowance = current_allowance
        self.max_allowance = max_allowance

    def __str__(self):
        return f"Allowance limit exceeded. Allowance is {self.current_allowance}. Limit is {self.max_allowance}."


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

    @retry(wait_exponential_multiplier=3000, wait_exponential_max=60000)
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
