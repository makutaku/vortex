from abc import ABC, abstractmethod

from contracts import AbstractContract
from period import Period
from price_series import PriceSeries


class DataStorage(ABC):

    def __init__(self, dry_run: bool):
        self.dry_run = dry_run

    @abstractmethod
    def load(self, contract: AbstractContract, period: Period) -> PriceSeries:
        pass

    @abstractmethod
    def persist(self, downloaded_data: PriceSeries, contract: AbstractContract, period: Period):
        pass
