import pandas as pd
from pandas import DataFrame

from .file_storage import FileStorage, DATE_TIME_FORMAT
from vortex.models.columns import DATE_TIME_COLUMN
from vortex.models.instrument import Instrument
from vortex.models.period import Period


class CsvStorage(FileStorage):

    def __init__(self, base_path: str, dry_run: bool):
        super().__init__(base_path, dry_run)

    def _make_file_path_for_instrument(self, instrument: Instrument, period: Period):
        base_file_path = super()._make_file_path_for_instrument(instrument, period)
        return f"{base_file_path}.csv"

    def _load(self, file_path) -> DataFrame:
        df = pd.read_csv(file_path)
        df[DATE_TIME_COLUMN] = pd.to_datetime(df[DATE_TIME_COLUMN], format=DATE_TIME_FORMAT)
        df = df.set_index(DATE_TIME_COLUMN).sort_index()
        return df

    def _persist(self, df: DataFrame, file_path: str) -> None:
        df.sort_index().to_csv(file_path, date_format=DATE_TIME_FORMAT)
