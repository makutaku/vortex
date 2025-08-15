"""Provider-specific validation formats."""

import logging
from pathlib import Path
from typing import Dict
from vortex.core.error_handling import return_none_on_error

# Import provider-specific constants from their respective providers
from vortex.infrastructure.providers.yahoo.column_mapping import YahooColumnMapping
from vortex.infrastructure.providers.barchart.column_mapping import BarchartColumnMapping  
from vortex.infrastructure.providers.ibkr.column_mapping import IbkrColumnMapping

from vortex.models.columns import (
    OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN
)

# Create instances to access provider-specific constants
_yahoo_mapping = YahooColumnMapping()
_barchart_mapping = BarchartColumnMapping()
_ibkr_mapping = IbkrColumnMapping()

# Extract constants for use in validation
ADJ_CLOSE_COLUMN = _yahoo_mapping.ADJ_CLOSE_COLUMN
WAP_COLUMN = _ibkr_mapping.WAP_COLUMN
COUNT_COLUMN = _ibkr_mapping.COUNT_COLUMN

logger = logging.getLogger(__name__)


class ProviderFormatValidator:
    """Strategy pattern for provider-specific format validation."""
    
    def __init__(self):
        self.validators = {
            "barchart": BarchartFormatValidator(),
            "yahoo": YahooFormatValidator(),
            "ibkr": IbkrFormatValidator()
        }
    
    def validate(self, path: Path, provider: str) -> dict:
        """Validate provider-specific format requirements."""
        result = {"errors": [], "warnings": []}
        
        try:
            df = self._load_dataframe(path, result)
            if df is None:
                return result
            
            validator = self.validators.get(provider)
            if validator:
                validator.validate_format(df, result)
            else:
                result["warnings"].append(f"Unknown provider '{provider}' - skipping provider-specific validation")
                
        except Exception as e:
            result["errors"].append(f"Provider format validation error: {e}")
        
        return result
    
    @return_none_on_error("load_dataframe", "ValidationCommand") 
    def _load_dataframe(self, path: Path, result: dict):
        """Load DataFrame from file."""
        import pandas as pd
        
        if path.suffix.lower() == '.csv':
            return pd.read_csv(path)
        elif path.suffix.lower() == '.parquet':
            return pd.read_parquet(path)
        else:
            result["errors"].append(f"Unsupported file format for provider validation: {path.suffix}")
            raise Exception(f"Unsupported file format for provider validation: {path.suffix}")


class BaseFormatValidator:
    """Base class for provider format validators."""
    
    def validate_format(self, df, result: dict):
        """Validate format for specific provider."""
        raise NotImplementedError
    
    def _normalize_columns(self, df, replacement: str = '') -> list:
        """Normalize column names for comparison."""
        return [col.lower().replace(' ', replacement) for col in df.columns]
    
    def _check_required_columns(self, df_columns: list, required_columns: list, 
                              column_constants: list, provider_name: str, result: dict):
        """Check for required columns and add warnings for missing ones."""
        for col_const, col_lower in zip(column_constants, required_columns):
            if col_lower not in df_columns:
                result["warnings"].append(f"{provider_name} format missing '{col_const}' column")
    
    def _check_date_columns(self, df_columns: list, date_variants: list, 
                          provider_name: str, result: dict):
        """Check for date/time columns."""
        has_date = any(col in df_columns for col in date_variants)
        if not has_date:
            result["warnings"].append(f"{provider_name} format missing date/time column")


class BarchartFormatValidator(BaseFormatValidator):
    """Validator for Barchart format."""
    
    def validate_format(self, df, result: dict):
        """Validate Barchart-specific format requirements."""
        df_columns_lower = self._normalize_columns(df, '')
        
        # Check date/time columns
        self._check_date_columns(
            df_columns_lower, 
            ['date', 'time', 'datetime'], 
            "Barchart", 
            result
        )
        
        # Check OHLCV columns
        self._check_ohlcv_columns(df_columns_lower, result)
        
        # Check close/last column (Barchart uses 'Last')
        self._check_close_column(df_columns_lower, result)
    
    def _check_ohlcv_columns(self, df_columns: list, result: dict):
        """Check OHLCV columns for Barchart."""
        required_constants = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, VOLUME_COLUMN]
        required_columns = [col.lower() for col in required_constants]
        self._check_required_columns(df_columns, required_columns, required_constants, "Barchart", result)
    
    def _check_close_column(self, df_columns: list, result: dict):
        """Check for close/last price column."""
        has_close = any(col in df_columns for col in [CLOSE_COLUMN.lower(), 'last'])
        if not has_close:
            result["warnings"].append("Barchart format missing close/last price column")


class YahooFormatValidator(BaseFormatValidator):
    """Validator for Yahoo Finance format."""
    
    def validate_format(self, df, result: dict):
        """Validate Yahoo Finance-specific format requirements."""
        df_columns_lower = self._normalize_columns(df, '_')
        
        # Check date columns
        self._check_date_columns(
            df_columns_lower, 
            ['date', 'datetime'], 
            "Yahoo", 
            result
        )
        
        # Check OHLCV columns
        self._check_standard_ohlcv_columns(df_columns_lower, result, "Yahoo")
        
        # Check Yahoo-specific columns
        self._check_adj_close_column(df_columns_lower, result)
    
    def _check_standard_ohlcv_columns(self, df_columns: list, result: dict, provider: str):
        """Check standard OHLCV columns."""
        required_constants = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        required_columns = [col.lower() for col in required_constants]
        self._check_required_columns(df_columns, required_columns, required_constants, provider, result)
    
    def _check_adj_close_column(self, df_columns: list, result: dict):
        """Check for Yahoo's Adj Close column."""
        has_adj_close = any(col in df_columns for col in ['adj_close', 'adjclose'])
        if not has_adj_close:
            result["warnings"].append(f"Yahoo format typically includes '{ADJ_CLOSE_COLUMN}' column")


class IbkrFormatValidator(BaseFormatValidator):
    """Validator for IBKR format."""
    
    def validate_format(self, df, result: dict):
        """Validate IBKR-specific format requirements."""
        df_columns_lower = self._normalize_columns(df, '')
        
        # Check date columns
        self._check_date_columns(
            df_columns_lower, 
            ['date', 'datetime'], 
            "IBKR", 
            result
        )
        
        # Check OHLCV columns
        self._check_standard_ohlcv_columns(df_columns_lower, result, "IBKR")
        
        # Check IBKR-specific columns
        self._check_ibkr_specific_columns(df_columns_lower, result)
    
    def _check_standard_ohlcv_columns(self, df_columns: list, result: dict, provider: str):
        """Check standard OHLCV columns."""
        required_constants = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
        required_columns = [col.lower() for col in required_constants]
        self._check_required_columns(df_columns, required_columns, required_constants, provider, result)
    
    def _check_ibkr_specific_columns(self, df_columns: list, result: dict):
        """Check IBKR-specific columns."""
        if WAP_COLUMN.lower() not in df_columns:
            result["warnings"].append(f"IBKR format typically includes '{WAP_COLUMN}' (Weighted Average Price) column")
        if COUNT_COLUMN.lower() not in df_columns:
            result["warnings"].append(f"IBKR format typically includes '{COUNT_COLUMN}' (trade count) column")