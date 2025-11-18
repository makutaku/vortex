"""
Financial instrument models and data structures.

This module contains the domain models for various financial instruments
including futures, stocks, forex pairs, and their associated data structures.
"""

from .column_constants import (
    CLOSE_COLUMN,
    DATETIME_INDEX_NAME,
    HIGH_COLUMN,
    LOW_COLUMN,
    OPEN_COLUMN,
    REQUIRED_DATA_COLUMNS,
    STANDARD_OHLCV_COLUMNS,
    VOLUME_COLUMN,
)
from .column_registry import (
    ColumnMappingRegistry,
    ProviderColumnMapping,
    register_provider_column_mapping,
)
from .columns import (
    get_column_mapping,
    get_provider_expected_columns,
    standardize_dataframe_columns,
    validate_column_data_types,
    validate_required_columns,
)
from .forex import Forex
from .future import Future
from .instrument import Instrument
from .metadata import Metadata
from .period import Period
from .price_series import PriceSeries
from .stock import Stock

__all__ = [
    "Instrument",
    "Future",
    "Stock",
    "Forex",
    "PriceSeries",
    "Period",
    "Metadata",
    "DATETIME_INDEX_NAME",
    "OPEN_COLUMN",
    "HIGH_COLUMN",
    "LOW_COLUMN",
    "CLOSE_COLUMN",
    "VOLUME_COLUMN",
    "STANDARD_OHLCV_COLUMNS",
    "REQUIRED_DATA_COLUMNS",
    "validate_required_columns",
    "get_provider_expected_columns",
    "get_column_mapping",
    "standardize_dataframe_columns",
    "validate_column_data_types",
    # New registry system
    "ProviderColumnMapping",
    "ColumnMappingRegistry",
    "register_provider_column_mapping",
]
