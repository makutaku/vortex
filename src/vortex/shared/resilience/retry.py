"""
Advanced Retry Mechanisms with Exponential Backoff and Jitter.

Provides sophisticated retry logic with configurable backoff strategies,
jitter for avoiding thundering herd problems, and intelligent exception
handling for different error types.
"""

import random
import time
import functools
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, Type, Tuple, Union, List
from abc import ABC, abstractmethod

from vortex.shared.exceptions import (
    VortexError, DataProviderError, AuthenticationError, 
    RateLimitError, ConnectionError, DataNotFoundError,
    AllowanceLimitExceededError
)
# Optional logging - graceful fallback if not available
try:
    from vortex.shared.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Available retry strategies."""
    FIXED_DELAY = "fixed_delay"
    LINEAR_BACKOFF = "linear_backoff"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    EXPONENTIAL_BACKOFF_JITTER = "exponential_backoff_jitter"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF_JITTER
    base_delay: float = 1.0           # Base delay in seconds
    max_delay: float = 60.0           # Maximum delay in seconds
    multiplier: float = 2.0           # Exponential multiplier
    jitter_max: float = 0.1           # Maximum jitter (fraction of delay)
    
    # Exception-specific behavior
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError,
        RateLimitError,
        DataProviderError,
    )
    
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (
        AuthenticationError,
        DataNotFoundError,
        AllowanceLimitExceededError,
    )
    
    # Rate limit specific handling
    rate_limit_backoff_multiplier: float = 1.5
    rate_limit_respect_retry_after: bool = True


class BackoffStrategy(ABC):
    """Abstract base class for backoff strategies."""
    
    @abstractmethod
    def calculate_delay(self, attempt: int, base_delay: float, max_delay: float, **kwargs) -> float:
        """Calculate delay for given attempt number."""
        pass


class FixedDelayStrategy(BackoffStrategy):
    """Fixed delay between retries."""
    
    def calculate_delay(self, attempt: int, base_delay: float, max_delay: float, **kwargs) -> float:
        return min(base_delay, max_delay)


class LinearBackoffStrategy(BackoffStrategy):
    """Linear increase in delay."""
    
    def calculate_delay(self, attempt: int, base_delay: float, max_delay: float, **kwargs) -> float:
        delay = base_delay * attempt
        return min(delay, max_delay)


class ExponentialBackoffStrategy(BackoffStrategy):
    """Exponential backoff with optional jitter."""
    
    def __init__(self, multiplier: float = 2.0, jitter: bool = False, jitter_max: float = 0.1):
        self.multiplier = multiplier
        self.jitter = jitter
        self.jitter_max = jitter_max
    
    def calculate_delay(self, attempt: int, base_delay: float, max_delay: float, **kwargs) -> float:
        # Calculate exponential delay
        delay = base_delay * (self.multiplier ** (attempt - 1))
        delay = min(delay, max_delay)
        
        # Add jitter if enabled
        if self.jitter and delay > 0:
            jitter_amount = delay * self.jitter_max * random.random()
            delay += jitter_amount
        
        return delay


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    delay: float
    exception: Optional[Exception]
    timestamp: datetime
    total_elapsed: float


class RetryManager:
    """
    Advanced retry manager with intelligent backoff strategies.
    
    Provides configurable retry logic with different backoff strategies,
    exception-specific handling, and comprehensive logging.
    """
    
    def __init__(self, policy: Optional[RetryPolicy] = None):
        self.policy = policy or RetryPolicy()
        self.strategy_map = {
            RetryStrategy.FIXED_DELAY: FixedDelayStrategy(),
            RetryStrategy.LINEAR_BACKOFF: LinearBackoffStrategy(), 
            RetryStrategy.EXPONENTIAL_BACKOFF: ExponentialBackoffStrategy(
                multiplier=self.policy.multiplier,
                jitter=False
            ),
            RetryStrategy.EXPONENTIAL_BACKOFF_JITTER: ExponentialBackoffStrategy(
                multiplier=self.policy.multiplier,
                jitter=True,
                jitter_max=self.policy.jitter_max
            )
        }
        
        logger.debug("RetryManager initialized",
                    max_attempts=self.policy.max_attempts,
                    strategy=self.policy.strategy.value,
                    base_delay=self.policy.base_delay)
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to add retry logic to a function."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return self.execute_with_retry(func, *args, **kwargs)
        return wrapper
    
    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function with retry logic.
        
        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            Last exception if all retries exhausted
        """
        start_time = time.time()
        last_exception = None
        attempts: List[RetryAttempt] = []
        
        for attempt in range(1, self.policy.max_attempts + 1):
            try:
                logger.debug(f"Executing function {func.__name__}, attempt {attempt}")
                result = func(*args, **kwargs)
                
                # Success - log and return
                total_elapsed = time.time() - start_time
                if attempt > 1:
                    logger.info(f"Function {func.__name__} succeeded after {attempt} attempts",
                              total_elapsed=total_elapsed,
                              attempts=len(attempts))
                
                return result
                
            except Exception as e:
                last_exception = e
                total_elapsed = time.time() - start_time
                
                # Check if this exception should be retried
                if not self._should_retry(e, attempt):
                    logger.info(f"Not retrying {func.__name__} due to non-retryable exception",
                              exception_type=type(e).__name__,
                              attempt=attempt)
                    raise
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, e)
                
                # Record this attempt
                retry_attempt = RetryAttempt(
                    attempt_number=attempt,
                    delay=delay,
                    exception=e,
                    timestamp=datetime.now(),
                    total_elapsed=total_elapsed
                )
                attempts.append(retry_attempt)
                
                # Log the failure and retry plan
                if attempt < self.policy.max_attempts:
                    logger.warning(f"Function {func.__name__} failed, retrying",
                                 exception_type=type(e).__name__,
                                 attempt=attempt,
                                 max_attempts=self.policy.max_attempts,
                                 delay=delay,
                                 correlation_id=getattr(e, 'correlation_id', None))
                    
                    # Wait before retry
                    if delay > 0:
                        time.sleep(delay)
                else:
                    # Final attempt failed
                    logger.error(f"Function {func.__name__} failed after all retry attempts",
                               exception_type=type(e).__name__,
                               max_attempts=self.policy.max_attempts,
                               total_elapsed=total_elapsed)
        
        # All retries exhausted - raise the last exception
        if last_exception:
            # Enhance exception with retry context
            if hasattr(last_exception, '__dict__'):
                last_exception.retry_attempts = len(attempts)
                last_exception.total_retry_time = time.time() - start_time
            
            raise last_exception
        
        # This should never happen, but just in case
        raise RuntimeError(f"All retry attempts failed for {func.__name__}")
    
    def _should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an exception should trigger a retry."""
        # Don't retry if we've exhausted attempts
        if attempt >= self.policy.max_attempts:
            return False
        
        # Check non-retryable exceptions first
        if isinstance(exception, self.policy.non_retryable_exceptions):
            return False
        
        # Check retryable exceptions
        if isinstance(exception, self.policy.retryable_exceptions):
            return True
        
        # For VortexError, check if it's a known retryable type
        if isinstance(exception, VortexError):
            # Rate limits are retryable with special handling
            if isinstance(exception, RateLimitError):
                return True
            # Connection errors are retryable
            if isinstance(exception, ConnectionError):
                return True
            # Generic data provider errors might be retryable
            if isinstance(exception, DataProviderError):
                return True
        
        # Default: don't retry unknown exceptions
        logger.debug(f"Exception not configured for retry: {type(exception).__name__}")
        return False
    
    def _calculate_delay(self, attempt: int, exception: Optional[Exception] = None) -> float:
        """Calculate delay before next retry attempt."""
        # Special handling for rate limit errors
        if isinstance(exception, RateLimitError) and self.policy.rate_limit_respect_retry_after:
            # If the exception provides a wait time, use it (with some buffer)
            if hasattr(exception, 'wait_time') and exception.wait_time:
                delay = exception.wait_time * self.policy.rate_limit_backoff_multiplier
                return min(delay, self.policy.max_delay)
        
        # Use configured backoff strategy
        strategy = self.strategy_map[self.policy.strategy]
        delay = strategy.calculate_delay(
            attempt=attempt,
            base_delay=self.policy.base_delay,
            max_delay=self.policy.max_delay,
            multiplier=self.policy.multiplier
        )
        
        return delay


class ProviderRetryManager(RetryManager):
    """
    Specialized retry manager for data providers.
    
    Includes provider-specific retry policies and error handling.
    """
    
    def __init__(self, provider_name: str, custom_policy: Optional[RetryPolicy] = None):
        self.provider_name = provider_name
        
        # Provider-specific retry policies
        provider_policies = {
            'barchart': RetryPolicy(
                max_attempts=5,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF_JITTER,
                base_delay=2.0,
                max_delay=120.0,
                rate_limit_backoff_multiplier=2.0
            ),
            'yahoo': RetryPolicy(
                max_attempts=3,
                strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
                base_delay=1.0,
                max_delay=30.0
            ),
            'ibkr': RetryPolicy(
                max_attempts=4,
                strategy=RetryStrategy.LINEAR_BACKOFF,
                base_delay=1.5,
                max_delay=60.0
            )
        }
        
        # Use custom policy or provider-specific or default
        policy = custom_policy or provider_policies.get(provider_name.lower()) or RetryPolicy()
        super().__init__(policy)
        
        logger.info(f"ProviderRetryManager initialized for {provider_name}",
                   max_attempts=self.policy.max_attempts,
                   strategy=self.policy.strategy.value)


def retry_with_backoff(
    max_attempts: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF_JITTER,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
) -> Callable:
    """
    Decorator for adding retry logic with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        strategy: Backoff strategy to use
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        **kwargs: Additional policy parameters
        
    Returns:
        Decorator function
    """
    policy = RetryPolicy(
        max_attempts=max_attempts,
        strategy=strategy,
        base_delay=base_delay,
        max_delay=max_delay,
        **kwargs
    )
    
    retry_manager = RetryManager(policy)
    return retry_manager


def provider_retry(provider_name: str, **kwargs) -> Callable:
    """
    Decorator for adding provider-specific retry logic.
    
    Args:
        provider_name: Name of the data provider
        **kwargs: Override policy parameters
        
    Returns:
        Decorator function
    """
    # Build custom policy from kwargs if provided
    custom_policy = None
    if kwargs:
        custom_policy = RetryPolicy(**kwargs)
    
    retry_manager = ProviderRetryManager(provider_name, custom_policy)
    return retry_manager