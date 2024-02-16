import logging
import os

import pandas as pd
from pandas import DataFrame

from contracts import AbstractContract
from data_storage.file_storage import FileStorage, DATE_TIME_FORMAT
from logging_utils import LoggingContext
from period import Period
from price_series import DATE_TIME_COLUMN


class CsvStorage(FileStorage):

    def __init__(self, base_path: str, dry_run: bool):
        super().__init__(base_path, dry_run)

    def _make_file_path_for_instrument(self, instrument: AbstractContract, period: Period):
        base_file_path = super()._make_file_path_for_instrument(instrument, period)
        return f"{base_file_path}.csv"

    def _load(self, file_path) -> DataFrame:
        with LoggingContext(entry_msg=f"Loading data from '{file_path}'",
                            success_msg=f"Loaded data from '{file_path}'",
                            success_level=logging.DEBUG):
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"Path '{file_path}' exists but it's not a file!")

            df = pd.read_csv(file_path)
            df[DATE_TIME_COLUMN] = pd.to_datetime(df[DATE_TIME_COLUMN], format=DATE_TIME_FORMAT)
            df = df.set_index(DATE_TIME_COLUMN).sort_index()
            return df

    def _persist(self, df: DataFrame, file_path: str) -> None:
        with LoggingContext(entry_msg=f"Saving data {df.shape} to '{file_path}'",
                            success_msg=f"Saved data {df.shape} to '{file_path}'",
                            failure_msg=f"Failed to save data {df.shape} to '{file_path}'"):
            df.sort_index().to_csv(file_path, date_format=DATE_TIME_FORMAT)
