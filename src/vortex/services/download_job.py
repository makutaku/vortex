from abc import ABC
from dataclasses import dataclass
from datetime import datetime

from vortex.infrastructure.providers.base import DataProvider
from vortex.infrastructure.storage.data_storage import DataStorage
from vortex.models.metadata import Metadata
from vortex.models.instrument import Instrument
from vortex.models.period import Period
from vortex.models.price_series import PriceSeries


@dataclass
class DownloadJob(ABC):
    data_provider: DataProvider
    data_storage: DataStorage
    instrument: Instrument
    period: Period
    start_date: datetime
    end_date: datetime
    backup_data_storage: DataStorage = None

    def __post_init__(self):
        if self.start_date > self.end_date:
            raise ValueError(f"start_date must come before end_date")

    def __str__(self):
        return (f"{self.instrument}|{self.period}|"
                f"{self.start_date.strftime('%Y-%m-%d')}|{self.end_date.strftime('%Y-%m-%d')}")

    def load(self) -> PriceSeries:
        try:
            return self.data_storage.load(self.instrument, self.period)
        except FileNotFoundError as e:
            if self.backup_data_storage:
                # logging.warning(
                # "Failed to load price from primary storage. Trying secondary storage", e)
                return self.backup_data_storage.load(self.instrument, self.period)
            else:
                raise

    def persist(self, downloaded_data: PriceSeries, backup=True):
        self.data_storage.persist(downloaded_data, self.instrument, self.period)

        if backup and self.backup_data_storage:
            self.backup_data_storage.persist(downloaded_data, self.instrument, self.period)

    def fetch(self) -> PriceSeries:
        df = self.data_provider.fetch_historical_data(
            self.instrument, self.period, self.start_date, self.end_date)
        
        try:
            metadata = Metadata.create_metadata(
                df,
                self.data_provider.get_name(),
                self.instrument.get_symbol(),
                self.period,
                self.start_date,
                self.end_date)
        except ValueError as e:
            # Handle invalid data from provider
            raise ValueError(f"Provider {self.data_provider.get_name()} returned invalid data for "
                           f"{self.instrument.get_symbol()} {self.period}: {str(e)}")
        
        return PriceSeries(df, metadata)
