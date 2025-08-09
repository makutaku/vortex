# Internal Vortex standard index and column names

# Index name (for DataFrames in memory - this is the pandas index name)
DATETIME_INDEX_NAME = 'Datetime'

# Column name (for CSV files and raw data - this is a regular DataFrame column)  
DATETIME_COLUMN_NAME = 'Datetime'

# Standard OHLCV column names (these are actual DataFrame columns)
OPEN_COLUMN = "Open"
HIGH_COLUMN = "High"
LOW_COLUMN = "Low"
CLOSE_COLUMN = "Close"
VOLUME_COLUMN = "Volume"

# Standard OHLCV column sets for validation (NO index name included)
STANDARD_OHLCV_COLUMNS = [OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, CLOSE_COLUMN, VOLUME_COLUMN]
REQUIRED_DATA_COLUMNS = STANDARD_OHLCV_COLUMNS  # Only actual data columns, not index

# CSV file column sets (includes datetime column since it's stored as a column in CSV)
CSV_REQUIRED_COLUMNS = [DATETIME_COLUMN_NAME] + REQUIRED_DATA_COLUMNS

# Legacy support (for backward compatibility only)
DATE_TIME_COLUMN = DATETIME_COLUMN_NAME  # For backward compatibility only
REQUIRED_PRICE_COLUMNS = CSV_REQUIRED_COLUMNS  # For backward compatibility with CSV format

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
    return column_name.lower().replace('_', '').replace(' ', '')

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
    from .column_registry import get_provider_expected_columns as registry_get_columns
    return registry_get_columns(provider_name)

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
    from .column_registry import get_column_mapping as registry_get_mapping
    return registry_get_mapping(provider_name, df_columns)

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
                    # Log detailed conflict information for better visibility
                    logging.warning(f"Column mapping conflicts detected for provider '{provider_name}':")
                    for conflict in conflicts:
                        logging.warning(f"  - {conflict}")
                    
                    # Resolve conflicts by keeping the first mapping encountered
                    # and warn about which columns are being ignored
                    cleaned_mapping = {}
                    seen_targets = set()
                    ignored_mappings = []
                    
                    for source_col, target_col in mapping.items():
                        if target_col not in seen_targets:
                            cleaned_mapping[source_col] = target_col
                            seen_targets.add(target_col)
                        else:
                            ignored_mappings.append(f"'{source_col}' -> '{target_col}' (target already mapped)")
                    
                    if ignored_mappings:
                        logging.warning(f"Ignored conflicting mappings: {'; '.join(ignored_mappings)}")
                    
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
    
    # Check if index is datetime (be flexible about the name - it might be None for freshly loaded data)
    if pd.api.types.is_datetime64_any_dtype(df.index):
        # Index is datetime - good. Check if name needs to be set or is correct
        if df.index.name is not None and df.index.name != DATETIME_INDEX_NAME:
            issues.append(f"DataFrame datetime index name should be '{DATETIME_INDEX_NAME}', got '{df.index.name}'")
    else:
        issues.append(f"DataFrame index should be datetime64, got {df.index.dtype}")
    
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
