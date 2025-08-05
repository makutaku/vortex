"""
Performance logging and metrics tracking.

Provides performance measurement tools and timing decorators.
"""

import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Dict, Optional
from uuid import uuid4

from .loggers import VortexLogger, get_logger


class PerformanceLogger:
    """Logger specialized for performance metrics and timing."""
    
    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.logger = get_logger(f"{name}.performance", correlation_id)
    
    def time_operation(self, operation: str, duration_ms: float, **context):
        """Log operation timing."""
        self.logger.info(
            f"Operation '{operation}' completed in {duration_ms:.2f}ms",
            operation=operation,
            duration=duration_ms,
            **context
        )
    
    def start_operation(self, operation: str, **context) -> 'TimedOperation':
        """Start timing an operation."""
        return TimedOperation(operation, self.logger, context)


class TimedOperation:
    """Context manager for timing operations with automatic logging."""
    
    def __init__(self, operation: str, logger: VortexLogger, context: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.logger = logger
        self.context = context or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        self.logger.debug(f"Starting operation: {self.operation}", **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is None:
            return
        
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        
        if exc_type is None:
            self.logger.info(
                f"Completed operation: {self.operation} in {duration_ms:.2f}ms",
                operation=self.operation,
                duration=duration_ms,
                status="success",
                **self.context
            )
        else:
            self.logger.error(
                f"Failed operation: {self.operation} after {duration_ms:.2f}ms: {exc_val}",
                operation=self.operation,
                duration=duration_ms,
                status="failed",
                error_type=exc_type.__name__,
                **self.context
            )


def get_performance_logger(name: str, correlation_id: Optional[str] = None) -> PerformanceLogger:
    """Get a PerformanceLogger instance."""
    return PerformanceLogger(name, correlation_id)


def timed(operation: Optional[str] = None, logger: Optional[VortexLogger] = None):
    """Decorator to time function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or f"{func.__module__}.{func.__name__}"
            perf_logger = logger or get_logger(f"{func.__module__}.performance")
            
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000
                perf_logger.info(
                    f"Function '{op_name}' completed in {duration_ms:.2f}ms",
                    operation=op_name,
                    duration=duration_ms,
                    status="success"
                )
                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                perf_logger.error(
                    f"Function '{op_name}' failed after {duration_ms:.2f}ms: {e}",
                    operation=op_name,
                    duration=duration_ms,
                    status="failed",
                    error_type=type(e).__name__
                )
                raise
        return wrapper
    return decorator