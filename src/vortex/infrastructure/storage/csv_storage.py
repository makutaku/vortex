import pandas as pd
from pandas import DataFrame

from vortex.models.columns import DATETIME_COLUMN_NAME, DATETIME_INDEX_NAME
from vortex.models.instrument import Instrument
from vortex.models.period import Period

from .file_storage import DATE_TIME_FORMAT, FileStorage


class CsvStorage(FileStorage):
    def __init__(self, base_path: str, dry_run: bool):
        super().__init__(base_path, dry_run)

    def _make_file_path_for_instrument(self, instrument: Instrument, period: Period):
        base_file_path = super()._make_file_path_for_instrument(instrument, period)
        return f"{base_file_path}.csv"

    def _load(self, file_path) -> DataFrame:
        df = pd.read_csv(file_path)
        # Convert datetime column to proper datetime type
        df[DATETIME_COLUMN_NAME] = pd.to_datetime(
            df[DATETIME_COLUMN_NAME], format=DATE_TIME_FORMAT
        )
        # Set as index and ensure it has the correct name
        df = df.set_index(DATETIME_COLUMN_NAME).sort_index()
        df.index.name = DATETIME_INDEX_NAME
        return df

    def _persist(self, df: DataFrame, file_path: str) -> None:
        df.sort_index().to_csv(file_path, date_format=DATE_TIME_FORMAT)
