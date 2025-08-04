"""
Correlation ID management for tracking operations across Vortex components.

This module provides utilities for generating, managing, and propagating
correlation IDs throughout the system for better observability and debugging.
"""

import functools
import threading
from typing import Optional, Any, Callable
from uuid import uuid4

from .logging_utils import get_structured_logger


# Thread-local storage for correlation IDs
_thread_local = threading.local()


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID for this thread."""
    return getattr(_thread_local, 'correlation_id', None)


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for this thread."""
    _thread_local.correlation_id = correlation_id


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid4())[:8]  # Short ID for readability


def clear_correlation_id() -> None:
    """Clear the correlation ID for this thread."""
    if hasattr(_thread_local, 'correlation_id'):
        delattr(_thread_local, 'correlation_id')


def with_correlation_id(correlation_id: Optional[str] = None):
    """
    Decorator to run a function with a correlation ID.
    
    If no correlation ID is provided, generates a new one.
    The correlation ID is available to the function and any code it calls.
    
    Args:
        correlation_id: Correlation ID to use, or None to generate new one
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate correlation ID if not provided
            corr_id = correlation_id or generate_correlation_id()
            
            # Store previous correlation ID to restore later
            previous_id = get_correlation_id()
            
            try:
                # Set the correlation ID for this operation
                set_correlation_id(corr_id)
                
                # Log operation start
                logger = get_structured_logger()
                logger.log_operation_start(
                    operation=f"{func.__module__}.{func.__name__}",
                    correlation_id=corr_id,
                    context={
                        "function": func.__name__,
                        "module": func.__module__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys())
                    }
                )
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Log successful completion
                logger.log_operation_success(
                    operation=f"{func.__module__}.{func.__name__}",
                    correlation_id=corr_id,
                    context={"result_type": type(result).__name__}
                )
                
                return result
                
            except Exception as e:
                # Log operation failure
                logger = get_structured_logger()
                logger.log_operation_failure(
                    operation=f"{func.__module__}.{func.__name__}",
                    correlation_id=corr_id,
                    error=e,
                    context={
                        "function": func.__name__,
                        "module": func.__module__,
                    }
                )
                
                # Re-raise the exception with correlation ID if it's a VortexError
                if hasattr(e, 'correlation_id'):
                    e.correlation_id = corr_id
                
                raise
                
            finally:
                # Restore previous correlation ID
                if previous_id is not None:
                    set_correlation_id(previous_id)
                else:
                    clear_correlation_id()
        
        return wrapper
    return decorator


def track_operation(operation_name: str, correlation_id: Optional[str] = None):
    """
    Decorator to track an operation with structured logging.
    
    Similar to with_correlation_id but allows custom operation names.
    
    Args:
        operation_name: Name of the operation being tracked
        correlation_id: Correlation ID to use, or None to generate new one
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate correlation ID if not provided
            corr_id = correlation_id or generate_correlation_id()
            
            # Store previous correlation ID to restore later
            previous_id = get_correlation_id()
            
            try:
                # Set the correlation ID for this operation
                set_correlation_id(corr_id)
                
                # Log operation start
                logger = get_structured_logger()
                logger.log_operation_start(
                    operation=operation_name,
                    correlation_id=corr_id,
                    context={
                        "function": func.__name__,
                        "module": func.__module__,
                    }
                )
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Log successful completion
                logger.log_operation_success(
                    operation=operation_name,
                    correlation_id=corr_id
                )
                
                return result
                
            except Exception as e:
                # Log operation failure
                logger = get_structured_logger()
                logger.log_operation_failure(
                    operation=operation_name,
                    correlation_id=corr_id,
                    error=e
                )
                
                # Add correlation ID to VortexError exceptions
                if hasattr(e, 'correlation_id'):
                    e.correlation_id = corr_id
                
                raise
                
            finally:
                # Restore previous correlation ID
                if previous_id is not None:
                    set_correlation_id(previous_id)
                else:
                    clear_correlation_id()
        
        return wrapper
    return decorator


class CorrelationContext:
    """Context manager for correlation ID management."""
    
    def __init__(self, correlation_id: Optional[str] = None):
        """Initialize correlation context.
        
        Args:
            correlation_id: Correlation ID to use, or None to generate new one
        """
        self.correlation_id = correlation_id or generate_correlation_id()
        self.previous_id = None
    
    def __enter__(self) -> str:
        """Enter the correlation context."""
        self.previous_id = get_correlation_id()
        set_correlation_id(self.correlation_id)
        return self.correlation_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the correlation context."""
        if self.previous_id is not None:
            set_correlation_id(self.previous_id)
        else:
            clear_correlation_id()