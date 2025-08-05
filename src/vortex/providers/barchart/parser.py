"""
Barchart data parsing and conversion utilities.

Handles CSV parsing, DataFrame conversion, and data formatting for Barchart data.
"""

import io
import logging

import pandas as pd

from vortex.models.columns import CLOSE_COLUMN, DATE_TIME_COLUMN
from vortex.models.period import Period


class BarchartParser:
    """Handles parsing and conversion of Barchart data."""
    
    BARCHART_DATE_TIME_COLUMN = 'Time'
    BARCHART_CLOSE_COLUMN = "Last"
    
    @classmethod
    def convert_downloaded_csv_to_df(cls, period: Period, data: str, tz: str) -> pd.DataFrame:
        """Convert downloaded CSV data to a standardized DataFrame."""
        iostr = io.StringIO(data)
        date_format = '%m/%d/%Y %H:%M' if period.is_intraday() else '%Y-%m-%d'
        df = pd.read_csv(iostr, skipfooter=1, engine='python')
        logging.debug(f"Received data {df.shape} from Barchart")

        # Rename columns to standard format
        columns = {
            cls.BARCHART_DATE_TIME_COLUMN: DATE_TIME_COLUMN,
            cls.BARCHART_CLOSE_COLUMN: CLOSE_COLUMN,
        }
        df = df.rename(columns=columns)
        
        # Parse and standardize datetime
        df[DATE_TIME_COLUMN] = (pd.to_datetime(df[DATE_TIME_COLUMN], format=date_format, errors='coerce')
                                .dt.tz_localize(tz).dt.tz_convert('UTC'))
        df.set_index(DATE_TIME_COLUMN, inplace=True)
        
        return df