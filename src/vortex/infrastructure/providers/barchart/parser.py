"""
Barchart data parsing and conversion utilities.

Handles CSV parsing, DataFrame conversion, and data formatting for Barchart data.
"""

import io
import logging

import pandas as pd

from vortex.models.columns import DATETIME_INDEX_NAME, standardize_dataframe_columns
from vortex.models.period import Period


class BarchartParser:
    """Handles parsing and conversion of Barchart data."""

    BARCHART_DATE_TIME_COLUMN = "Time"
    BARCHART_CLOSE_COLUMN = "Last"

    def convert_downloaded_csv_to_df(
        self, period: Period, data: str, tz: str
    ) -> pd.DataFrame:
        """Convert downloaded CSV data to a standardized DataFrame."""
        # Debug: log raw CSV content to understand what we're receiving
        debug_length = getattr(self, "debug_log_length", 500)
        logging.debug(
            f"Raw CSV data from Barchart: {data[:debug_length]}..."
        )  # First N chars

        iostr = io.StringIO(data)
        date_format = "%Y-%m-%d %H:%M" if period.is_intraday() else "%Y-%m-%d"

        # Handle quoted timestamps in CSV by specifying quote character
        # Allow configurable CSV parsing options
        skipfooter = getattr(self, "csv_skipfooter", 1)
        engine = getattr(self, "csv_engine", "python")
        quotechar = getattr(self, "csv_quotechar", '"')

        df = pd.read_csv(
            iostr, skipfooter=skipfooter, engine=engine, quotechar=quotechar
        )
        logging.debug(f"Received data {df.shape} from Barchart")
        logging.debug(f"CSV columns: {list(df.columns)}")

        # Basic column presence check - detailed validation will be handled by provider
        required_columns = [self.BARCHART_DATE_TIME_COLUMN, self.BARCHART_CLOSE_COLUMN]
        if not all(col in df.columns for col in required_columns):
            # Log for debugging but don't fail - standardized validation will handle this
            missing = [col for col in required_columns if col not in df.columns]
            logging.debug(
                f"Barchart parser: Raw CSV missing expected columns {missing}. Found columns: {list(df.columns)}"
            )
            # Continue processing - the standardized validation will provide proper error handling

        # Standardize columns using the centralized mapping system
        df = standardize_dataframe_columns(df, "barchart")

        # Parse and standardize datetime - should be mapped to DATETIME_INDEX_NAME by standardize_dataframe_columns
        if DATETIME_INDEX_NAME in df.columns:
            df[DATETIME_INDEX_NAME] = (
                pd.to_datetime(
                    df[DATETIME_INDEX_NAME], format=date_format, errors="coerce"
                )
                .dt.tz_localize(tz)
                .dt.tz_convert("UTC")
            )
            df.set_index(DATETIME_INDEX_NAME, inplace=True)
        else:
            # Fallback: try to find the datetime column that was mapped
            datetime_candidates = [
                col
                for col in df.columns
                if "time" in col.lower() or "date" in col.lower()
            ]
            if datetime_candidates:
                datetime_col = datetime_candidates[0]
                df[datetime_col] = (
                    pd.to_datetime(
                        df[datetime_col], format=date_format, errors="coerce"
                    )
                    .dt.tz_localize(tz)
                    .dt.tz_convert("UTC")
                )
                df.set_index(datetime_col, inplace=True)
                df.index.name = DATETIME_INDEX_NAME

        return df
