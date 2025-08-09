"""Yahoo Finance provider-specific column mapping."""

from typing import Dict, List
from vortex.models.column_registry import ProviderColumnMapping
from vortex.models.columns import (
    DATETIME_INDEX_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN
)


class YahooColumnMapping(ProviderColumnMapping):
    """Yahoo Finance column mapping implementation."""
    
    # Yahoo-specific column names
    ADJ_CLOSE_COLUMN = "Adj Close"
    DIVIDENDS_COLUMN = "Dividends"
    STOCK_SPLITS_COLUMN = "Stock Splits"
    
    @property
    def provider_name(self) -> str:
        return "yahoo"
    
    def get_provider_specific_columns(self) -> List[str]:
        """Get Yahoo-specific columns."""
        return [self.ADJ_CLOSE_COLUMN, self.DIVIDENDS_COLUMN, self.STOCK_SPLITS_COLUMN]
    
    def get_column_mapping(self, df_columns: List[str]) -> Dict[str, str]:
        """Get Yahoo-specific column mapping."""
        mapping = {}
        
        # Define Yahoo-specific mappings with variations
        yahoo_mappings = {
            # Date/time variations (these will become the index)
            'date': DATETIME_INDEX_NAME,
            'datetime': DATETIME_INDEX_NAME,
            # Price variations (Yahoo uses capitalized names)
            'open': OPEN_COLUMN,
            'high': HIGH_COLUMN,
            'low': LOW_COLUMN,
            'close': CLOSE_COLUMN,
            # Volume
            'volume': VOLUME_COLUMN,
            # Yahoo specific
            'adj close': self.ADJ_CLOSE_COLUMN,
            'adjclose': self.ADJ_CLOSE_COLUMN,
            'dividends': self.DIVIDENDS_COLUMN,
            'stock splits': self.STOCK_SPLITS_COLUMN,
        }
        
        # Create case-insensitive mapping for actual columns
        df_cols_lower = {col.lower().replace('_', '').replace(' ', ''): col for col in df_columns}
        
        for yahoo_col, standard_col in yahoo_mappings.items():
            # Normalize Yahoo column name (lowercase, no spaces/underscores)
            normalized_yahoo = yahoo_col.lower().replace('_', '').replace(' ', '')
            
            # Find matching actual column
            if normalized_yahoo in df_cols_lower:
                actual_col = df_cols_lower[normalized_yahoo]
                mapping[actual_col] = standard_col
        
        return mapping