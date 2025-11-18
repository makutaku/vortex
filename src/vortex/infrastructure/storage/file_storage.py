import logging
import os
from abc import abstractmethod
from functools import singledispatchmethod

from pandas import DataFrame

from vortex.models.forex import Forex
from vortex.models.future import Future
from vortex.models.instrument import Instrument
from vortex.models.period import Period
from vortex.models.price_series import PriceSeries
from vortex.models.stock import Stock
from vortex.utils.logging_utils import LoggingConfiguration, LoggingContext
from vortex.utils.utils import create_full_path

from .data_storage import DataStorage
from .metadata import Metadata, MetadataHandler

DATE_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


class FileStorage(DataStorage):
    def __init__(self, base_path: str, dry_run: bool):
        super().__init__(dry_run)
        self.base_path = base_path

    def persist(
        self, downloaded_data: PriceSeries, instrument: Instrument, period: Period
    ):
        df = downloaded_data.df
        file_path = self._make_file_path_for_instrument(instrument, period)

        config = LoggingConfiguration(
            entry_msg=f"Saving data {df.shape} to '{file_path}'",
            success_msg=f"Saved data {df.shape} to '{file_path}'",
            failure_msg=f"Failed to save data {df.shape} to '{file_path}'",
        )
        with LoggingContext(config):
            create_full_path(file_path)
            self._persist(df, file_path)
            FileStorage.persist_metadata(file_path, downloaded_data.metadata)

    def load(self, instrument: Instrument, period: Period) -> PriceSeries:
        file_path = self._make_file_path_for_instrument(instrument, period)

        config = LoggingConfiguration(
            entry_msg=f"Loading data from '{file_path}'",
            success_msg=f"Loaded data from '{file_path}'",
            success_level=logging.DEBUG,
        )
        with LoggingContext(config):
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)
            if not os.path.isfile(file_path):
                raise FileNotFoundError(
                    f"Path '{file_path}' exists but it's not a file!"
                )

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
        date_code = str(future.year) + "{0:02d}".format(future.month)
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
        return retrieved_metadata

    @staticmethod
    def persist_metadata(file_path: str, metadata: Metadata) -> None:
        metadata_handler = MetadataHandler(file_path)
        metadata_handler.set_metadata(metadata)
