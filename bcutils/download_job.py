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

    def load(self) -> PriceSeries:
        return self.data_storage.load(self.contract, self.period)

    def persist(self, downloaded_data: PriceSeries):
        self.data_storage.persist(downloaded_data, self.contract, self.period)

    def fetch(self) -> PriceSeries:
        return self.data_provider.fetch_historical_data(
            self.contract, self.period, self.start_date, self.end_date)

