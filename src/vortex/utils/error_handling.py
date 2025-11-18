"""
Centralized error handling utilities to eliminate duplication across the codebase.

This module provides reusable error handling patterns that were previously
duplicated throughout the application, improving maintainability and consistency.
"""

import logging
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from ..exceptions.config import ConfigurationError, InvalidConfigurationError

# Type variables for generic decorators
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)

# Error message templates for consistency
ERROR_TEMPLATES = {
    "file_permission": "Cannot {operation} {file_type}: {error}. Check file permissions for {file_path}",
    "file_not_found": "Cannot {operation} {file_type}: file not found at {file_path}",
    "provider_registry": "Failed to load provider registry for {context}: {error}",
    "configuration_validation": "Invalid {provider} configuration: {error}",
    "analytics_operation": "Analytics {operation_name} failed: {error}",
    "completion_error": "Completion operation failed: {error}",
}


@dataclass
class ErrorContext:
    """Context information for error handling operations."""

    operation: str
    component: str
    correlation_id: Optional[str] = None
    extra_context: Dict[str, Any] = None

    def __post_init__(self):
        if self.extra_context is None:
            self.extra_context = {}


class SafeOperationHandler:
    """Handles safe operation patterns with consistent error handling."""

    @staticmethod
    def safe_completion(
        operation_func: Callable[..., Optional[List[str]]],
    ) -> Callable[..., List[str]]:
        """
        Decorator to safely handle completion operations with debug logging.

        Used for CLI completion operations where errors should be silently handled
        to avoid breaking the completion experience.

        Args:
            operation_func: The completion function to wrap

        Returns:
            Wrapped function that returns empty list on error
        """

        @wraps(operation_func)
        def wrapper(*args, **kwargs) -> List[str]:
            try:
                result = operation_func(*args, **kwargs)
                if result is None:
                    return []
                return result if isinstance(result, list) else [str(result)]
            except (ValueError, TypeError, KeyError) as e:
                logger.debug(
                    ERROR_TEMPLATES["completion_error"].format(
                        error=f"Expected error: {e}"
                    )
                )
                return []
            except Exception as e:
                logger.warning(
                    ERROR_TEMPLATES["completion_error"].format(
                        error=f"Unexpected error: {e}"
                    )
                )
                return []

        return wrapper

    @staticmethod
    def safe_analytics_operation(
        operation_name: str, operation_func: Callable[..., T], *args, **kwargs
    ) -> Optional[T]:
        """
        Centralized analytics error handling with consistent logging.

        Args:
            operation_name: Name of the analytics operation for logging
            operation_func: Function to execute
            *args, **kwargs: Arguments to pass to operation_func

        Returns:
            Operation result or None if error occurred
        """
        try:
            return operation_func(*args, **kwargs)
        except (ValueError, TypeError, KeyError) as e:
            logger.debug(
                ERROR_TEMPLATES["analytics_operation"].format(
                    operation_name=operation_name, error=f"Expected error: {e}"
                )
            )
            return None
        except Exception as e:
            logger.warning(
                ERROR_TEMPLATES["analytics_operation"].format(
                    operation_name=operation_name, error=f"Unexpected error: {e}"
                )
            )
            return None


class FileOperationHandler:
    """Handles common file operation error patterns with consistent messaging."""

    @staticmethod
    def safe_file_operation(
        file_path: Union[str, Path],
        operation: Callable[[Any], T],
        mode: str = "rb",
        file_type: str = "file",
        operation_name: str = "access",
        default_on_missing: Optional[T] = None,
    ) -> T:
        """
        Centralized file operation with consistent error handling.

        Args:
            file_path: Path to the file
            operation: Function to execute with file handle
            mode: File open mode
            file_type: Type description for error messages
            operation_name: Operation description for error messages
            default_on_missing: Default value to return if file not found (read operations)

        Returns:
            Result of operation

        Raises:
            ConfigurationError: For permission/access errors
            InvalidConfigurationError: For other file operation errors
        """
        try:
            with open(file_path, mode) as f:
                return operation(f)
        except FileNotFoundError:
            if "r" in mode and default_on_missing is not None:
                return default_on_missing
            from vortex.exceptions.base import ExceptionContext

            context = ExceptionContext(
                help_text=f"Create the {file_type} or check the file path"
            )
            raise ConfigurationError(
                ERROR_TEMPLATES["file_not_found"].format(
                    operation=operation_name, file_type=file_type, file_path=file_path
                ),
                context,
            )
        except PermissionError as e:
            from vortex.exceptions.base import ExceptionContext

            context = ExceptionContext(
                help_text=f"Check file permissions for {file_path}"
            )
            raise ConfigurationError(
                ERROR_TEMPLATES["file_permission"].format(
                    operation=operation_name,
                    file_type=file_type,
                    error=e,
                    file_path=file_path,
                ),
                context,
            )
        except Exception:
            raise InvalidConfigurationError(
                "file_operation", str(file_path), f"valid {file_type}"
            )


class ProviderOperationHandler:
    """Handles common provider operation error patterns."""

    @staticmethod
    def with_registry_operation(
        operation_func: Callable[[Any], T], error_context: str = "plugin operation"
    ) -> Optional[T]:
        """
        Execute operation with registry.

        Args:
            operation_func: Function that takes registry as argument
            error_context: Context description for error messages

        Returns:
            Operation result or None if operation fails
        """
        try:
            # Avoid circular import by importing here
            from ..infrastructure.plugins import get_provider_registry

            registry = get_provider_registry()
            return operation_func(registry)
        except Exception as e:
            logger.error(
                ERROR_TEMPLATES["provider_registry"].format(
                    context=error_context, error=e
                )
            )
            return None

    @staticmethod
    def safe_provider_operation(
        provider_name: str,
        operation_func: Callable,
        *args,
        correlation_id: Optional[str] = None,
        **kwargs,
    ) -> Optional[Any]:
        """
        Execute provider operation with consistent error logging.

        Args:
            provider_name: Name of the provider for logging
            operation_func: Provider operation to execute
            correlation_id: Optional correlation ID for tracing
            *args, **kwargs: Arguments for the operation

        Returns:
            Operation result or None if error occurred
        """
        try:
            return operation_func(*args, **kwargs)
        except Exception as e:
            log_context = {"provider": provider_name, "error": str(e)}
            if correlation_id:
                log_context["correlation_id"] = correlation_id

            logger.error("Provider operation failed", **log_context, exc_info=True)
            return None


class ConfigurationErrorHandler:
    """Handles configuration-related error patterns with consistent messaging."""

    @staticmethod
    def validate_provider_config(provider: str, provider_config: dict) -> None:
        """
        Validate provider configuration with consistent error handling.

        Args:
            provider: Provider name
            provider_config: Configuration dictionary

        Raises:
            ConfigurationError: If validation fails
        """
        try:
            # Import here to avoid circular imports
            from ..core.config.models import BarchartConfig, IbkrConfig, YahooConfig

            if provider == "barchart":
                BarchartConfig(**provider_config)
            elif provider == "yahoo":
                YahooConfig(**provider_config)
            elif provider == "ibkr":
                IbkrConfig(**provider_config)
            else:
                raise InvalidConfigurationError(
                    "provider", provider, "barchart, yahoo, or ibkr"
                )
        except Exception as e:
            from vortex.exceptions.base import ExceptionContext

            context = ExceptionContext(
                help_text=f"Check the {provider} configuration format and required fields"
            )
            raise ConfigurationError(
                ERROR_TEMPLATES["configuration_validation"].format(
                    provider=provider, error=e
                ),
                context,
            )


def log_provider_error(
    operation_name: str,
    provider_name: str,
    error: Exception,
    correlation_id: Optional[str] = None,
    **extra_context,
) -> None:
    """
    Centralized provider error logging with consistent format.

    Args:
        operation_name: Name of the operation that failed
        provider_name: Provider that encountered the error
        error: The exception that occurred
        correlation_id: Optional correlation ID for tracing
        **extra_context: Additional context for logging
    """
    log_data = {
        "provider": provider_name,
        "error": str(error),
        "operation": operation_name,
        **extra_context,
    }

    if correlation_id:
        log_data["correlation_id"] = correlation_id

    logger.error(f"Provider {operation_name} failed", **log_data, exc_info=True)


def format_error_message(template_key: str, **kwargs) -> str:
    """
    Format error message using standardized templates.

    Args:
        template_key: Key from ERROR_TEMPLATES
        **kwargs: Values for template formatting

    Returns:
        Formatted error message

    Raises:
        KeyError: If template_key not found
    """
    if template_key not in ERROR_TEMPLATES:
        available_keys = list(ERROR_TEMPLATES.keys())
        raise KeyError(
            f"Unknown error template '{template_key}'. Available: {available_keys}"
        )

    return ERROR_TEMPLATES[template_key].format(**kwargs)
