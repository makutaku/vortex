"""IBKR provider-specific column mapping."""

from typing import Dict, List
from vortex.models.column_registry import ProviderColumnMapping
from vortex.models.columns import (
    DATETIME_INDEX_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN
)


class IbkrColumnMapping(ProviderColumnMapping):
    """IBKR column mapping implementation."""
    
    # IBKR-specific column names
    WAP_COLUMN = "wap"           # Weighted Average Price
    COUNT_COLUMN = "count"       # Trade count
    
    @property
    def provider_name(self) -> str:
        return "ibkr"
    
    def get_provider_specific_columns(self) -> List[str]:
        """Get IBKR-specific columns."""
        return [self.WAP_COLUMN, self.COUNT_COLUMN]
    
    def get_column_mapping(self, df_columns: List[str]) -> Dict[str, str]:
        """Get IBKR-specific column mapping."""
        mapping = {}
        
        # Define IBKR-specific mappings with variations
        ibkr_mappings = {
            # Date/time variations (IBKR uses lowercase - these will become the index)
            'date': DATETIME_INDEX_NAME,
            'datetime': DATETIME_INDEX_NAME,
            # Price variations (IBKR uses lowercase)
            'open': OPEN_COLUMN,
            'high': HIGH_COLUMN,
            'low': LOW_COLUMN,
            'close': CLOSE_COLUMN,
            # Volume
            'volume': VOLUME_COLUMN,
            # IBKR specific
            'wap': self.WAP_COLUMN,
            'count': self.COUNT_COLUMN,
        }
        
        # Create case-insensitive mapping for actual columns
        df_cols_lower = {col.lower().replace('_', '').replace(' ', ''): col for col in df_columns}
        
        for ibkr_col, standard_col in ibkr_mappings.items():
            # Normalize IBKR column name (lowercase, no spaces/underscores)
            normalized_ibkr = ibkr_col.lower().replace('_', '').replace(' ', '')
            
            # Find matching actual column
            if normalized_ibkr in df_cols_lower:
                actual_col = df_cols_lower[normalized_ibkr]
                mapping[actual_col] = standard_col
        
        return mapping