"""
Correlation decorators for automatic context management.

Provides decorators for automatically adding correlation context to functions,
combining features from both the utils and resilience correlation implementations.
"""

import functools
from typing import Callable, Optional

from .manager import CorrelationIdManager
from .utils import get_structured_logger


def with_correlation(
    operation: Optional[str] = None,
    provider: Optional[str] = None,
    generate_id: bool = True,
):
    """
    Decorator to add correlation context to a function.

    This is the primary decorator for adding correlation tracking to any function.
    It combines the simplicity of the utils version with the power of the
    resilience version.

    Args:
        operation: Name of the operation (defaults to function name)
        provider: Data provider name
        generate_id: Whether to generate a new correlation ID
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__

            # Use existing correlation ID if present and not generating new
            correlation_id = None
            if not generate_id:
                correlation_id = CorrelationIdManager.get_current_id()

            with CorrelationIdManager.correlation_context(
                correlation_id=correlation_id, operation=op_name, provider=provider
            ):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def with_provider_correlation(provider: str):
    """
    Decorator specifically for data provider operations.

    Args:
        provider: Name of the data provider
    """
    return with_correlation(provider=provider, generate_id=True)


def track_operation(operation_name: str, correlation_id: Optional[str] = None):
    """
    Decorator to track an operation with structured logging.

    This provides compatibility with the utils.correlation API while
    leveraging the more powerful correlation context system.

    Args:
        operation_name: Name of the operation being tracked
        correlation_id: Correlation ID to use, or None to generate new one

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with CorrelationIdManager.correlation_context(
                correlation_id=correlation_id, operation=operation_name
            ) as context:
                try:
                    # Log operation start (compatible with utils version)
                    logger = get_structured_logger()
                    if logger and hasattr(logger, "log_operation_start"):
                        logger.log_operation_start(
                            operation=operation_name,
                            correlation_id=context.correlation_id,
                            context={
                                "function": func.__name__,
                                "module": func.__module__,
                                "args_count": len(args),
                                "kwargs_keys": list(kwargs.keys()),
                            },
                        )

                    # Execute the function
                    result = func(*args, **kwargs)

                    # Log successful completion
                    if logger and hasattr(logger, "log_operation_success"):
                        logger.log_operation_success(
                            operation=operation_name,
                            correlation_id=context.correlation_id,
                            context={"result_type": type(result).__name__},
                        )

                    return result

                except Exception as e:
                    # Log operation failure
                    if logger and hasattr(logger, "log_operation_failure"):
                        logger.log_operation_failure(
                            operation=operation_name,
                            correlation_id=context.correlation_id,
                            error=e,
                            context={
                                "function": func.__name__,
                                "module": func.__module__,
                            },
                        )

                    # Add correlation ID to VortexError exceptions
                    if hasattr(e, "correlation_id"):
                        e.correlation_id = context.correlation_id

                    raise

        return wrapper

    return decorator
