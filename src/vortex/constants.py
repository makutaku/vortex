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
    "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "NFLX",
    "BRKB", "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL"
]

COMMON_ETF_SYMBOLS = [
    # Major indices/ETFs
    "SPY", "QQQ", "IWM", "VTI", "VOO", "VEA", "VWO", "AGG", "BND"
]

COMMON_FUTURES_SYMBOLS = [
    # Futures (Barchart)
    "ES", "NQ", "YM", "RTY",  # Equity indices
    "GC", "SI", "HG", "PL",   # Metals
    "CL", "NG", "RB", "HO",   # Energy
    "ZC", "ZS", "ZW", "ZM",   # Agriculture
    "6E", "6B", "6J", "6A",   # Currencies
]

COMMON_FOREX_SYMBOLS = [
    # Forex pairs
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"
]

# All common symbols combined for convenience
ALL_COMMON_SYMBOLS = (
    COMMON_STOCK_SYMBOLS + 
    COMMON_ETF_SYMBOLS + 
    COMMON_FUTURES_SYMBOLS + 
    COMMON_FOREX_SYMBOLS
)

# Supported file extensions
SUPPORTED_CONFIG_EXTENSIONS = [".toml", ".yaml", ".yml", ".json"]
SUPPORTED_DATA_EXTENSIONS = [".csv", ".parquet"]

# Error and status codes
SUCCESS_EXIT_CODE = 0
ERROR_EXIT_CODE = 1
USER_ABORT_EXIT_CODE = 2