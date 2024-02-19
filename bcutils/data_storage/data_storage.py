from abc import ABC, abstractmethod

from instruments.instrument import Instrument
from instruments.period import Period
from instruments.price_series import PriceSeries


class DataStorage(ABC):

    def __init__(self, dry_run: bool):
        self.dry_run = dry_run

    @abstractmethod
    def load(self, contract: Instrument, period: Period) -> PriceSeries:
        pass

    @abstractmethod
    def persist(self, downloaded_data: PriceSeries, contract: Instrument, period: Period):
        pass
