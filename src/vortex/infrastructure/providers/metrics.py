"""
Provider metrics and observability system.

This module provides comprehensive metrics collection, performance tracking,
and observability features for data providers.
"""

import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""

    operation_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def finish(self, success: bool = True, error: Optional[Exception] = None):
        """Mark operation as finished."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.success = success

        if error:
            self.error_type = type(error).__name__
            self.error_message = str(error)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/export."""
        return {
            "operation": self.operation_name,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "correlation_id": self.correlation_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            **self.additional_data,
        }


@dataclass
class ProviderMetrics:
    """Comprehensive metrics for a data provider."""

    provider_name: str
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    total_duration_ms: float = 0.0
    average_duration_ms: float = 0.0
    min_duration_ms: float = float("inf")
    max_duration_ms: float = 0.0

    # Error breakdown
    error_counts: Dict[str, int] = field(default_factory=dict)

    # Recent operations (last 100)
    recent_operations: List[OperationMetrics] = field(default_factory=list)

    # Performance buckets (response time distribution)
    performance_buckets: Dict[str, int] = field(
        default_factory=lambda: {
            "<100ms": 0,
            "100-500ms": 0,
            "500ms-1s": 0,
            "1-5s": 0,
            "5-30s": 0,
            ">30s": 0,
        }
    )

    # Time window metrics (last hour)
    hourly_operations: int = 0
    hourly_failures: int = 0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update(self, operation: OperationMetrics):
        """Update metrics with a completed operation."""
        self.total_operations += 1

        if operation.success:
            self.successful_operations += 1
        else:
            self.failed_operations += 1
            if operation.error_type:
                self.error_counts[operation.error_type] = (
                    self.error_counts.get(operation.error_type, 0) + 1
                )

        # Update duration metrics
        if operation.duration_ms:
            self.total_duration_ms += operation.duration_ms
            self.average_duration_ms = self.total_duration_ms / self.total_operations
            self.min_duration_ms = min(self.min_duration_ms, operation.duration_ms)
            self.max_duration_ms = max(self.max_duration_ms, operation.duration_ms)

            # Update performance buckets
            self._update_performance_bucket(operation.duration_ms)

        # Update recent operations (keep last 100)
        self.recent_operations.append(operation)
        if len(self.recent_operations) > 100:
            self.recent_operations.pop(0)

        # Update hourly metrics
        self._update_hourly_metrics(operation)

    def _update_performance_bucket(self, duration_ms: float):
        """Update performance bucket based on duration."""
        if duration_ms < 100:
            self.performance_buckets["<100ms"] += 1
        elif duration_ms < 500:
            self.performance_buckets["100-500ms"] += 1
        elif duration_ms < 1000:
            self.performance_buckets["500ms-1s"] += 1
        elif duration_ms < 5000:
            self.performance_buckets["1-5s"] += 1
        elif duration_ms < 30000:
            self.performance_buckets["5-30s"] += 1
        else:
            self.performance_buckets[">30s"] += 1

    def _update_hourly_metrics(self, operation: OperationMetrics):
        """Update hourly metrics, resetting if an hour has passed."""
        now = datetime.now(timezone.utc)

        # Reset hourly metrics if an hour has passed
        if now - self.last_reset > timedelta(hours=1):
            self.hourly_operations = 0
            self.hourly_failures = 0
            self.last_reset = now

        self.hourly_operations += 1
        if not operation.success:
            self.hourly_failures += 1

    @property
    def success_rate(self) -> float:
        """Calculate success rate as a percentage."""
        if self.total_operations == 0:
            return 100.0
        return (self.successful_operations / self.total_operations) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate as a percentage."""
        return 100.0 - self.success_rate

    @property
    def hourly_success_rate(self) -> float:
        """Calculate hourly success rate as a percentage."""
        if self.hourly_operations == 0:
            return 100.0
        return (
            (self.hourly_operations - self.hourly_failures) / self.hourly_operations
        ) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for export."""
        return {
            "provider": self.provider_name,
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "average_duration_ms": self.average_duration_ms,
            "min_duration_ms": (
                self.min_duration_ms if self.min_duration_ms != float("inf") else 0
            ),
            "max_duration_ms": self.max_duration_ms,
            "error_counts": self.error_counts,
            "performance_buckets": self.performance_buckets,
            "hourly_operations": self.hourly_operations,
            "hourly_failures": self.hourly_failures,
            "hourly_success_rate": self.hourly_success_rate,
        }


class ProviderMetricsCollector:
    """Thread-safe metrics collector for provider operations."""

    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.metrics = ProviderMetrics(provider_name)
        self._lock = threading.RLock()
        self._active_operations: Dict[str, OperationMetrics] = {}

    @contextmanager
    def track_operation(
        self,
        operation_name: str,
        correlation_id: Optional[str] = None,
        **additional_data,
    ):
        """Context manager to track an operation's performance.

        Args:
            operation_name: Name of the operation being tracked
            correlation_id: Optional correlation ID for tracing
            **additional_data: Additional data to include in metrics

        Usage:
            with collector.track_operation('fetch_data', correlation_id='abc123', symbol='AAPL'):
                # Perform operation
                result = fetch_data()
        """
        operation = OperationMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            correlation_id=correlation_id,
            additional_data=additional_data,
        )

        operation_id = f"{operation_name}_{id(operation)}"

        with self._lock:
            self._active_operations[operation_id] = operation

        try:
            yield operation
            operation.finish(success=True)

        except Exception as e:
            operation.finish(success=False, error=e)
            raise

        finally:
            with self._lock:
                self._active_operations.pop(operation_id, None)
                self.metrics.update(operation)

    def record_operation(
        self,
        operation_name: str,
        duration_ms: float,
        success: bool = True,
        error: Optional[Exception] = None,
        correlation_id: Optional[str] = None,
        **additional_data,
    ):
        """Manually record a completed operation.

        Args:
            operation_name: Name of the operation
            duration_ms: Duration in milliseconds
            success: Whether the operation succeeded
            error: Optional error if operation failed
            correlation_id: Optional correlation ID for tracing
            **additional_data: Additional data to include in metrics
        """
        operation = OperationMetrics(
            operation_name=operation_name,
            start_time=time.time() - (duration_ms / 1000),
            correlation_id=correlation_id,
            additional_data=additional_data,
        )
        operation.finish(success=success, error=error)

        with self._lock:
            self.metrics.update(operation)

    def get_metrics(self) -> ProviderMetrics:
        """Get current metrics (thread-safe copy)."""
        with self._lock:
            # Return a copy to avoid modification issues
            import copy

            return copy.deepcopy(self.metrics)

    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get currently active operations."""
        with self._lock:
            return [
                {
                    "operation": op.operation_name,
                    "start_time": op.start_time,
                    "duration_so_far_ms": (time.time() - op.start_time) * 1000,
                    "correlation_id": op.correlation_id,
                    **op.additional_data,
                }
                for op in self._active_operations.values()
            ]

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.metrics = ProviderMetrics(self.provider_name)
            self._active_operations.clear()

    def get_health_score(self) -> float:
        """Calculate a health score based on recent performance.

        Returns:
            Health score from 0-100, where 100 is perfect health
        """
        with self._lock:
            metrics = self.metrics

            # Base score on success rate
            base_score = (
                metrics.hourly_success_rate
                if metrics.hourly_operations > 0
                else metrics.success_rate
            )

            # Apply penalties for poor performance
            if metrics.average_duration_ms > 10000:  # > 10 seconds
                base_score *= 0.7
            elif metrics.average_duration_ms > 5000:  # > 5 seconds
                base_score *= 0.85
            elif metrics.average_duration_ms > 2000:  # > 2 seconds
                base_score *= 0.95

            # Penalty for high error rates in specific error types
            critical_errors = [
                "ConnectionError",
                "AuthenticationError",
                "DataProviderError",
            ]
            for error_type in critical_errors:
                if (
                    error_type in metrics.error_counts
                    and metrics.error_counts[error_type] > 3
                ):
                    base_score *= 0.8

            return max(0.0, min(100.0, base_score))


# Global registry for provider metrics collectors
_metrics_registry: Dict[str, ProviderMetricsCollector] = {}
_registry_lock = threading.RLock()


def get_metrics_collector(provider_name: str) -> ProviderMetricsCollector:
    """Get or create a metrics collector for a provider.

    Args:
        provider_name: Name of the provider

    Returns:
        ProviderMetricsCollector instance for the provider
    """
    with _registry_lock:
        if provider_name not in _metrics_registry:
            _metrics_registry[provider_name] = ProviderMetricsCollector(provider_name)
        return _metrics_registry[provider_name]


def get_all_metrics() -> Dict[str, ProviderMetrics]:
    """Get metrics for all registered providers.

    Returns:
        Dictionary mapping provider names to their metrics
    """
    with _registry_lock:
        return {
            name: collector.get_metrics()
            for name, collector in _metrics_registry.items()
        }


def reset_all_metrics():
    """Reset metrics for all providers (useful for testing)."""
    with _registry_lock:
        for collector in _metrics_registry.values():
            collector.reset_metrics()
