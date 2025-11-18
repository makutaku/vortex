import logging

import pandas as pd
from pandas import DataFrame

from vortex.models.columns import (
    DATETIME_INDEX_NAME,
    REQUIRED_DATA_COLUMNS,
    validate_required_columns,
)
from vortex.models.instrument import Instrument
from vortex.models.period import Period

from .file_storage import FileStorage


class ParquetStorage(FileStorage):
    def __init__(self, base_path: str, dry_run: bool):
        super().__init__(base_path, dry_run)

    def _make_file_path_for_instrument(self, instrument: Instrument, period: Period):
        base_file_path = super()._make_file_path_for_instrument(instrument, period)
        return f"{base_file_path}.parquet"

    def _load(self, file_path) -> DataFrame:
        df = pd.read_parquet(file_path)

        # Add column validation for data columns (not index)
        # Check that index name is correct
        if df.index.name != DATETIME_INDEX_NAME:
            logging.warning(
                f"Parquet file {file_path} has incorrect index name: {df.index.name}, expected: {DATETIME_INDEX_NAME}"
            )

        # Check data columns
        missing_cols, found_cols = validate_required_columns(
            df.columns, REQUIRED_DATA_COLUMNS, case_insensitive=True
        )
        if missing_cols:
            logging.warning(
                f"Parquet file {file_path} missing expected columns: {missing_cols}"
            )

        return df.sort_index()

    def _persist(self, df: DataFrame, file_path: str) -> None:
        df.sort_index().to_parquet(file_path, index=True)
