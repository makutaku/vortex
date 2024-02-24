from abc import ABC
from dataclasses import dataclass
from datetime import datetime

from data_providers.data_provider import DataProvider
from data_storage.data_storage import DataStorage
from data_storage.metadata import Metadata
from instruments.instrument import Instrument
from instruments.period import Period
from instruments.price_series import PriceSeries


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
        metadata = Metadata.create_metadata(
            df,
            self.data_provider.get_name(),
            self.instrument.get_symbol(),
            self.period,
            self.start_date,
            self.end_date)
        return PriceSeries(df, metadata)
