import pandas as pd
from pandas import DataFrame

from contracts import AbstractContract
from data_storage.file_storage import FileStorage, DATE_TIME_FORMAT
from period import Period
from price_series import DATE_TIME_COLUMN


class ParquetStorage(FileStorage):

    def __init__(self, base_path: str, dry_run: bool):
        super().__init__(base_path, dry_run)

    def _make_file_path_for_instrument(self, instrument: AbstractContract, period: Period):
        base_file_path = super()._make_file_path_for_instrument(instrument, period)
        return f"{base_file_path}.parquet"

    def _load(self, file_path) -> DataFrame:
        df = pd.read_parquet(file_path)
        df.sort_index()
        return df

    def _persist(self, df: DataFrame, file_path: str) -> None:
        df.sort_index().to_parquet(file_path, index=True)
