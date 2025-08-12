"""
Instrument-related exceptions.

All exceptions related to financial instrument validation and processing.
"""

from typing import List, Optional

from .base import VortexError


class InstrumentError(VortexError):
    """Base class for instrument-related errors."""
    pass


class InvalidInstrumentError(InstrumentError):
    """Raised when an instrument specification is invalid."""
    
    def __init__(self, symbol: str, reason: str):
        from .base import ExceptionContext
        message = f"Invalid instrument '{symbol}': {reason}"
        help_text = "Check the symbol format and ensure it's supported by the selected provider"
        context = ExceptionContext(help_text=help_text, error_code="INVALID_INSTRUMENT")
        super().__init__(message, context)


class UnsupportedInstrumentError(InstrumentError):
    """Raised when an instrument is not supported by the provider."""
    
    def __init__(self, symbol: str, provider: str, supported_types: Optional[List[str]] = None):
        from .base import ExceptionContext
        message = f"Instrument '{symbol}' not supported by {provider}"
        if supported_types:
            message += f" (supports: {', '.join(supported_types)})"
        
        help_text = f"Use 'vortex providers --info {provider}' to see supported instrument types"
        context = ExceptionContext(help_text=help_text, error_code="UNSUPPORTED_INSTRUMENT")
        super().__init__(message, context)