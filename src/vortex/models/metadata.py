"""
Metadata model for price series data.

This module contains the core Metadata dataclass that represents
metadata information for price series data. It belongs in the domain
models layer as it's a core business entity.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import pandas as pd

from .columns import VOLUME_COLUMN
from .period import Period


@dataclass
class Metadata:
    """Metadata for price series data."""

    symbol: str
    period: Period
    start_date: datetime
    end_date: datetime
    first_row_date: datetime
    last_row_date: datetime
    data_provider: str = None
    expiration_date: datetime = None
    created_date: datetime = datetime.utcnow()

    def __str__(self):
        return (
            f"{self.symbol}, {self.period.value}, "
            f"{self.start_date.strftime('%Y-%m-%d')}, {self.end_date.strftime('%Y-%m-%d')}"
        )

    @staticmethod
    def create_metadata(df, provider_name, symbol, period: Period, start, end):
        """Create metadata from DataFrame and parameters."""
        df = df.sort_index()

        # Validate that we have valid datetime indices before creating metadata
        if df.empty or df.index.isna().all():
            raise ValueError(
                f"Cannot create metadata for {symbol}: DataFrame has no valid datetime indices"
            )

        first_row_date = df.index[0].to_pydatetime()
        last_row_date = df.index[-1].to_pydatetime()

        # Additional check for NaT values after conversion
        if pd.isna(first_row_date) or pd.isna(last_row_date):
            raise ValueError(
                f"Cannot create metadata for {symbol}: DataFrame index contains invalid datetime values"
            )
        expiration_date = None
        if df[VOLUME_COLUMN].iloc[-1] == 0:
            logging.debug(
                "Detected possible contract expiration: last bar has volume 0. Adjusting expected end date."
            )
            expiration_date = last_row_date
        metadata = Metadata(
            symbol,
            period,
            start,
            end,
            first_row_date,
            last_row_date,
            data_provider=provider_name,
            expiration_date=expiration_date,
        )
        return metadata


def default_serializer(obj):
    """Default serializer for JSON serialization of metadata objects."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, (str, int, float)):
        return obj  # Serialize strings, ints, and floats as-is
    elif isinstance(obj, Enum):
        return obj.value
    raise TypeError("Type not serializable")
