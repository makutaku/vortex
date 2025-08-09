"""
Financial instrument models and data structures.

This module contains the domain models for various financial instruments
including futures, stocks, forex pairs, and their associated data structures.
"""

from .instrument import Instrument
from .future import Future
from .stock import Stock
from .forex import Forex
from .price_series import PriceSeries
from .period import Period
from .metadata import Metadata
from .columns import (
    DATETIME_INDEX_NAME, DATE_TIME_COLUMN, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, 
    CLOSE_COLUMN, VOLUME_COLUMN, STANDARD_OHLCV_COLUMNS, REQUIRED_DATA_COLUMNS,
    validate_required_columns, get_provider_expected_columns,
    get_column_mapping, standardize_dataframe_columns, validate_column_data_types,
    # Legacy support
    REQUIRED_PRICE_COLUMNS
)
from .column_registry import (
    ProviderColumnMapping, ColumnMappingRegistry, register_provider_column_mapping
)

__all__ = [
    'Instrument',
    'Future',
    'Stock', 
    'Forex',
    'PriceSeries',
    'Period',
    'Metadata',
    'DATETIME_INDEX_NAME',
    'DATE_TIME_COLUMN',  # Legacy support
    'OPEN_COLUMN',
    'HIGH_COLUMN',
    'LOW_COLUMN',
    'CLOSE_COLUMN', 
    'VOLUME_COLUMN',
    'STANDARD_OHLCV_COLUMNS',
    'REQUIRED_DATA_COLUMNS',
    'REQUIRED_PRICE_COLUMNS',  # Legacy support
    'validate_required_columns',
    'get_provider_expected_columns',
    'get_column_mapping',
    'standardize_dataframe_columns',
    'validate_column_data_types',
    # New registry system
    'ProviderColumnMapping',
    'ColumnMappingRegistry',
    'register_provider_column_mapping',
]