"""
Standardized error handling strategies for the Vortex application.

This module defines consistent error handling patterns that should be used
across the entire codebase to replace the current inconsistent approaches.
"""

import logging
from enum import Enum
from typing import Any, Callable, Optional, Type, TypeVar, Union
from functools import wraps
from dataclasses import dataclass

from vortex.exceptions.base import VortexError

T = TypeVar('T')


class ErrorHandlingStrategy(Enum):
    """Defines standardized error handling strategies."""
    
    FAIL_FAST = "fail_fast"           # Raise exception immediately (for critical operations)
    RETURN_NONE = "return_none"       # Return None on error (for optional operations)  
    RETURN_DEFAULT = "return_default" # Return default value (for operations with fallbacks)
    LOG_AND_CONTINUE = "log_continue" # Log error and continue (for best-effort operations)
    COLLECT_ERRORS = "collect_errors" # Collect errors and return them (for batch operations)


@dataclass
class ErrorContext:
    """Context information for error handling."""
    operation: str
    component: str
    error_type: Optional[Type[Exception]] = None
    default_value: Any = None
    correlation_id: Optional[str] = None


class StandardizedErrorHandler:
    """Centralized error handling with consistent strategies."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        strategy: ErrorHandlingStrategy
    ) -> Any:
        """Handle error using the specified strategy."""
        
        # Always log the error with context
        self._log_error(error, context)
        
        if strategy == ErrorHandlingStrategy.FAIL_FAST:
            return self._fail_fast(error, context)
        elif strategy == ErrorHandlingStrategy.RETURN_NONE:
            return self._return_none(error, context)
        elif strategy == ErrorHandlingStrategy.RETURN_DEFAULT:
            return self._return_default(error, context)
        elif strategy == ErrorHandlingStrategy.LOG_AND_CONTINUE:
            return self._log_and_continue(error, context)
        elif strategy == ErrorHandlingStrategy.COLLECT_ERRORS:
            return self._collect_errors(error, context)
        else:
            raise ValueError(f"Unknown error handling strategy: {strategy}")
    
    def _log_error(self, error: Exception, context: ErrorContext):
        """Log error with consistent format."""
        correlation_part = f"[{context.correlation_id}] " if context.correlation_id else ""
        self.logger.error(
            f"{correlation_part}{context.component}.{context.operation} failed: {error}",
            exc_info=isinstance(error, VortexError)
        )
    
    def _fail_fast(self, error: Exception, context: ErrorContext):
        """Raise exception immediately (critical operations)."""
        if isinstance(error, VortexError):
            raise error
        # Wrap non-Vortex exceptions in a VortexError
        raise VortexError(f"{context.component}.{context.operation} failed: {error}") from error
    
    def _return_none(self, error: Exception, context: ErrorContext) -> None:
        """Return None (optional operations)."""
        return None
    
    def _return_default(self, error: Exception, context: ErrorContext):
        """Return default value (operations with fallbacks)."""
        return context.default_value
    
    def _log_and_continue(self, error: Exception, context: ErrorContext):
        """Log error and continue (best-effort operations)."""
        # Error already logged in _log_error
        pass
    
    def _collect_errors(self, error: Exception, context: ErrorContext):
        """Collect errors for batch operations."""
        return {
            'error': error,
            'operation': context.operation,
            'component': context.component
        }


def with_error_handling(
    strategy: ErrorHandlingStrategy,
    operation: str,
    component: str,
    default_value: Any = None,
    error_types: Optional[tuple] = None
):
    """
    Decorator that applies standardized error handling to functions.
    
    Args:
        strategy: Error handling strategy to use
        operation: Name of the operation being performed
        component: Name of the component/module
        default_value: Default value to return (for RETURN_DEFAULT strategy)
        error_types: Tuple of exception types to handle (default: all exceptions)
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, None, Any]]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            handler = StandardizedErrorHandler()
            context = ErrorContext(
                operation=operation,
                component=component,
                default_value=default_value
            )
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if error_types and not isinstance(e, error_types):
                    raise  # Re-raise if it's not an error type we handle
                
                return handler.handle_error(e, context, strategy)
        
        return wrapper
    return decorator


# Convenience decorators for common patterns
def fail_fast(operation: str, component: str):
    """Decorator for operations that should fail immediately on error."""
    return with_error_handling(ErrorHandlingStrategy.FAIL_FAST, operation, component)


def return_none_on_error(operation: str, component: str, error_types: Optional[tuple] = None):
    """Decorator for optional operations that should return None on error."""
    return with_error_handling(ErrorHandlingStrategy.RETURN_NONE, operation, component, error_types=error_types)


def return_default_on_error(operation: str, component: str, default_value: Any):
    """Decorator for operations with fallback values."""
    return with_error_handling(ErrorHandlingStrategy.RETURN_DEFAULT, operation, component, default_value)


def log_and_continue(operation: str, component: str):
    """Decorator for best-effort operations that should continue on error."""
    return with_error_handling(ErrorHandlingStrategy.LOG_AND_CONTINUE, operation, component)