from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from contracts import AbstractContract, FutureContract, StockContract, Forex
from data_providers.data_provider import DataProvider
from data_storage.data_storage import DataStorage
from period import Period
from price_series import PriceSeries


@dataclass
class DownloadJob(ABC):
    data_provider: DataProvider
    data_storage: DataStorage
    contract: AbstractContract
    period: Period
    start_date: datetime
    end_date: datetime

    def __str__(self):
        return (f"{self.contract}|{self.period}|"
                f"{self.start_date.strftime('%Y-%m-%d')}|{self.end_date.strftime('%Y-%m-%d')}")

    @abstractmethod
    def load(self) -> PriceSeries:
        pass

    @abstractmethod
    def persist(self, downloaded_data: PriceSeries):
        pass

    @abstractmethod
    def fetch(self) -> PriceSeries:
        pass


class FutureDownloadJob(DownloadJob):
    def load(self) -> PriceSeries:
        return self.data_storage.load_futures(cast(FutureContract, self.contract), self.period)

    def persist(self, downloaded_data: PriceSeries):
        self.data_storage.persist_futures(downloaded_data, cast(FutureContract, self.contract), self.period)

    def fetch(self) -> PriceSeries:
        contract: FutureContract = cast(FutureContract, self.contract)
        return self.data_provider.fetch_futures_historical_data(contract.get_symbol(), self.period, self.start_date,
                                                                self.end_date)


class StockDownloadJob(DownloadJob):
    def load(self) -> PriceSeries:
        return self.data_storage.load_stock(cast(StockContract, self.contract), self.period)

    def persist(self, downloaded_data: PriceSeries):
        self.data_storage.persist_stock(downloaded_data, cast(StockContract, self.contract), self.period)

    def fetch(self) -> PriceSeries:
        contract: StockContract = cast(StockContract, self.contract)
        return self.data_provider.fetch_stock_historical_data(contract.get_symbol(), self.period, self.start_date,
                                                              self.end_date)


class ForexDownloadJob(DownloadJob):
    def load(self) -> PriceSeries:
        return self.data_storage.load_forex(cast(Forex, self.contract), self.period)

    def persist(self, downloaded_data: PriceSeries):
        self.data_storage.persist_forex(downloaded_data, cast(Forex, self.contract), self.period)

    def fetch(self) -> PriceSeries:
        contract: Forex = cast(Forex, self.contract)
        return self.data_provider.fetch_forex_historical_data(contract.get_symbol(), self.period, self.start_date,
                                                              self.end_date)
