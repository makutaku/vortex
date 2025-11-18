# Shared column constants to avoid circular imports
# This module contains only constants used by both columns.py and column_registry.py

# Index name (for DataFrames in memory - this is the pandas index name)
DATETIME_INDEX_NAME = "Datetime"

# Standard OHLCV column names (these are actual DataFrame columns)
OPEN_COLUMN = "Open"
HIGH_COLUMN = "High"
LOW_COLUMN = "Low"
CLOSE_COLUMN = "Close"
VOLUME_COLUMN = "Volume"

# Standard OHLCV column sets for validation (NO index name included)
STANDARD_OHLCV_COLUMNS = [
    OPEN_COLUMN,
    HIGH_COLUMN,
    LOW_COLUMN,
    CLOSE_COLUMN,
    VOLUME_COLUMN,
]
REQUIRED_DATA_COLUMNS = STANDARD_OHLCV_COLUMNS  # Only actual data columns, not index
