"""
Utility functions for correlation ID management.

Provides simple utility functions that offer compatibility with the
original utils.correlation API while leveraging the unified correlation system.
"""

from typing import Optional

from .manager import CorrelationIdManager


def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID for this thread."""
    return CorrelationIdManager.get_current_id()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for this thread."""
    CorrelationIdManager.set_correlation_id(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return CorrelationIdManager.generate_id()


def clear_correlation_id() -> None:
    """Clear the correlation ID for this thread."""
    CorrelationIdManager.clear_context()


def get_structured_logger():
    """
    Get structured logger for compatibility with utils.correlation.

    This provides a fallback for the original utils.correlation API
    that expected a structured logger.
    """
    try:
        from vortex.shared.utils.logging_utils import get_structured_logger

        return get_structured_logger()
    except ImportError:
        # Graceful fallback if structured logger not available
        return None


class CorrelationContext:
    """
    Context manager for correlation ID management (utils.correlation compatibility).

    This provides compatibility with the original utils.correlation.CorrelationContext
    class while leveraging the more powerful unified correlation system.
    """

    def __init__(self, correlation_id: Optional[str] = None):
        """Initialize correlation context.

        Args:
            correlation_id: Correlation ID to use, or None to generate new one
        """
        self.correlation_id = correlation_id or generate_correlation_id()
        self._context_manager = None

    def __enter__(self) -> str:
        """Enter the correlation context."""
        self._context_manager = CorrelationIdManager.correlation_context(
            correlation_id=self.correlation_id
        )
        context = self._context_manager.__enter__()
        return context.correlation_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the correlation context."""
        if self._context_manager:
            return self._context_manager.__exit__(exc_type, exc_val, exc_tb)
