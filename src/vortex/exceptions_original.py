"""
Vortex Exception Hierarchy

This module provides a comprehensive exception hierarchy for the Vortex financial data
download automation tool. All exceptions include actionable error messages and
context to help users resolve issues.

Exception Hierarchy:
    VortexError (base)
    ├── ConfigurationError
    │   ├── InvalidConfigurationError
    │   ├── MissingConfigurationError
    │   └── ConfigurationValidationError
    ├── DataProviderError  
    │   ├── AuthenticationError
    │   ├── RateLimitError
    │   ├── ConnectionError
    │   ├── DataNotFoundError
    │   └── AllowanceLimitExceededError
    ├── DataStorageError
    │   ├── FileStorageError
    │   ├── PermissionError
    │   └── DiskSpaceError
    ├── InstrumentError
    │   ├── InvalidInstrumentError
    │   └── UnsupportedInstrumentError
    └── CLIError
        ├── InvalidCommandError
        ├── MissingArgumentError
        └── UserAbortError
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from .instruments.period import Period


class VortexError(Exception):
    """Base exception for all Vortex-related errors.
    
    All Vortex exceptions should inherit from this class to provide
    consistent error handling and user experience.
    
    Attributes:
        message: The error message
        help_text: Optional actionable guidance for the user
        error_code: Optional error code for programmatic handling
        correlation_id: Unique ID for tracking this error across logs
        context: Additional context information
        user_action: Suggested user action to resolve the issue
        technical_details: Technical information for debugging
    """
    
    def __init__(
        self, 
        message: str, 
        help_text: Optional[str] = None, 
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_action: Optional[str] = None,
        technical_details: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        self.message = message
        self.help_text = help_text
        self.error_code = error_code
        self.context = context or {}
        self.user_action = user_action
        self.technical_details = technical_details
        self.correlation_id = correlation_id or str(uuid.uuid4())[:8]
        self.timestamp = datetime.now()
        
        super().__init__(message)
    
    def __str__(self) -> str:
        result = self.message
        
        if self.help_text:
            result += f"\n\n💡 Help: {self.help_text}"
            
        if self.user_action:
            result += f"\n\n🔧 Action: {self.user_action}"
            
        if self.context:
            context_items = [f"{k}: {v}" for k, v in self.context.items() if v is not None]
            if context_items:
                result += f"\n\n📋 Context: {', '.join(context_items)}"
        
        result += f"\n\n🔍 Error ID: {self.correlation_id}"
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            'error_type': self.__class__.__name__,
            'message': self.message,
            'error_code': self.error_code,
            'correlation_id': self.correlation_id,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'help_text': self.help_text,
            'user_action': self.user_action,
            'technical_details': self.technical_details
        }
    
    def add_context(self, **kwargs) -> 'VortexError':
        """Add additional context to the exception."""
        self.context.update(kwargs)
        return self


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(VortexError):
    """Base class for configuration-related errors."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration contains invalid values."""
    
    def __init__(self, field: str, value: Any, expected: str):
        message = f"Invalid configuration for '{field}': got '{value}', expected {expected}"
        help_text = f"Please check your configuration file or use 'vortex config --help' for guidance"
        super().__init__(message, help_text, "CONFIG_INVALID")


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    
    def __init__(self, field: str, config_location: Optional[str] = None):
        message = f"Missing required configuration: '{field}'"
        help_text = f"Set this value using 'vortex config --provider <provider> --set-credentials'"
        if config_location:
            help_text += f" or add it to {config_location}"
        super().__init__(message, help_text, "CONFIG_MISSING")


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration fails validation."""
    
    def __init__(self, errors: List[str]):
        message = f"Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        help_text = "Fix the configuration errors above and try again"
        super().__init__(message, help_text, "CONFIG_VALIDATION")


# =============================================================================
# Data Provider Errors
# =============================================================================

class DataProviderError(VortexError):
    """Base class for data provider-related errors."""
    
    def __init__(self, provider: str, message: str, help_text: Optional[str] = None, error_code: Optional[str] = None):
        self.provider = provider
        full_message = f"[{provider.upper()}] {message}"
        super().__init__(full_message, help_text, error_code)


class AuthenticationError(DataProviderError):
    """Raised when authentication with a data provider fails."""
    
    def __init__(self, provider: str, details: Optional[str] = None, http_code: Optional[int] = None):
        message = "Authentication failed"
        if details:
            message += f": {details}"
        
        help_text = f"Verify your {provider} credentials are correct and active"
        user_action = f"Run: vortex config --provider {provider} --set-credentials"
        
        context = {"provider": provider}
        if http_code:
            context["http_code"] = http_code
            
        technical_details = None
        if http_code == 401:
            technical_details = "HTTP 401 Unauthorized - Invalid credentials"
        elif http_code == 403:
            technical_details = "HTTP 403 Forbidden - Valid credentials but insufficient permissions"
        elif http_code == 429:
            technical_details = "HTTP 429 Too Many Requests - Authentication rate limited"
            
        super().__init__(
            provider, message, help_text, "AUTH_FAILED",
            context=context, user_action=user_action, technical_details=technical_details
        )


class RateLimitError(DataProviderError):
    """Raised when API rate limits are exceeded."""
    
    def __init__(self, provider: str, wait_time: Optional[int] = None, daily_limit: Optional[int] = None):
        message = "Rate limit exceeded"
        if daily_limit:
            message += f" (daily limit: {daily_limit})"
        
        help_text = "Wait before retrying"
        if wait_time:
            help_text += f" (suggested wait: {wait_time} seconds)"
        help_text += f" or check your {provider} subscription limits"
        
        super().__init__(provider, message, help_text, "RATE_LIMIT")


class ConnectionError(DataProviderError):
    """Raised when connection to data provider fails."""
    
    def __init__(self, provider: str, details: Optional[str] = None):
        message = "Connection failed"
        if details:
            message += f": {details}"
        
        help_text = f"Check your internet connection and {provider} service status"
        super().__init__(provider, message, help_text, "CONNECTION_FAILED")


@dataclass
class DataNotFoundError(DataProviderError):
    """Raised when requested data is not available from the provider."""
    
    def __init__(self, provider: str, symbol: str, period: "Period", 
                 start_date: datetime, end_date: datetime, http_code: Optional[int] = None):
        self.symbol = symbol
        self.period = period
        self.start_date = start_date
        self.end_date = end_date
        self.http_code = http_code
        
        message = f"No data found for {symbol} ({period}) from {start_date.date()} to {end_date.date()}"
        if http_code:
            message += f" (HTTP {http_code})"
        
        help_text = f"Verify that {symbol} is valid and data exists for the requested date range on {provider}"
        super().__init__(provider, message, help_text, "DATA_NOT_FOUND")


class AllowanceLimitExceededError(DataProviderError):
    """Raised when API allowance/quota limits are exceeded."""
    
    def __init__(self, provider: str, current_allowance: int, max_allowance: int):
        self.current_allowance = current_allowance
        self.max_allowance = max_allowance
        
        message = f"Allowance limit exceeded: {current_allowance}/{max_allowance}"
        help_text = f"Wait for allowance reset or upgrade your {provider} subscription"
        super().__init__(provider, message, help_text, "ALLOWANCE_EXCEEDED")


# =============================================================================
# Data Storage Errors
# =============================================================================

class DataStorageError(VortexError):
    """Base class for data storage-related errors."""
    pass


class FileStorageError(DataStorageError):
    """Raised when file storage operations fail."""
    
    def __init__(self, operation: str, file_path: Path, details: Optional[str] = None):
        self.operation = operation
        self.file_path = file_path
        
        message = f"File {operation} failed: {file_path}"
        if details:
            message += f" - {details}"
        
        help_text = f"Check file permissions and available disk space for {file_path.parent}"
        super().__init__(message, help_text, "FILE_STORAGE_ERROR")


class PermissionError(DataStorageError):
    """Raised when file system permissions prevent operations."""
    
    def __init__(self, path: Path, operation: str = "access"):
        message = f"Permission denied: cannot {operation} {path}"
        help_text = f"Check file/directory permissions for {path} and ensure Vortex has the necessary access rights"
        super().__init__(message, help_text, "PERMISSION_DENIED")


class DiskSpaceError(DataStorageError):
    """Raised when insufficient disk space is available."""
    
    def __init__(self, path: Path, required_space: Optional[str] = None):
        message = f"Insufficient disk space: {path}"
        if required_space:
            message += f" (need at least {required_space})"
        
        help_text = f"Free up disk space in {path} or choose a different output directory"
        super().__init__(message, help_text, "DISK_SPACE_ERROR")


# =============================================================================
# Instrument Errors
# =============================================================================

class InstrumentError(VortexError):
    """Base class for instrument-related errors."""
    pass


class InvalidInstrumentError(InstrumentError):
    """Raised when an instrument specification is invalid."""
    
    def __init__(self, symbol: str, reason: str):
        message = f"Invalid instrument '{symbol}': {reason}"
        help_text = "Check the symbol format and ensure it's supported by the selected provider"
        super().__init__(message, help_text, "INVALID_INSTRUMENT")


class UnsupportedInstrumentError(InstrumentError):
    """Raised when an instrument is not supported by the provider."""
    
    def __init__(self, symbol: str, provider: str, supported_types: Optional[List[str]] = None):
        message = f"Instrument '{symbol}' not supported by {provider}"
        if supported_types:
            message += f" (supports: {', '.join(supported_types)})"
        
        help_text = f"Use 'vortex providers --info {provider}' to see supported instrument types"
        super().__init__(message, help_text, "UNSUPPORTED_INSTRUMENT")


# =============================================================================
# CLI Errors
# =============================================================================

class CLIError(VortexError):
    """Base class for CLI-related errors."""
    pass


class InvalidCommandError(CLIError):
    """Raised when CLI command usage is invalid."""
    
    def __init__(self, command: str, reason: str):
        message = f"Invalid command usage: {reason}"
        help_text = f"Use 'vortex {command} --help' for correct usage"
        super().__init__(message, help_text, "INVALID_COMMAND")


class MissingArgumentError(CLIError):
    """Raised when required CLI arguments are missing."""
    
    def __init__(self, argument: str, command: str):
        message = f"Missing required argument: {argument}"
        help_text = f"Use 'vortex {command} --help' to see all required arguments"
        super().__init__(message, help_text, "MISSING_ARGUMENT")


class UserAbortError(CLIError):
    """Raised when user explicitly aborts an operation."""
    
    def __init__(self, reason: Optional[str] = None):
        message = "Operation aborted by user"
        if reason:
            message += f": {reason}"
        super().__init__(message, error_code="USER_ABORT")


# =============================================================================
# Legacy Exception Compatibility
# =============================================================================

# Maintain compatibility with existing code while migrating
# These will be removed in a future version

class DownloadError(DataProviderError):
    """Legacy exception - use DataProviderError instead."""
    
    def __init__(self, status: str, msg: str):
        super().__init__("legacy", f"Download failed ({status}): {msg}", error_code="DOWNLOAD_ERROR")
        self.status = status
        self.msg = msg


class LowDataError(DataProviderError):
    """Legacy exception - use DataNotFoundError instead."""
    
    def __init__(self, provider: str = "unknown"):
        super().__init__(provider, "Insufficient data available", error_code="LOW_DATA")


# Re-export legacy exceptions for backward compatibility
NotFoundError = DataNotFoundError
AllowanceLimitExceeded = AllowanceLimitExceededError