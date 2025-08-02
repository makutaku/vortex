import logging
import os
from abc import abstractmethod
from datetime import datetime, timedelta
from functools import singledispatchmethod

import pytz
from pandas import DataFrame

from .data_storage import DataStorage
from .metadata import Metadata, MetadataHandler
from ..instruments.forex import Forex
from ..instruments.future import Future
from ..instruments.instrument import Instrument
from ..instruments.period import Period
from ..instruments.price_series import PriceSeries
from ..instruments.stock import Stock
from ..utils.logging_utils import LoggingContext
from ..utils.utils import create_full_path

DATE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S%z'


class FileStorage(DataStorage):

    def __init__(self, base_path: str, dry_run: bool):
        super().__init__(dry_run)
        self.base_path = base_path

    def persist(self,
                downloaded_data: PriceSeries,
                instrument: Instrument,
                period: Period):
        df = downloaded_data.df
        file_path = self._make_file_path_for_instrument(instrument, period)

        with LoggingContext(entry_msg=f"Saving data {df.shape} to '{file_path}'",
                            success_msg=f"Saved data {df.shape} to '{file_path}'",
                            failure_msg=f"Failed to save data {df.shape} to '{file_path}'"):
            create_full_path(file_path)
            self._persist(df, file_path)
            FileStorage.persist_metadata(file_path, downloaded_data.metadata)

    def load(self, instrument: Instrument, period: Period) -> PriceSeries:
        file_path = self._make_file_path_for_instrument(instrument, period)

        with LoggingContext(entry_msg=f"Loading data from '{file_path}'",
                            success_msg=f"Loaded data from '{file_path}'",
                            success_level=logging.DEBUG):
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"Path '{file_path}' exists but it's not a file!")

            metadata = FileStorage.load_metadata(file_path)
            if not metadata:
                raise FileNotFoundError(f"Metadata file not found for '{file_path}'")
            df = self._load(file_path)
            return PriceSeries(df, metadata)

    @abstractmethod
    def _load(self, file_path) -> DataFrame:
        pass

    @abstractmethod
    def _persist(self, downloaded_data: DataFrame, file_path: str) -> None:
        pass

    @singledispatchmethod
    def _make_file_path_for_instrument(self, future: Future, period: Period):
        date_code = str(future.year) + '{0:02d}'.format(future.month)
        full_path = f"{self.base_path}/futures/{period.value}/{future.id}/{future.id}_{date_code}00"
        return full_path

    @_make_file_path_for_instrument.register
    def _(self, stock: Stock, period):
        full_path = f"{self.base_path}/stocks/{period.value}/{stock.id}"
        return full_path

    @_make_file_path_for_instrument.register
    def _(self, forex: Forex, period):
        full_path = f"{self.base_path}/forex/{period.value}/{forex.id}"
        return full_path

    @staticmethod
    def load_metadata(file_path: str) -> Metadata:
        metadata_handler = MetadataHandler(file_path)
        retrieved_metadata = metadata_handler.get_metadata()
        # Following is a temporary hack to force some back-filling:
        # retrieved_metadata.end_date = datetime.now(pytz.timezone('America/Chicago')) - timedelta(days=2)
        return retrieved_metadata

    @staticmethod
    def persist_metadata(file_path: str, metadata: Metadata) -> None:
        metadata_handler = MetadataHandler(file_path)
        metadata_handler.set_metadata(metadata)
