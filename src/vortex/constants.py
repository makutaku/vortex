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

# Time period constants (days)
DAYS_IN_MONTH_APPROX = 30
DAYS_IN_WEEK = 7
HOURS_IN_DAY = 24
MINUTES_IN_HOUR = 60
SECONDS_IN_MINUTE = 60

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