import pandas as pd
from pandas import DataFrame

from .file_storage import FileStorage
from ..instruments.instrument import Instrument
from ..instruments.period import Period


class ParquetStorage(FileStorage):

    def __init__(self, base_path: str, dry_run: bool):
        super().__init__(base_path, dry_run)

    def _make_file_path_for_instrument(self, instrument: Instrument, period: Period):
        base_file_path = super()._make_file_path_for_instrument(instrument, period)
        return f"{base_file_path}.parquet"

    def _load(self, file_path) -> DataFrame:
        df = pd.read_parquet(file_path)
        df.sort_index()
        return df

    def _persist(self, df: DataFrame, file_path: str) -> None:
        df.sort_index().to_parquet(file_path, index=True)
