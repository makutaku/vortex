"""
Application constants and configuration values.

This module centralizes magic numbers and hardcoded values to improve
maintainability and make configuration easier.
"""

from typing import Dict, Any


class ProviderConstants:
    """Constants specific to data providers."""
    
    class Barchart:
        """Barchart.com provider constants."""
        
        # Daily download limits
        DEFAULT_DAILY_DOWNLOAD_LIMIT = 150
        PAID_USER_SERVER_LIMIT = 250
        FREE_USER_SERVER_LIMIT = 5
        
        # Request limits
        MAX_BARS_PER_DOWNLOAD = 20000
        MAX_RETRIES = 3
        REQUEST_TIMEOUT_SECONDS = 30
        
        # Data validation
        MIN_REQUIRED_DATA_POINTS = 4
        
        # URLs
        BASE_URL = 'https://www.barchart.com'
        DOWNLOAD_ENDPOINT = '/my/download'
        
        # Download request payload defaults
        DEFAULT_ORDER = 'asc'
        DEFAULT_DIVIDENDS = 'false'
        DEFAULT_BACKADJUST = 'false'
        DEFAULT_DBAR = 1
        DEFAULT_CUSTOMBAR = ''
        DEFAULT_VOLUME = 'true'
        DEFAULT_OPEN_INTEREST = 'true'
        DEFAULT_SPLITS = 'true'
        DEFAULT_USAGE_TYPE = 'quotes'
        
    class Yahoo:
        """Yahoo Finance provider constants."""
        
        # Request limits
        MAX_SYMBOLS_PER_REQUEST = 10
        MAX_BARS_PER_DOWNLOAD = 50000
        MAX_RETRIES = 3
        REQUEST_TIMEOUT_SECONDS = 15
        
        # Data validation
        MIN_REQUIRED_DATA_POINTS = 2
        
        # Time limits (Yahoo-specific restrictions)
        INTRADAY_30MIN_DAYS_LIMIT = 59
        INTRADAY_15MIN_DAYS_LIMIT = 59
        INTRADAY_5MIN_DAYS_LIMIT = 59
        INTRADAY_1MIN_DAYS_LIMIT = 7
        
    class IBKR:
        """Interactive Brokers provider constants."""
        
        # Connection settings
        DEFAULT_HOST = 'localhost'
        DEFAULT_PORT = 7497
        DEFAULT_CLIENT_ID = 1
        CONNECTION_TIMEOUT_SECONDS = 10
        HISTORICAL_DATA_TIMEOUT_SECONDS = 120
        
        # Request limits
        MAX_BARS_PER_DOWNLOAD = 10000
        MAX_RETRIES = 5
        
        # Data validation
        MIN_REQUIRED_DATA_POINTS = 1


class DataValidationConstants:
    """Constants for data validation and quality checks."""
    
    # Minimum data requirements
    MIN_TRADING_DAYS_FOR_ANALYSIS = 5
    MIN_DATA_POINTS_FOR_STATISTICS = 10
    
    # Data quality thresholds
    MAX_MISSING_DATA_PERCENTAGE = 0.05  # 5%
    MAX_ZERO_VOLUME_PERCENTAGE = 0.20   # 20%
    
    # Price validation
    MIN_VALID_PRICE = 0.01
    MAX_DAILY_PRICE_CHANGE_PERCENTAGE = 0.50  # 50%


class FileSystemConstants:
    """Constants for file system operations."""
    
    # Directory names
    DEFAULT_OUTPUT_DIR = './data'
    DEFAULT_CONFIG_DIR = './config'
    DEFAULT_LOG_DIR = './logs'
    
    # File extensions
    CSV_EXTENSION = '.csv'
    PARQUET_EXTENSION = '.parquet'
    JSON_EXTENSION = '.json'
    LOG_EXTENSION = '.log'
    
    # File permissions (octal)
    SECURE_FILE_PERMISSIONS = 0o600  # Read/write for owner only
    DEFAULT_FILE_PERMISSIONS = 0o644  # Read/write for owner, read for others
    DEFAULT_DIR_PERMISSIONS = 0o755   # Read/write/execute for owner, read/execute for others


class NetworkConstants:
    """Constants for network operations."""
    
    # HTTP settings
    DEFAULT_USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0'
    SIMPLE_USER_AGENT = 'Mozilla/5.0'
    DEFAULT_REQUEST_TIMEOUT = 30
    SHORT_REQUEST_TIMEOUT = 10
    LONG_REQUEST_TIMEOUT = 60
    LOGIN_REQUEST_TIMEOUT = 30
    MAX_REDIRECTS = 5
    
    # HTTP Status Codes
    HTTP_OK = 200
    HTTP_UNAUTHORIZED = 401
    HTTP_FORBIDDEN = 403
    HTTP_NOT_FOUND = 404
    HTTP_SERVER_ERROR = 500
    
    # Retry settings
    DEFAULT_MAX_RETRIES = 3
    RETRY_BACKOFF_FACTOR = 2.0
    MAX_RETRY_DELAY_SECONDS = 300  # 5 minutes


class LoggingConstants:
    """Constants for logging configuration."""
    
    # Log levels
    DEFAULT_LOG_LEVEL = 'INFO'
    
    # Log formats
    CONSOLE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    FILE_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    
    # Log rotation
    MAX_LOG_FILE_SIZE_MB = 10
    MAX_LOG_FILES = 5


class TimeConstants:
    """Constants for time-related operations."""
    
    # Datetime formats
    ISO_DATE_FORMAT = '%Y-%m-%d'
    ISO_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
    US_DATE_FORMAT = '%m/%d/%Y'
    
    # Time periods (in days)
    DEFAULT_LOOKBACK_DAYS = 365
    MAX_HISTORICAL_DATA_DAYS = 365 * 25  # 25 years
    MIN_INTRADAY_DATA_DAYS = 365 * 2     # 2 years
    
    # Rate limiting
    MIN_REQUEST_INTERVAL_SECONDS = 1.0
    RATE_LIMIT_WINDOW_SECONDS = 60




def get_provider_constants(provider_name: str) -> Dict[str, Any]:
    """
    Get constants for a specific provider.
    
    Args:
        provider_name: Name of the provider ('barchart', 'yahoo', 'ibkr')
        
    Returns:
        Dictionary of constants for the provider
    """
    provider_map = {
        'barchart': ProviderConstants.Barchart,
        'yahoo': ProviderConstants.Yahoo,
        'ibkr': ProviderConstants.IBKR
    }
    
    provider_class = provider_map.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    # Convert class attributes to dictionary
    return {
        key: value 
        for key, value in provider_class.__dict__.items() 
        if not key.startswith('_')
    }