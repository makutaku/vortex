"""
Core error handling module for standardized error management across Vortex.
"""

from .strategies import (
    ErrorHandlingStrategy,
    StandardizedErrorHandler,
    ErrorContext,
    with_error_handling,
    fail_fast,
    return_none_on_error,
    return_default_on_error,
    log_and_continue
)

__all__ = [
    'ErrorHandlingStrategy',
    'StandardizedErrorHandler', 
    'ErrorContext',
    'with_error_handling',
    'fail_fast',
    'return_none_on_error',
    'return_default_on_error',
    'log_and_continue'
]