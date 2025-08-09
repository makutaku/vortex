# Internal Vortex standard column names
DATE_TIME_COLUMN = 'Datetime'
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
    import logging
    
    try:
        mapping = get_column_mapping(provider_name, df.columns)
        if mapping:
            # Check for potential conflicts (multiple source columns mapping to same target)
            reverse_mapping = {}
            conflicts = []
            
            for source_col, target_col in mapping.items():
                if target_col in reverse_mapping:
                    conflicts.append(f"Multiple columns map to '{target_col}': {reverse_mapping[target_col]} and {source_col}")
                else:
                    reverse_mapping[target_col] = source_col
            
            if conflicts:
                error_msg = f"Column mapping conflicts for provider '{provider_name}': {'; '.join(conflicts)}"
                if strict:
                    raise ValueError(error_msg)
                else:
                    logging.warning(error_msg)
                    # Use only the first mapping for each target column
                    cleaned_mapping = {}
                    seen_targets = set()
                    for source_col, target_col in mapping.items():
                        if target_col not in seen_targets:
                            cleaned_mapping[source_col] = target_col
                            seen_targets.add(target_col)
                    mapping = cleaned_mapping
            
            # Check for missing columns after mapping
            original_cols = set(df.columns)
            df = df.rename(columns=mapping)
            mapped_cols = set(mapping.values())
            
            logging.debug(f"Column mapping for {provider_name}: {len(mapping)} columns renamed")
            
        return df
        
    except Exception as e:
        error_msg = f"Error in column standardization for provider '{provider_name}': {e}"
        if strict:
            raise ValueError(error_msg) from e
        else:
            logging.error(error_msg)
            return df  # Return original DataFrame on error

def validate_column_data_types(df, strict=False):
    """
    Validate that DataFrame columns have expected data types.
    
    Args:
        df: pandas DataFrame to validate
        strict: If True, raise exceptions on validation errors. If False, return warnings.
    
    Returns:
        tuple: (is_valid: bool, issues: list of str)
    """
    import pandas as pd
    import numpy as np
    
    issues = []
    
    # Check if index is datetime (for DATETIME column)
    if hasattr(df.index, 'name') and df.index.name == DATE_TIME_COLUMN:
        if not pd.api.types.is_datetime64_any_dtype(df.index):
            issues.append(f"Index column '{DATE_TIME_COLUMN}' should be datetime64, got {df.index.dtype}")
    
    # Check price columns should be numeric
    price_columns = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]
    for col in price_columns:
        if col in df.columns:
            if not pd.api.types.is_numeric_dtype(df[col]):
                issues.append(f"Price column '{col}' should be numeric, got {df[col].dtype}")
            else:
                # Check for negative prices (usually invalid)
                if (df[col] < 0).any():
                    neg_count = (df[col] < 0).sum()
                    issues.append(f"Price column '{col}' contains {neg_count} negative values")
    
    # Check volume column should be numeric and non-negative
    if VOLUME_COLUMN in df.columns:
        if not pd.api.types.is_numeric_dtype(df[VOLUME_COLUMN]):
            issues.append(f"Volume column '{VOLUME_COLUMN}' should be numeric, got {df[VOLUME_COLUMN].dtype}")
        else:
            # Check for negative volumes
            if (df[VOLUME_COLUMN] < 0).any():
                neg_count = (df[VOLUME_COLUMN] < 0).sum()
                issues.append(f"Volume column '{VOLUME_COLUMN}' contains {neg_count} negative values")
    
    # Check for NaN values in critical columns
    critical_columns = [col for col in [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN] if col in df.columns]
    for col in critical_columns:
        nan_count = df[col].isna().sum()
        if nan_count > 0:
            issues.append(f"Critical column '{col}' contains {nan_count} NaN values")
    
    # Validate OHLC relationships if all OHLC columns are present AND all are numeric
    ohlc_cols = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN]
    if (all(col in df.columns for col in ohlc_cols) and 
        all(pd.api.types.is_numeric_dtype(df[col]) for col in ohlc_cols)):
        # High should be >= Low, Open, Close
        invalid_high = ((df[HIGH_COLUMN] < df[LOW_COLUMN]) | 
                       (df[HIGH_COLUMN] < df[OPEN_COLUMN]) | 
                       (df[HIGH_COLUMN] < df[CLOSE_COLUMN])).sum()
        if invalid_high > 0:
            issues.append(f"Found {invalid_high} rows where High < (Low, Open, or Close)")
        
        # Low should be <= High, Open, Close  
        invalid_low = ((df[LOW_COLUMN] > df[HIGH_COLUMN]) | 
                      (df[LOW_COLUMN] > df[OPEN_COLUMN]) | 
                      (df[LOW_COLUMN] > df[CLOSE_COLUMN])).sum()
        if invalid_low > 0:
            issues.append(f"Found {invalid_low} rows where Low > (High, Open, or Close)")
    
    is_valid = len(issues) == 0
    
    if strict and not is_valid:
        raise ValueError(f"Column data type validation failed: {'; '.join(issues)}")
    
    return is_valid, issues
