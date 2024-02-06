import enum
from abc import ABC, abstractmethod

from price_series import PriceSeries


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


class NotFoundError(Exception):
    pass


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
    def fetch_futures_historical_data(self, symbol: str, period, start_date, end_date) -> PriceSeries:
        pass

    @abstractmethod
    def fetch_stock_historical_data(self, symbol: str, period, start_date, end_date) -> PriceSeries:
        pass

    @abstractmethod
    def get_futures_timeframes(self):
        pass

    @abstractmethod
    def get_stock_timeframes(self):
        pass

    def logout(self):
        pass
