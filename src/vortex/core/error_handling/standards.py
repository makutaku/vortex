"""
Standardized error handling patterns and decorators.

This module provides consistent error handling patterns to ensure uniform
error handling across the entire Vortex codebase.
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, TypeVar

from vortex.exceptions.base import VortexError
from vortex.exceptions.config import ConfigurationError, ConfigurationValidationError
from vortex.exceptions.providers import AuthenticationError, DataProviderError
from vortex.exceptions.storage import DataStorageError, VortexPermissionError

T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


class ErrorCategories:
    """Categorized exception types for consistent handling."""

    # Expected errors that should be handled gracefully
    EXPECTED_ERRORS: Tuple[Type[Exception], ...] = (
        ValueError,
        TypeError,
        KeyError,
        FileNotFoundError,
        PermissionError,
    )

    # Vortex-specific expected errors
    VORTEX_EXPECTED_ERRORS: Tuple[Type[VortexError], ...] = (
        ConfigurationError,
        ConfigurationValidationError,
        DataProviderError,
        DataStorageError,
        VortexPermissionError,
    )

    # Authentication errors that should not be retried
    NON_RETRYABLE_ERRORS: Tuple[Type[Exception], ...] = (
        AuthenticationError,
        PermissionError,
        VortexPermissionError,
    )

    # All expected errors (union of above)
    ALL_EXPECTED_ERRORS: Tuple[Type[Exception], ...] = (
        EXPECTED_ERRORS + VORTEX_EXPECTED_ERRORS
    )


def standard_error_handler(
    operation_name: str,
    expected_errors: Optional[Tuple[Type[Exception], ...]] = None,
    reraise_unexpected: bool = True,
    log_unexpected: bool = True,
) -> Callable[[F], F]:
    """
    Standard error handling decorator with consistent logging and categorization.

    Args:
        operation_name: Name of the operation for logging context
        expected_errors: Tuple of expected exception types to handle gracefully
        reraise_unexpected: Whether to reraise unexpected exceptions
        log_unexpected: Whether to log unexpected exceptions with exc_info

    Returns:
        Decorated function with standardized error handling
    """
    if expected_errors is None:
        expected_errors = ErrorCategories.ALL_EXPECTED_ERRORS

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except expected_errors as e:
                logger.warning(
                    f"{operation_name} failed with expected error: {e}",
                    extra={
                        "operation": operation_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                    },
                )
                raise  # Re-raise expected errors for proper handling
            except Exception as e:
                if log_unexpected:
                    logger.error(
                        f"{operation_name} failed with unexpected error: {e}",
                        extra={
                            "operation": operation_name,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                        exc_info=True,
                    )

                if reraise_unexpected:
                    raise
                return None

        return wrapper

    return decorator


def safe_operation(
    operation_name: str, default_return: Any = None, log_level: str = "warning"
) -> Callable[[F], F]:
    """
    Decorator for operations that should never raise exceptions.

    Args:
        operation_name: Name of the operation for logging
        default_return: Value to return on any exception
        log_level: Logging level for errors ('debug', 'info', 'warning', 'error')

    Returns:
        Decorated function that returns default_return on any exception
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except ErrorCategories.ALL_EXPECTED_ERRORS as e:
                log_func = getattr(logger, log_level)
                log_func(
                    f"{operation_name} failed (expected): {e}",
                    extra={"operation": operation_name, "error_type": type(e).__name__},
                )
                return default_return
            except Exception as e:
                logger.error(
                    f"{operation_name} failed (unexpected): {e}",
                    extra={"operation": operation_name, "error_type": type(e).__name__},
                    exc_info=True,
                )
                return default_return

        return wrapper

    return decorator


def validation_error_handler(field_name: str) -> Callable[[F], F]:
    """
    Specialized decorator for validation operations.

    Args:
        field_name: Name of the field being validated

    Returns:
        Decorated function with validation-specific error handling
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except (ValueError, TypeError) as e:
                logger.info(
                    f"Validation failed for {field_name}: {e}",
                    extra={"field": field_name, "error_type": type(e).__name__},
                )
                raise ConfigurationValidationError([f"Invalid {field_name}: {e}"])
            except Exception as e:
                logger.error(
                    f"Unexpected validation error for {field_name}: {e}",
                    extra={"field": field_name, "error_type": type(e).__name__},
                    exc_info=True,
                )
                raise ConfigurationValidationError(
                    [f"Validation error for {field_name}: {e}"]
                )

        return wrapper

    return decorator


def provider_operation_handler(provider_name: str) -> Callable[[F], F]:
    """
    Specialized decorator for data provider operations.

    Args:
        provider_name: Name of the data provider

    Returns:
        Decorated function with provider-specific error handling
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except DataProviderError:
                # Re-raise DataProviderError as-is
                raise
            except AuthenticationError:
                # Re-raise AuthenticationError as-is
                raise
            except (ValueError, TypeError, KeyError) as e:
                logger.warning(
                    f"Provider {provider_name} operation failed: {e}",
                    extra={
                        "provider": provider_name,
                        "operation": func.__name__,
                        "error_type": type(e).__name__,
                    },
                )
                raise DataProviderError(provider_name, f"Operation failed: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error in provider {provider_name}: {e}",
                    extra={
                        "provider": provider_name,
                        "operation": func.__name__,
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                raise DataProviderError(provider_name, f"Unexpected error: {e}")

        return wrapper

    return decorator


def cli_command_handler(command_name: str) -> Callable[[F], F]:
    """
    Specialized decorator for CLI command operations.

    Args:
        command_name: Name of the CLI command

    Returns:
        Decorated function with CLI-specific error handling
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except KeyboardInterrupt:
                logger.info(f"CLI command '{command_name}' cancelled by user")
                import click

                raise click.Abort()
            except VortexError as e:
                logger.error(
                    f"CLI command '{command_name}' failed: {e.message}",
                    extra={
                        "command": command_name,
                        "error_type": type(e).__name__,
                        "correlation_id": getattr(e, "correlation_id", None),
                    },
                )
                raise
            except Exception as e:
                logger.error(
                    f"Unexpected error in CLI command '{command_name}': {e}",
                    extra={"command": command_name, "error_type": type(e).__name__},
                    exc_info=True,
                )
                import click

                raise click.Abort()

        return wrapper

    return decorator


class ErrorHandlingMixin:
    """
    Mixin class providing standardized error handling methods.

    Classes can inherit from this mixin to get consistent error handling
    across different components.
    """

    def __init__(self, component_name: str = None):
        self.component_name = component_name or self.__class__.__name__
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def handle_expected_error(self, error: Exception, operation: str) -> None:
        """Handle expected errors with appropriate logging."""
        self.logger.warning(
            f"{self.component_name} {operation} failed: {error}",
            extra={
                "component": self.component_name,
                "operation": operation,
                "error_type": type(error).__name__,
            },
        )

    def handle_unexpected_error(self, error: Exception, operation: str) -> None:
        """Handle unexpected errors with detailed logging."""
        self.logger.error(
            f"{self.component_name} {operation} unexpected error: {error}",
            extra={
                "component": self.component_name,
                "operation": operation,
                "error_type": type(error).__name__,
            },
            exc_info=True,
        )

    def safe_execute(
        self, operation: str, func: Callable[[], T], default: T = None
    ) -> T:
        """Safely execute a function with standardized error handling."""
        try:
            return func()
        except ErrorCategories.ALL_EXPECTED_ERRORS as e:
            self.handle_expected_error(e, operation)
            return default
        except Exception as e:
            self.handle_unexpected_error(e, operation)
            return default
