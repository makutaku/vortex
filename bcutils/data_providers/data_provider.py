import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta

from pandas import DataFrame

from instruments.instrument import Instrument
from instruments.period import Period


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

    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_max_range(self, period: Period) -> timedelta:
        pass

    @abstractmethod
    def get_min_start(self, period: Period) -> datetime | None:
        pass

    @abstractmethod
    def fetch_historical_data(self,
                              instrument: Instrument,
                              period,
                              start_date, end_date) -> DataFrame | None:
        pass

    @abstractmethod
    def get_supported_timeframes(self, instrument: Instrument) -> list[Period]:
        pass

    def login(self):
        pass

    def logout(self):
        pass
