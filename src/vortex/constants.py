from typing import Any, Dict

"""
Application-wide constants for Vortex.

This module contains magic numbers and configuration constants that are used
throughout the application to improve maintainability and reduce duplication.
"""

# File size constants (bytes)
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024
BYTES_PER_GB = 1024 * 1024 * 1024

# Network and connection constants
DEFAULT_IBKR_PORT = 7497
MAX_PORT_NUMBER = 65535
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_CONNECTION_TIMEOUT = 10
DEFAULT_READ_TIMEOUT = 30

# Data processing constants
DEFAULT_DAILY_LIMIT = 150
MIN_DATA_POINTS_FOR_ANALYSIS = 150
MAX_COMPLETION_SUGGESTIONS = 20
MAX_RECENT_FILES_TO_CHECK = 20

# Provider-specific constants
# Barchart limits and configurations
BARCHART_MAX_HISTORICAL_YEARS_DAILY = 25
BARCHART_MAX_HISTORICAL_YEARS_INTRADAY = 2
BARCHART_MAX_BARS_PER_DOWNLOAD = 20000

# IBKR timeout and connection constants
IBKR_HISTORICAL_DATA_TIMEOUT_SECONDS = 120
IBKR_DEFAULT_CLIENT_ID = 998
IBKR_CONNECTION_TIMEOUT_SECONDS = 20
IBKR_CONNECTION_SLEEP_SECONDS = 10
IBKR_DEFAULT_CONTRACT_MULTIPLIER = 37500

# Configuration validation limits
MAX_DAILY_DOWNLOAD_LIMIT = 1000
MAX_CLIENT_ID = 999
MAX_TIMEOUT_SECONDS = 300
DEFAULT_START_YEAR = 2000
MIN_HISTORICAL_YEAR = 1980

# HTTP status codes
HTTP_STATUS_OK = 200
HTTP_STATUS_UNAUTHORIZED = 401
HTTP_STATUS_FORBIDDEN = 403
HTTP_STATUS_TOO_MANY_REQUESTS = 429

# Time period constants (days)
DAYS_IN_MONTH_APPROX = 30
DAYS_IN_WEEK = 7
DAYS_IN_QUARTER_APPROX = 90
DAYS_IN_YEAR = 365
TRADING_DAYS_PER_WEEK = 5
HOURS_IN_DAY = 24
MINUTES_IN_HOUR = 60
SECONDS_IN_MINUTE = 60

# Unix epoch constants
UNIX_EPOCH_YEAR = 1970
UNIX_EPOCH_MONTH = 1
UNIX_EPOCH_DAY = 1

# File permissions
DEFAULT_DIR_PERMISSIONS_OCTAL_STR = "755"

# Logging and file constants
DEFAULT_LOG_FILE_SIZE_MB = 10
DEFAULT_LOG_BACKUP_COUNT = 5
DEFAULT_LOG_FILE_SIZE_BYTES = 10 * BYTES_PER_MB
MIN_LOG_FILE_SIZE_BYTES = BYTES_PER_KB

# CLI and UI constants
MAX_COMPLETION_MATCHES = 20
MAX_RECENT_SYMBOLS = 20
DEFAULT_COMPLETION_LIMIT = 10
MAX_TABLE_DISPLAY_ROWS = 50

# Time intervals (minutes)
MINUTE_10 = 10
MINUTE_15 = 15
MINUTE_20 = 20
MINUTE_30 = 30

# Retry and resilience constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 1
DEFAULT_EXPONENTIAL_BACKOFF_MULTIPLIER = 2
MAX_RETRY_DELAY_SECONDS = 300

# Cache and performance constants
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour
DEFAULT_CACHE_SIZE = 1000
DEFAULT_CONNECTION_POOL_SIZE = 10

# File permissions (octal)
SECURE_FILE_PERMISSIONS = 0o600  # Read/write for owner only
DEFAULT_DIR_PERMISSIONS = 0o755  # Standard directory permissions

# Common symbols for auto-completion
COMMON_STOCK_SYMBOLS = [
    # Major stocks
    "AAPL",
    "GOOGL",
    "MSFT",
    "AMZN",
    "TSLA",
    "META",
    "NVDA",
    "NFLX",
    "BRKB",
    "JPM",
    "JNJ",
    "V",
    "PG",
    "UNH",
    "HD",
    "MA",
    "DIS",
    "PYPL",
]

COMMON_ETF_SYMBOLS = [
    # Major indices/ETFs
    "SPY",
    "QQQ",
    "IWM",
    "VTI",
    "VOO",
    "VEA",
    "VWO",
    "AGG",
    "BND",
]

COMMON_FUTURES_SYMBOLS = [
    # Futures (Barchart)
    "ES",
    "NQ",
    "YM",
    "RTY",  # Equity indices
    "GC",
    "SI",
    "HG",
    "PL",  # Metals
    "CL",
    "NG",
    "RB",
    "HO",  # Energy
    "ZC",
    "ZS",
    "ZW",
    "ZM",  # Agriculture
    "6E",
    "6B",
    "6J",
    "6A",  # Currencies
]

COMMON_FOREX_SYMBOLS = [
    # Forex pairs
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCHF",
    "AUDUSD",
    "USDCAD",
]

# All common symbols combined for convenience
ALL_COMMON_SYMBOLS = (
    COMMON_STOCK_SYMBOLS
    + COMMON_ETF_SYMBOLS
    + COMMON_FUTURES_SYMBOLS
    + COMMON_FOREX_SYMBOLS
)

# Supported file extensions
SUPPORTED_CONFIG_EXTENSIONS = [".toml", ".yaml", ".yml", ".json"]
SUPPORTED_DATA_EXTENSIONS = [".csv", ".parquet"]

# Error and status codes
SUCCESS_EXIT_CODE = 0
ERROR_EXIT_CODE = 1
USER_ABORT_EXIT_CODE = 2


# ==============================================================================
# Class-based constant organization (for backward compatibility)
# ==============================================================================


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
        BASE_URL = "https://www.barchart.com"
        DOWNLOAD_ENDPOINT = "/my/download"

        # Download request payload defaults
        DEFAULT_ORDER = "asc"
        DEFAULT_DIVIDENDS = "false"
        DEFAULT_BACKADJUST = "false"
        DEFAULT_DBAR = 1
        DEFAULT_CUSTOMBAR = ""
        DEFAULT_VOLUME = "true"
        DEFAULT_OPEN_INTEREST = "true"
        DEFAULT_SPLITS = "true"
        DEFAULT_USAGE_TYPE = "quotes"

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
        DEFAULT_HOST = "localhost"
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
    MAX_ZERO_VOLUME_PERCENTAGE = 0.20  # 20%

    # Price validation
    MIN_VALID_PRICE = 0.01
    MAX_DAILY_PRICE_CHANGE_PERCENTAGE = 0.50  # 50%


class FileSystemConstants:
    """Constants for file system operations."""

    # Directory names
    DEFAULT_OUTPUT_DIR = "./data"
    DEFAULT_CONFIG_DIR = "./config"
    DEFAULT_LOG_DIR = "./logs"

    # File extensions
    CSV_EXTENSION = ".csv"
    PARQUET_EXTENSION = ".parquet"
    JSON_EXTENSION = ".json"
    LOG_EXTENSION = ".log"

    # File permissions (octal)
    SECURE_FILE_PERMISSIONS = 0o600  # Read/write for owner only
    DEFAULT_FILE_PERMISSIONS = 0o644  # Read/write for owner, read for others
    DEFAULT_DIR_PERMISSIONS = (
        0o755  # Read/write/execute for owner, read/execute for others
    )


class NetworkConstants:
    """Constants for network operations."""

    # HTTP settings
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0"
    )
    SIMPLE_USER_AGENT = "Mozilla/5.0"
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
    DEFAULT_LOG_LEVEL = "INFO"

    # Log formats
    CONSOLE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    FILE_FORMAT = (
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )

    # Log rotation
    MAX_LOG_FILE_SIZE_MB = 10
    MAX_LOG_FILES = 5


class TimeConstants:
    """Constants for time-related operations."""

    # Datetime formats
    ISO_DATE_FORMAT = "%Y-%m-%d"
    ISO_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
    US_DATE_FORMAT = "%m/%d/%Y"

    # Time periods (in days)
    DEFAULT_LOOKBACK_DAYS = 365
    MAX_HISTORICAL_DATA_DAYS = 365 * 25  # 25 years
    MIN_INTRADAY_DATA_DAYS = 365 * 2  # 2 years

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
        "barchart": ProviderConstants.Barchart,
        "yahoo": ProviderConstants.Yahoo,
        "ibkr": ProviderConstants.IBKR,
    }

    provider_class = provider_map.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")

    # Convert class attributes to dictionary
    return {
        key: value
        for key, value in provider_class.__dict__.items()
        if not key.startswith("_")
    }
