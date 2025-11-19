"""
Core correlation ID management and request tracking.

This module provides the main CorrelationIdManager class and supporting
infrastructure for managing correlation IDs across the Vortex system.
"""

# Use standard Python logging for compatibility
import logging
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
_structured_logger = False


def _log_with_context(level, message, **kwargs):
    """Log message with context, handling both structured and standard loggers."""
    # Always use string formatting for compatibility - structured logging disabled
    context_parts = [f"{k}={v}" for k, v in kwargs.items() if v is not None]
    if context_parts:
        full_message = f"{message} ({', '.join(context_parts)})"
    else:
        full_message = message
    getattr(logger, level)(full_message)


# Thread-local storage for correlation context
_context_storage = threading.local()


@dataclass
class CorrelationContext:
    """
    Context information for request correlation.

    Stores all relevant information about a correlated operation,
    including timing, metadata, and hierarchical relationships.
    """

    correlation_id: str
    parent_id: Optional[str] = None
    operation: Optional[str] = None
    provider: Optional[str] = None
    start_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def elapsed_seconds(self) -> float:
        """Get elapsed time since operation start."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()


class CorrelationIdManager:
    """
    Manager for correlation IDs and request tracing.

    Provides comprehensive context management for tracking requests across
    multiple components and external service calls. Combines features from
    both the utils and resilience correlation implementations.
    """

    @staticmethod
    def generate_id() -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())[:8]  # Short ID for readability

    @staticmethod
    def get_current_id() -> Optional[str]:
        """Get the current correlation ID from thread-local storage."""
        return getattr(_context_storage, "correlation_id", None)

    @staticmethod
    def get_current_context() -> Optional[CorrelationContext]:
        """Get the current correlation context."""
        return getattr(_context_storage, "context", None)

    @staticmethod
    def set_correlation_id(correlation_id: str) -> None:
        """Set just the correlation ID for this thread (simple mode)."""
        _context_storage.correlation_id = correlation_id

    @staticmethod
    def set_context(context: CorrelationContext):
        """Set the full correlation context for the current thread."""
        _context_storage.context = context
        _context_storage.correlation_id = context.correlation_id

        logger.debug(
            f"Correlation context set (correlation_id={context.correlation_id}, "
            f"operation={context.operation}, provider={context.provider})"
        )

    @staticmethod
    def clear_context():
        """Clear the correlation context for the current thread."""
        correlation_id = getattr(_context_storage, "correlation_id", None)
        if hasattr(_context_storage, "context"):
            delattr(_context_storage, "context")
        if hasattr(_context_storage, "correlation_id"):
            delattr(_context_storage, "correlation_id")

        if correlation_id:
            logger.debug(
                f"Correlation context cleared (correlation_id={correlation_id})"
            )

    @staticmethod
    @contextmanager
    def correlation_context(
        correlation_id: Optional[str] = None,
        operation: Optional[str] = None,
        provider: Optional[str] = None,
        **metadata,
    ):
        """
        Context manager for correlation ID management.

        Args:
            correlation_id: Specific correlation ID (generates new if None)
            operation: Name of the operation being performed
            provider: Data provider name
            **metadata: Additional metadata for the context
        """
        # Generate ID if not provided
        if correlation_id is None:
            correlation_id = CorrelationIdManager.generate_id()

        # Get parent context if exists
        parent_context = CorrelationIdManager.get_current_context()
        parent_id = parent_context.correlation_id if parent_context else None

        # Create new context
        context = CorrelationContext(
            correlation_id=correlation_id,
            parent_id=parent_id,
            operation=operation,
            provider=provider,
            metadata=metadata,
        )

        # Store previous context to restore later
        previous_context = getattr(_context_storage, "context", None)
        previous_id = getattr(_context_storage, "correlation_id", None)

        try:
            # Set new context
            CorrelationIdManager.set_context(context)
            _log_with_context(
                "info",
                "Operation started",
                correlation_id=correlation_id,
                parent_id=parent_id,
                operation=operation,
                provider=provider,
            )

            yield context

            # Log successful completion
            elapsed = context.elapsed_seconds()
            _log_with_context(
                "info",
                "Operation completed successfully",
                correlation_id=correlation_id,
                operation=operation,
                elapsed_seconds=elapsed,
            )

        except Exception as e:
            # Log error with context
            elapsed = context.elapsed_seconds()
            _log_with_context(
                "error",
                "Operation failed",
                correlation_id=correlation_id,
                operation=operation,
                exception_type=type(e).__name__,
                exception_message=str(e),
                elapsed_seconds=elapsed,
            )

            # Add correlation ID to exception if it supports it
            if hasattr(e, "correlation_id"):
                e.correlation_id = correlation_id
            if hasattr(e, "add_context"):
                e.add_context(
                    correlation_id=correlation_id,
                    operation=operation,
                    provider=provider,
                )

            raise

        finally:
            # Restore previous context
            if previous_context:
                _context_storage.context = previous_context
                _context_storage.correlation_id = previous_id
            else:
                CorrelationIdManager.clear_context()

    @staticmethod
    def add_context_metadata(**metadata):
        """Add metadata to the current correlation context."""
        context = CorrelationIdManager.get_current_context()
        if context:
            context.metadata.update(metadata)
            logger.debug(
                f"Added context metadata (correlation_id={context.correlation_id}, metadata={metadata})"
            )


class RequestTracker:
    """
    Helper class for tracking request metrics and performance.

    Works with correlation context to provide detailed request analytics
    and performance monitoring across the system.
    """

    def __init__(self):
        self._requests: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def start_request(self, correlation_id: str, operation: str, **metadata):
        """Start tracking a request."""
        with self._lock:
            self._requests[correlation_id] = {
                "operation": operation,
                "start_time": datetime.now(timezone.utc),
                "metadata": metadata,
                "status": "in_progress",
            }

    def complete_request(
        self, correlation_id: str, success: bool = True, **result_metadata
    ):
        """Mark a request as completed."""
        with self._lock:
            if correlation_id in self._requests:
                request = self._requests[correlation_id]
                request["end_time"] = datetime.now(timezone.utc)
                request["duration"] = (
                    request["end_time"] - request["start_time"]
                ).total_seconds()
                request["status"] = "success" if success else "failed"
                request["result_metadata"] = result_metadata

    def get_request_stats(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific request."""
        with self._lock:
            return self._requests.get(correlation_id)

    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently active requests."""
        with self._lock:
            return {
                cid: req
                for cid, req in self._requests.items()
                if req["status"] == "in_progress"
            }

    def cleanup_old_requests(self, max_age_hours: int = 24):
        """Clean up old request tracking data."""
        with self._lock:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            to_remove = [
                cid
                for cid, req in self._requests.items()
                if req.get("end_time", req["start_time"]) < cutoff_time
            ]

            for cid in to_remove:
                del self._requests[cid]

            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old request tracking records")


# Global request tracker instance
_request_tracker = RequestTracker()


def get_request_tracker() -> RequestTracker:
    """Get the global request tracker instance."""
    return _request_tracker
