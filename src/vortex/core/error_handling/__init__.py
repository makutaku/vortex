"""
Core error handling module for standardized error management across Vortex.
"""

from .strategies import (
    ErrorContext,
    ErrorHandlingStrategy,
    StandardizedErrorHandler,
    fail_fast,
    log_and_continue,
    return_default_on_error,
    return_none_on_error,
    with_error_handling,
)

__all__ = [
    "ErrorHandlingStrategy",
    "StandardizedErrorHandler",
    "ErrorContext",
    "with_error_handling",
    "fail_fast",
    "return_none_on_error",
    "return_default_on_error",
    "log_and_continue",
]
