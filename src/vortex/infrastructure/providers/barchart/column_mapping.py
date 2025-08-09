"""Barchart provider-specific column mapping."""

from typing import Dict, List
from vortex.models.column_registry import ProviderColumnMapping
from vortex.models.columns import (
    DATETIME_INDEX_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN
)


class BarchartColumnMapping(ProviderColumnMapping):
    """Barchart column mapping implementation."""
    
    # Barchart-specific column names
    OPEN_INTEREST_COLUMN = "Open Interest"
    
    @property
    def provider_name(self) -> str:
        return "barchart"
    
    def get_provider_specific_columns(self) -> List[str]:
        """Get Barchart-specific columns."""
        return [self.OPEN_INTEREST_COLUMN]
    
    def get_column_mapping(self, df_columns: List[str]) -> Dict[str, str]:
        """Get Barchart-specific column mapping."""
        mapping = {}
        
        # Define Barchart-specific mappings with variations
        barchart_mappings = {
            # Date/time variations (these will become the index)
            'time': DATETIME_INDEX_NAME,
            'date': DATETIME_INDEX_NAME,
            'datetime': DATETIME_INDEX_NAME,
            # Price variations
            'last': CLOSE_COLUMN,  # Barchart uses 'Last' for close price
            'close': CLOSE_COLUMN,
            'open': OPEN_COLUMN,
            'high': HIGH_COLUMN,
            'low': LOW_COLUMN,
            # Volume variations
            'volume': VOLUME_COLUMN,
            'vol': VOLUME_COLUMN,
            # Barchart specific
            'open interest': self.OPEN_INTEREST_COLUMN,
            'openinterest': self.OPEN_INTEREST_COLUMN,
        }
        
        # Create case-insensitive mapping for actual columns
        df_cols_lower = {col.lower().replace('_', '').replace(' ', ''): col for col in df_columns}
        
        for barchart_col, standard_col in barchart_mappings.items():
            # Normalize Barchart column name (lowercase, no spaces/underscores)
            normalized_barchart = barchart_col.lower().replace('_', '').replace(' ', '')
            
            # Find matching actual column
            if normalized_barchart in df_cols_lower:
                actual_col = df_cols_lower[normalized_barchart]
                mapping[actual_col] = standard_col
        
        return mapping