"""
Example: Adding a new AlphaVantage provider with column mapping.

This demonstrates how easy it is to add a new provider without modifying
the central columns.py file - the new provider owns its column mapping.
"""

from typing import Dict, List
from vortex.models.column_registry import ProviderColumnMapping, register_provider_column_mapping
from vortex.models.columns import (
    DATETIME_INDEX_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN
)


class AlphaVantageColumnMapping(ProviderColumnMapping):
    """AlphaVantage provider-specific column mapping."""
    
    # AlphaVantage-specific column names
    ADJUSTED_CLOSE_COLUMN = "5. adjusted close"
    SPLIT_COEFFICIENT_COLUMN = "8. split coefficient"
    DIVIDEND_AMOUNT_COLUMN = "7. dividend amount"
    
    @property
    def provider_name(self) -> str:
        return "alphavantage"
    
    def get_provider_specific_columns(self) -> List[str]:
        """Get AlphaVantage-specific columns."""
        return [
            self.ADJUSTED_CLOSE_COLUMN,
            self.SPLIT_COEFFICIENT_COLUMN,
            self.DIVIDEND_AMOUNT_COLUMN
        ]
    
    def get_column_mapping(self, df_columns: List[str]) -> Dict[str, str]:
        """Get AlphaVantage-specific column mapping."""
        mapping = {}
        
        # AlphaVantage has a unique naming convention with numbers
        alphavantage_mappings = {
            # Date/time variations (these will become the index)
            'timestamp': DATETIME_INDEX_NAME,
            'date': DATETIME_INDEX_NAME,
            # AlphaVantage uses numbered column names
            '1. open': OPEN_COLUMN,
            '2. high': HIGH_COLUMN,
            '3. low': LOW_COLUMN,
            '4. close': CLOSE_COLUMN,
            '6. volume': VOLUME_COLUMN,
            # AlphaVantage specific columns preserved as-is
            '5. adjusted close': self.ADJUSTED_CLOSE_COLUMN,
            '7. dividend amount': self.DIVIDEND_AMOUNT_COLUMN,
            '8. split coefficient': self.SPLIT_COEFFICIENT_COLUMN,
        }
        
        # Create case-insensitive mapping for actual columns
        df_cols_lower = {col.lower().replace('_', '').replace(' ', '').replace('.', ''): col 
                        for col in df_columns}
        
        for av_col, standard_col in alphavantage_mappings.items():
            # Normalize AlphaVantage column name (lowercase, no spaces/underscores/dots)
            normalized_av = av_col.lower().replace('_', '').replace(' ', '').replace('.', '')
            
            # Find matching actual column
            if normalized_av in df_cols_lower:
                actual_col = df_cols_lower[normalized_av]
                mapping[actual_col] = standard_col
        
        return mapping


# Register the new provider - this is all that's needed!
# No need to modify any existing files in the core system
register_provider_column_mapping(AlphaVantageColumnMapping())

# Now the new provider works with all existing APIs:
if __name__ == "__main__":
    from vortex.models.column_registry import get_provider_expected_columns, get_column_mapping
    
    # Test the new provider
    required, optional = get_provider_expected_columns("alphavantage")
    print(f"Required columns: {required}")
    print(f"Optional columns: {optional}")
    
    # Test column mapping
    sample_columns = ["timestamp", "1. open", "2. high", "3. low", "4. close", "6. volume", "5. adjusted close"]
    mapping = get_column_mapping("alphavantage", sample_columns)
    print(f"Column mapping: {mapping}")
    
    # Output:
    # Required columns: ['Open', 'High', 'Low', 'Close', 'Volume']
    # Optional columns: ['5. adjusted close', '8. split coefficient', '7. dividend amount']  
    # Column mapping: {'timestamp': 'Datetime', '1. open': 'Open', '2. high': 'High', '3. low': 'Low', '4. close': 'Close', '6. volume': 'Volume', '5. adjusted close': '5. adjusted close'}