import logging
import os

import pandas as pd

from contracts import FutureContract, StockContract, Forex
from data_storage.data_storage import DataStorage
from data_storage.metadata import Metadata, MetadataHandler
from logging_utils import LoggingContext
from period import Period
from price_series import PriceSeries, DATE_TIME_COLUMN
from utils import create_full_path


class CsvStorage(DataStorage):

    def __init__(self, base_path: str, dry_run: bool):
        super().__init__(dry_run)
        self.base_path = base_path

    def persist_futures(self, downloaded_data: PriceSeries, contract: FutureContract, period: Period):
        file_path = self._make_file_path_for_futures(contract.instrument, contract.month, contract.year, period)
        create_full_path(file_path)
        CsvStorage.persist(downloaded_data, file_path)

    def persist_stock(self, downloaded_data: PriceSeries, contract: StockContract, period: Period):
        file_path = self._make_file_path_for_stock(contract.instrument, period)
        create_full_path(file_path)
        CsvStorage.persist(downloaded_data, file_path)

    def persist_forex(self, downloaded_data: PriceSeries, contract: Forex, period: Period):
        file_path = self._make_file_path_for_forex(contract.instrument, period)
        create_full_path(file_path)
        CsvStorage.persist(downloaded_data, file_path)

    def load_futures(self, contract: FutureContract, period: Period) -> PriceSeries:
        file_path = self._make_file_path_for_futures(contract.instrument, contract.month, contract.year, period)
        return CsvStorage.load(file_path)

    def load_stock(self, contract: StockContract, period: Period) -> PriceSeries:
        file_path = self._make_file_path_for_stock(contract.instrument, period)
        return CsvStorage.load(file_path)

    def load_forex(self, contract: Forex, period: Period) -> PriceSeries:
        file_path = self._make_file_path_for_forex(contract.instrument, period)
        return CsvStorage.load(file_path)

    def _make_file_path_for_futures(self, instrument: str, month: int, year: int, period: Period):
        date_code = str(year) + '{0:02d}'.format(month)
        filename = f"{instrument}_{date_code}00.csv"
        full_path = f"{self.base_path}/futures/{period.value}/{filename}"
        return full_path

    def _make_file_path_for_stock(self, symbol, period):
        filename = f"{symbol}.csv"
        full_path = f"{self.base_path}/stocks/{period.value}/{filename}"
        return full_path

    def _make_file_path_for_forex(self, symbol, period):
        filename = f"{symbol}.csv"
        full_path = f"{self.base_path}/forex/{period.value}/{filename}"
        return full_path

    @staticmethod
    def load_metadata(file_path: str) -> Metadata:
        metadata_handler = MetadataHandler(file_path)
        retrieved_metadata = metadata_handler.get_metadata()
        return retrieved_metadata

    @staticmethod
    def persist_metadata(file_path: str, metadata: Metadata) -> None:
        metadata_handler = MetadataHandler(file_path)
        metadata_handler.set_metadata(metadata)

    @staticmethod
    def load(file_path) -> PriceSeries:
        with LoggingContext(entry_msg=f"Loading data from '{file_path}'",
                            success_msg=f"Loaded data from '{file_path}'",
                            success_level=logging.DEBUG):
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"Path '{file_path}' exists but it's not a file!")

            metadata = CsvStorage.load_metadata(file_path)
            if not metadata:
                raise FileNotFoundError(f"Metadata file not found for '{file_path}'")

            df = pd.read_csv(file_path)
            df[DATE_TIME_COLUMN] = pd.to_datetime(df[DATE_TIME_COLUMN], format='%Y-%m-%dT%H:%M:%S%z')
            df = df.set_index(DATE_TIME_COLUMN).sort_index()

            return PriceSeries(df, metadata)

    @staticmethod
    def persist(downloaded_data: PriceSeries, file_path: str) -> None:
        df = downloaded_data.df
        with LoggingContext(entry_msg=f"Saving data {df.shape} to '{file_path}'",
                            success_msg=f"Saved data {df.shape} to '{file_path}'",
                            failure_msg=f"Failed to save data {df.shape} to '{file_path}'"):
            df.sort_index().to_csv(file_path, date_format='%Y-%m-%dT%H:%M:%S%z')
            CsvStorage.persist_metadata(file_path, downloaded_data.metadata)
