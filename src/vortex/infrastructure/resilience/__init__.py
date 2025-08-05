"""
Resilience and error recovery patterns for Vortex.

This module provides advanced error handling, retry mechanisms, and resilience
patterns to ensure robust operation in the face of network failures, API issues,
and other transient problems.
"""

from .circuit_breaker import CircuitBreaker, CircuitState
from .retry import RetryManager, ExponentialBackoffStrategy, RetryPolicy
from .recovery import ErrorRecoveryManager, RecoveryStrategy
from vortex.core.correlation import CorrelationIdManager

__all__ = [
    'CircuitBreaker',
    'CircuitState', 
    'RetryManager',
    'ExponentialBackoffStrategy',
    'RetryPolicy',
    'ErrorRecoveryManager',
    'RecoveryStrategy',
    'CorrelationIdManager'
]