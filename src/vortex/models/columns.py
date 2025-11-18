# Internal Vortex standard index and column names

# Import shared constants to avoid circular imports
import logging
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .column_constants import (
    CLOSE_COLUMN,
    DATETIME_INDEX_NAME,
    HIGH_COLUMN,
    LOW_COLUMN,
    OPEN_COLUMN,
    REQUIRED_DATA_COLUMNS,
    VOLUME_COLUMN,
)
from .column_registry import (
    get_column_mapping as registry_get_column_mapping,
    get_provider_expected_columns as registry_get_provider_expected_columns,
)

# Column name (for CSV files and raw data - this is a regular DataFrame column)
DATETIME_COLUMN_NAME = "Datetime"

# CSV file column sets (includes datetime column since it's stored as a column in CSV)
CSV_REQUIRED_COLUMNS = [DATETIME_COLUMN_NAME] + REQUIRED_DATA_COLUMNS


# Structured error classes for column validation


class ValidationIssueType(Enum):
    """Types of column validation issues."""

    INDEX_TYPE_MISMATCH = "index_type_mismatch"
    INDEX_NAME_MISMATCH = "index_name_mismatch"
    COLUMN_TYPE_MISMATCH = "column_type_mismatch"
    NEGATIVE_VALUES = "negative_values"
    NAN_VALUES = "nan_values"
    OHLC_RELATIONSHIP_VIOLATION = "ohlc_relationship_violation"


@dataclass
class ValidationIssue:
    """Structured representation of a column validation issue."""

    type: ValidationIssueType
    column_name: Optional[str]
    message: str
    count: Optional[int] = None
    expected_type: Optional[str] = None
    actual_type: Optional[str] = None

    def __str__(self) -> str:
        return self.message


# Column normalization utilities
def normalize_column_name(column_name):
    """
    Normalize column name for case-insensitive matching.

    Converts to lowercase and removes spaces and underscores.

    Args:
        column_name: Column name to normalize

    Returns:
        str: Normalized column name
    """
    return column_name.lower().replace("_", "").replace(" ", "")


def create_normalized_column_mapping(df_columns):
    """
    Create a mapping from normalized column names to actual column names.

    Args:
        df_columns: List of actual DataFrame column names

    Returns:
        dict: Mapping from normalized names to actual column names
    """
    return {normalize_column_name(col): col for col in df_columns}


# Column validation utilities
def validate_required_columns(df_columns, required_columns, case_insensitive=True):
    """
    Validate that required columns exist in DataFrame columns.

    Args:
        df_columns: List of DataFrame column names
        required_columns: List of required column names
        case_insensitive: Whether to perform case-insensitive matching

    Returns:
        tuple: (missing_columns, found_columns)
    """
    if case_insensitive:
        # Use the standardized normalization logic
        df_cols_normalized = {normalize_column_name(col): col for col in df_columns}
        missing = []
        found = []

        for req_col in required_columns:
            normalized_req = normalize_column_name(req_col)
            if normalized_req in df_cols_normalized:
                found.append(req_col)
            else:
                missing.append(req_col)
    else:
        missing = [col for col in required_columns if col not in df_columns]
        found = [col for col in required_columns if col in df_columns]

    return missing, found


def get_provider_expected_columns(provider_name):
    """
    Get expected columns for a specific provider.

    Args:
        provider_name: Name of the provider

    Returns:
        tuple: (required_data_columns, optional_columns)

    Note: This returns ONLY DataFrame columns. The index name (Datetime) is handled separately.
    This function delegates to the column registry for provider-specific columns.
    """
    return registry_get_provider_expected_columns(provider_name)


def get_column_mapping(provider_name, df_columns):
    """
    Get a column mapping dictionary for standardizing provider-specific columns.

    Args:
        provider_name: Name of the provider
        df_columns: List of actual DataFrame column names

    Returns:
        dict: Mapping from actual column names to standard column names

    Note: This function delegates to the column registry for provider-specific mappings.
    """

    return registry_get_column_mapping(provider_name, df_columns)


class ColumnStandardizer:
    """Handles column standardization for different providers."""

    def __init__(self, provider_name: str, strict: bool = False):
        self.provider_name = provider_name
        self.strict = strict

        self.logger = logging.getLogger(__name__)

    def standardize(self, df):
        """Standardize DataFrame column names."""
        try:
            mapping = get_column_mapping(self.provider_name, df.columns)
            if not mapping:
                return df

            validated_mapping = self._validate_mapping(mapping)
            return self._apply_mapping(df, validated_mapping)

        except Exception as e:
            return self._handle_error(e, df)

    def _validate_mapping(self, mapping: dict) -> dict:
        """Validate column mapping for conflicts."""
        conflicts = self._detect_conflicts(mapping)

        if not conflicts:
            return mapping

        if self.strict:
            error_msg = f"Column mapping conflicts for provider '{self.provider_name}': {'; '.join(conflicts)}"
            raise ValueError(error_msg)

        return self._resolve_conflicts(mapping, conflicts)

    def _detect_conflicts(self, mapping: dict) -> list:
        """Detect mapping conflicts where multiple sources map to same target."""
        reverse_mapping = {}
        conflicts = []

        for source_col, target_col in mapping.items():
            if target_col in reverse_mapping:
                conflicts.append(
                    f"Multiple columns map to '{target_col}': {reverse_mapping[target_col]} and {source_col}"
                )
            else:
                reverse_mapping[target_col] = source_col

        return conflicts

    def _resolve_conflicts(self, mapping: dict, conflicts: list) -> dict:
        """Resolve mapping conflicts by keeping first occurrence."""
        self._log_conflicts(conflicts)

        cleaned_mapping = {}
        seen_targets = set()
        ignored_mappings = []

        for source_col, target_col in mapping.items():
            if target_col not in seen_targets:
                cleaned_mapping[source_col] = target_col
                seen_targets.add(target_col)
            else:
                ignored_mappings.append(
                    f"'{source_col}' -> '{target_col}' (target already mapped)"
                )

        if ignored_mappings:
            self.logger.warning(
                f"Ignored conflicting mappings: {'; '.join(ignored_mappings)}"
            )

        return cleaned_mapping

    def _log_conflicts(self, conflicts: list):
        """Log detailed conflict information."""
        self.logger.warning(
            f"Column mapping conflicts detected for provider '{self.provider_name}':"
        )
        for conflict in conflicts:
            self.logger.warning(f"  - {conflict}")

    def _apply_mapping(self, df, mapping: dict):
        """Apply validated mapping to DataFrame."""
        df = df.rename(columns=mapping)
        self.logger.debug(
            f"Column mapping for {self.provider_name}: {len(mapping)} columns renamed"
        )
        return df

    def _handle_error(self, error: Exception, df):
        """Handle errors during standardization."""
        error_msg = f"Error in column standardization for provider '{self.provider_name}': {error}"
        if self.strict:
            raise ValueError(error_msg) from error
        else:
            self.logger.error(error_msg)
            return df


def standardize_dataframe_columns(df, provider_name, strict=False):
    """
    Standardize DataFrame column names for a specific provider.

    Args:
        df: pandas DataFrame
        provider_name: Name of the provider ('yahoo', 'barchart', 'ibkr')
        strict: If True, raise exception on mapping conflicts. If False, log warnings.

    Returns:
        pandas DataFrame: DataFrame with standardized column names

    Raises:
        ValueError: If strict=True and column mapping conflicts are detected
    """
    standardizer = ColumnStandardizer(provider_name, strict)
    return standardizer.standardize(df)


class DataTypeValidator:
    """Handles data type validation for DataFrame columns."""

    def __init__(self, df, strict: bool = False):
        self.df = df
        self.strict = strict
        self.issues = []

        self.pd = pd

    def validate(self) -> tuple:
        """Perform complete data type validation."""
        self._validate_index_type()
        self._validate_price_columns()
        self._validate_volume_column()
        self._validate_nan_values()
        self._validate_ohlc_relationships()

        is_valid = len(self.issues) == 0

        if self.strict and not is_valid:
            error_messages = [str(issue) for issue in self.issues]
            raise ValueError(
                f"Column data type validation failed: {'; '.join(error_messages)}"
            )

        return is_valid, self.issues

    def _validate_index_type(self):
        """Validate that index is datetime with correct name."""
        if self.pd.api.types.is_datetime64_any_dtype(self.df.index):
            self._check_index_name()
        else:
            self._add_issue(
                ValidationIssueType.INDEX_TYPE_MISMATCH,
                None,
                f"DataFrame index should be datetime64, got {self.df.index.dtype}",
                expected_type="datetime64",
                actual_type=str(self.df.index.dtype),
            )

    def _check_index_name(self):
        """Check if datetime index has correct name."""
        if self.df.index.name is not None and self.df.index.name != DATETIME_INDEX_NAME:
            self._add_issue(
                ValidationIssueType.INDEX_NAME_MISMATCH,
                None,
                f"DataFrame datetime index name should be '{DATETIME_INDEX_NAME}', got '{self.df.index.name}'",
                expected_type=DATETIME_INDEX_NAME,
                actual_type=str(self.df.index.name),
            )

    def _validate_price_columns(self):
        """Validate price columns are numeric and non-negative."""
        price_columns = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]
        for col in price_columns:
            if col in self.df.columns:
                self._validate_column_numeric(col, "Price")
                if self.pd.api.types.is_numeric_dtype(self.df[col]):
                    self._validate_column_non_negative(col, "Price")

    def _validate_volume_column(self):
        """Validate volume column is numeric and non-negative."""
        if VOLUME_COLUMN in self.df.columns:
            self._validate_column_numeric(VOLUME_COLUMN, "Volume")
            if self.pd.api.types.is_numeric_dtype(self.df[VOLUME_COLUMN]):
                self._validate_column_non_negative(VOLUME_COLUMN, "Volume")

    def _validate_column_numeric(self, column: str, column_type: str):
        """Validate that a column is numeric."""
        if not self.pd.api.types.is_numeric_dtype(self.df[column]):
            self._add_issue(
                ValidationIssueType.COLUMN_TYPE_MISMATCH,
                column,
                f"{column_type} column '{column}' should be numeric, got {self.df[column].dtype}",
                expected_type="numeric",
                actual_type=str(self.df[column].dtype),
            )

    def _validate_column_non_negative(self, column: str, column_type: str):
        """Validate that a column has no negative values."""
        if (self.df[column] < 0).any():
            neg_count = (self.df[column] < 0).sum()
            self._add_issue(
                ValidationIssueType.NEGATIVE_VALUES,
                column,
                f"{column_type} column '{column}' contains {neg_count} negative values",
                count=neg_count,
            )

    def _validate_nan_values(self):
        """Validate critical columns don't contain NaN values."""
        critical_columns = [
            col
            for col in [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]
            if col in self.df.columns
        ]

        for col in critical_columns:
            nan_count = self.df[col].isna().sum()
            if nan_count > 0:
                self._add_issue(
                    ValidationIssueType.NAN_VALUES,
                    col,
                    f"Critical column '{col}' contains {nan_count} NaN values",
                    count=nan_count,
                )

    def _validate_ohlc_relationships(self):
        """Validate OHLC price relationships."""
        ohlc_cols = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]

        if not self._all_ohlc_columns_present_and_numeric(ohlc_cols):
            return

        self._validate_high_column_relationships()
        self._validate_low_column_relationships()

    def _all_ohlc_columns_present_and_numeric(self, ohlc_cols: list) -> bool:
        """Check if all OHLC columns are present and numeric."""
        return all(col in self.df.columns for col in ohlc_cols) and all(
            self.pd.api.types.is_numeric_dtype(self.df[col]) for col in ohlc_cols
        )

    def _validate_high_column_relationships(self):
        """Validate High column relationships."""
        invalid_high = (
            (self.df[HIGH_COLUMN] < self.df[LOW_COLUMN])
            | (self.df[HIGH_COLUMN] < self.df[OPEN_COLUMN])
            | (self.df[HIGH_COLUMN] < self.df[CLOSE_COLUMN])
        ).sum()

        if invalid_high > 0:
            self._add_issue(
                ValidationIssueType.OHLC_RELATIONSHIP_VIOLATION,
                HIGH_COLUMN,
                f"Found {invalid_high} rows where High < (Low, Open, or Close)",
                count=invalid_high,
            )

    def _validate_low_column_relationships(self):
        """Validate Low column relationships."""
        invalid_low = (
            (self.df[LOW_COLUMN] > self.df[HIGH_COLUMN])
            | (self.df[LOW_COLUMN] > self.df[OPEN_COLUMN])
            | (self.df[LOW_COLUMN] > self.df[CLOSE_COLUMN])
        ).sum()

        if invalid_low > 0:
            self._add_issue(
                ValidationIssueType.OHLC_RELATIONSHIP_VIOLATION,
                LOW_COLUMN,
                f"Found {invalid_low} rows where Low > (High, Open, or Close)",
                count=invalid_low,
            )

    def _add_issue(
        self,
        issue_type: ValidationIssueType,
        column_name: str,
        message: str,
        count: Optional[int] = None,
        expected_type: Optional[str] = None,
        actual_type: Optional[str] = None,
    ) -> None:
        """Add a validation issue to the issues list."""
        self.issues.append(
            ValidationIssue(
                type=issue_type,
                column_name=column_name,
                message=message,
                count=count,
                expected_type=expected_type,
                actual_type=actual_type,
            )
        )


def validate_column_data_types(df, strict=False):
    """
    Validate that DataFrame columns have expected data types.

    Args:
        df: pandas DataFrame to validate
        strict: If True, raise exceptions on validation errors. If False, return warnings.

    Returns:
        tuple: (is_valid: bool, issues: List[ValidationIssue])
    """
    validator = DataTypeValidator(df, strict)
    return validator.validate()
