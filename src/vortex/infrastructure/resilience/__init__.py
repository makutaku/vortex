"""
Resilience and error recovery patterns for Vortex.

This module provides advanced error handling, retry mechanisms, and resilience
patterns to ensure robust operation in the face of network failures, API issues,
and other transient problems.
"""

from vortex.core.correlation import CorrelationIdManager

from .circuit_breaker import CircuitBreaker, CircuitState
from .recovery import ErrorRecoveryManager, RecoveryStrategy
from .retry import ExponentialBackoffStrategy, RetryManager, RetryPolicy

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "RetryManager",
    "ExponentialBackoffStrategy",
    "RetryPolicy",
    "ErrorRecoveryManager",
    "RecoveryStrategy",
    "CorrelationIdManager",
]
