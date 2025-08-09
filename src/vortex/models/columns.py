# Internal Vortex standard column names
DATE_TIME_COLUMN = 'DATETIME'
OPEN_COLUMN = "Open"
HIGH_COLUMN = "High"
LOW_COLUMN = "Low"
CLOSE_COLUMN = "Close"
VOLUME_COLUMN = "Volume"

# Provider-specific column names
ADJ_CLOSE_COLUMN = "Adj Close"          # Yahoo Finance adjusted close
DIVIDENDS_COLUMN = "Dividends"          # Yahoo Finance dividends
STOCK_SPLITS_COLUMN = "Stock Splits"    # Yahoo Finance stock splits
OPEN_INTEREST_COLUMN = "Open Interest"  # Barchart/futures open interest
WAP_COLUMN = "wap"                      # IBKR weighted average price
COUNT_COLUMN = "count"                  # IBKR trade count

# Standard OHLCV sets for validation
STANDARD_OHLCV_COLUMNS = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
REQUIRED_PRICE_COLUMNS = [DATE_TIME_COLUMN] + STANDARD_OHLCV_COLUMNS

# Provider-specific column sets
YAHOO_SPECIFIC_COLUMNS = [ADJ_CLOSE_COLUMN, DIVIDENDS_COLUMN, STOCK_SPLITS_COLUMN]
BARCHART_SPECIFIC_COLUMNS = [OPEN_INTEREST_COLUMN]
IBKR_SPECIFIC_COLUMNS = [WAP_COLUMN, COUNT_COLUMN]

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
        df_cols_lower = [col.lower() for col in df_columns]
        required_lower = [col.lower() for col in required_columns]
        missing = [req for req_lower, req in zip(required_lower, required_columns) 
                  if req_lower not in df_cols_lower]
        found = [req for req_lower, req in zip(required_lower, required_columns) 
                if req_lower in df_cols_lower]
    else:
        missing = [col for col in required_columns if col not in df_columns]
        found = [col for col in required_columns if col in df_columns]
    
    return missing, found

def get_provider_expected_columns(provider_name):
    """
    Get expected columns for a specific provider.
    
    Args:
        provider_name: Name of the provider ('yahoo', 'barchart', 'ibkr')
    
    Returns:
        tuple: (required_columns, optional_columns)
    """
    base_required = REQUIRED_PRICE_COLUMNS
    
    if provider_name.lower() == 'yahoo':
        optional = YAHOO_SPECIFIC_COLUMNS
    elif provider_name.lower() == 'barchart':
        optional = BARCHART_SPECIFIC_COLUMNS
    elif provider_name.lower() == 'ibkr':
        optional = IBKR_SPECIFIC_COLUMNS
    else:
        optional = []
    
    return base_required, optional

def get_column_mapping(provider_name, df_columns):
    """
    Get a column mapping dictionary for standardizing provider-specific columns.
    
    Args:
        provider_name: Name of the provider ('yahoo', 'barchart', 'ibkr')
        df_columns: List of actual DataFrame column names
    
    Returns:
        dict: Mapping from actual column names to standard column names
    """
    mapping = {}
    provider_lower = provider_name.lower()
    
    # Define provider-specific mappings with variations
    provider_mappings = {
        'barchart': {
            # Date/time variations
            'time': DATE_TIME_COLUMN,
            'date': DATE_TIME_COLUMN,
            'datetime': DATE_TIME_COLUMN,
            # Price variations
            'last': CLOSE_COLUMN,
            'close': CLOSE_COLUMN,
            'open': OPEN_COLUMN,
            'high': HIGH_COLUMN,
            'low': LOW_COLUMN,
            # Volume variations
            'volume': VOLUME_COLUMN,
            'vol': VOLUME_COLUMN,
            # Other Barchart specific
            'open interest': OPEN_INTEREST_COLUMN,
            'openinterest': OPEN_INTEREST_COLUMN,
        },
        'yahoo': {
            # Date/time variations
            'date': DATE_TIME_COLUMN,
            'datetime': DATE_TIME_COLUMN,
            # Price variations (Yahoo uses capitalized names)
            'open': OPEN_COLUMN,
            'high': HIGH_COLUMN,
            'low': LOW_COLUMN,
            'close': CLOSE_COLUMN,
            # Volume
            'volume': VOLUME_COLUMN,
            # Yahoo specific
            'adj close': ADJ_CLOSE_COLUMN,
            'adjclose': ADJ_CLOSE_COLUMN,
            'dividends': DIVIDENDS_COLUMN,
            'stock splits': STOCK_SPLITS_COLUMN,
        },
        'ibkr': {
            # Date/time variations (IBKR uses lowercase)
            'date': DATE_TIME_COLUMN,
            'datetime': DATE_TIME_COLUMN,
            # Price variations (IBKR uses lowercase)
            'open': OPEN_COLUMN,
            'high': HIGH_COLUMN,
            'low': LOW_COLUMN,
            'close': CLOSE_COLUMN,
            # Volume
            'volume': VOLUME_COLUMN,
            # IBKR specific
            'wap': WAP_COLUMN,
            'count': COUNT_COLUMN,
        }
    }
    
    if provider_lower not in provider_mappings:
        return mapping
    
    provider_map = provider_mappings[provider_lower]
    
    # Create case-insensitive mapping for actual columns
    df_cols_lower = {col.lower().replace('_', '').replace(' ', ''): col for col in df_columns}
    
    for provider_col, standard_col in provider_map.items():
        # Normalize provider column name (lowercase, no spaces/underscores)
        normalized_provider = provider_col.lower().replace('_', '').replace(' ', '')
        
        # Find matching actual column
        if normalized_provider in df_cols_lower:
            actual_col = df_cols_lower[normalized_provider]
            mapping[actual_col] = standard_col
    
    return mapping

def standardize_dataframe_columns(df, provider_name):
    """
    Standardize DataFrame column names for a specific provider.
    
    Args:
        df: pandas DataFrame
        provider_name: Name of the provider ('yahoo', 'barchart', 'ibkr')
    
    Returns:
        pandas DataFrame: DataFrame with standardized column names
    """
    mapping = get_column_mapping(provider_name, df.columns)
    if mapping:
        df = df.rename(columns=mapping)
    return df
