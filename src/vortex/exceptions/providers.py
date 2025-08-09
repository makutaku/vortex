"""
Data provider-related exceptions.

All exceptions related to data provider authentication, connection, 
and data retrieval operations.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from .base import VortexError
from .templates import ErrorMessageTemplates, RecoverySuggestions, ErrorCodes

if TYPE_CHECKING:
    from vortex.models.period import Period


class DataProviderError(VortexError):
    """Base class for data provider-related errors."""
    
    def __init__(self, provider: str, message: str, help_text: Optional[str] = None, error_code: Optional[str] = None):
        self.provider = provider
        full_message = ErrorMessageTemplates.PROVIDER_ERROR.format(provider=provider, message=message)
        super().__init__(full_message, help_text=help_text, error_code=error_code)


class AuthenticationError(DataProviderError):
    """Raised when authentication with a data provider fails."""
    
    def __init__(self, provider: str, details: Optional[str] = None, http_code: Optional[int] = None):
        message = f"Authentication failed"
        if details:
            message += f" - {details}"
        
        # Use standardized recovery suggestions
        recovery_suggestions = RecoverySuggestions.for_auth_error(provider)
        help_text = recovery_suggestions[0] if recovery_suggestions else f"Verify your {provider} credentials"
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
            provider, message, help_text, ErrorCodes.PROVIDER_AUTH_FAILED
        )
        self.context.update(context)
        self.user_action = user_action
        self.technical_details = technical_details


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
        
        super().__init__(provider, message, help_text=help_text, error_code="RATE_LIMIT")


class VortexConnectionError(DataProviderError):
    """Raised when connection to data provider fails."""
    
    def __init__(self, provider: str, details: Optional[str] = None):
        message = "Connection failed"
        if details:
            message += f": {details}"
        
        help_text = f"Check your internet connection and {provider} service status"
        super().__init__(provider, message, help_text=help_text, error_code="CONNECTION_FAILED")


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
        super().__init__(provider, message, help_text=help_text, error_code="DATA_NOT_FOUND")


class AllowanceLimitExceededError(DataProviderError):
    """Raised when API allowance/quota limits are exceeded."""
    
    def __init__(self, provider: str, current_allowance: int, max_allowance: int):
        self.current_allowance = current_allowance
        self.max_allowance = max_allowance
        
        message = f"Allowance limit exceeded: {current_allowance}/{max_allowance}"
        help_text = f"Wait for allowance reset or upgrade your {provider} subscription"
        super().__init__(provider, message, help_text=help_text, error_code="ALLOWANCE_EXCEEDED")