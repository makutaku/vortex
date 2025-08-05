"""
Comprehensive Error Recovery Strategies.

Provides intelligent error recovery mechanisms including provider fallback,
graceful degradation, and system protection patterns.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, List, Optional, Dict, Union
import time
import threading

from vortex.shared.exceptions import (
    VortexError, DataProviderError, AuthenticationError,
    ConnectionError, RateLimitError, DataNotFoundError,
    AllowanceLimitExceededError
)
# Optional logging - graceful fallback if not available
try:
    from vortex.shared.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from .circuit_breaker import CircuitBreaker, get_circuit_breaker
from .correlation import CorrelationIdManager, with_correlation


class RecoveryStrategy(Enum):
    """Available recovery strategies."""
    IMMEDIATE_RETRY = "immediate_retry"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    PROVIDER_FALLBACK = "provider_fallback"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    CIRCUIT_BREAKER = "circuit_breaker"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class RecoveryAction:
    """Represents a recovery action to be taken."""
    strategy: RecoveryStrategy
    delay: float = 0.0
    fallback_provider: Optional[str] = None
    degraded_operation: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    
@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""
    success: bool
    strategy_used: RecoveryStrategy
    attempts_made: int
    total_time: float
    final_exception: Optional[Exception] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RecoveryPolicy(ABC):
    """Abstract base class for recovery policies."""
    
    @abstractmethod
    def analyze_error(self, exception: Exception, context: Dict[str, Any]) -> List[RecoveryAction]:
        """Analyze an error and return possible recovery actions."""
        pass
    
    @abstractmethod
    def should_attempt_recovery(self, exception: Exception, attempt_count: int) -> bool:
        """Determine if recovery should be attempted."""
        pass


class DataProviderRecoveryPolicy(RecoveryPolicy):
    """Recovery policy specifically for data provider errors."""
    
    def __init__(self, max_retry_attempts: int = 3, fallback_providers: Optional[List[str]] = None):
        self.max_retry_attempts = max_retry_attempts
        self.fallback_providers = fallback_providers or []
    
    def analyze_error(self, exception: Exception, context: Dict[str, Any]) -> List[RecoveryAction]:
        """Analyze provider error and suggest recovery actions."""
        actions = []
        
        if isinstance(exception, AuthenticationError):
            # Authentication errors require manual intervention
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.MANUAL_INTERVENTION,
                metadata={'reason': 'Invalid credentials require user action'}
            ))
            
        elif isinstance(exception, RateLimitError):
            # Rate limit errors need backoff
            wait_time = getattr(exception, 'wait_time', 60)
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
                delay=wait_time,
                metadata={'rate_limit_wait': wait_time}
            ))
            
            # Also try fallback providers
            for provider in self.fallback_providers:
                actions.append(RecoveryAction(
                    strategy=RecoveryStrategy.PROVIDER_FALLBACK,
                    fallback_provider=provider
                ))
                
        elif isinstance(exception, ConnectionError):
            # Connection errors can be retried with backoff
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
                delay=5.0,
                metadata={'reason': 'Network connectivity issue'}
            ))
            
            # Try fallback providers
            for provider in self.fallback_providers:
                actions.append(RecoveryAction(
                    strategy=RecoveryStrategy.PROVIDER_FALLBACK,
                    fallback_provider=provider
                ))
                
        elif isinstance(exception, DataNotFoundError):
            # Data not found might be available from other providers
            for provider in self.fallback_providers:
                actions.append(RecoveryAction(
                    strategy=RecoveryStrategy.PROVIDER_FALLBACK,
                    fallback_provider=provider,
                    metadata={'reason': 'Data not available from primary provider'}
                ))
                
        elif isinstance(exception, AllowanceLimitExceededError):
            # Quota exceeded - try fallback providers
            for provider in self.fallback_providers:
                actions.append(RecoveryAction(
                    strategy=RecoveryStrategy.PROVIDER_FALLBACK,
                    fallback_provider=provider,
                    metadata={'reason': 'Primary provider quota exceeded'}
                ))
                
        elif isinstance(exception, DataProviderError):
            # Generic provider error - try exponential backoff first
            actions.append(RecoveryAction(
                strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
                delay=2.0
            ))
            
            # Then try fallback providers
            for provider in self.fallback_providers:
                actions.append(RecoveryAction(
                    strategy=RecoveryStrategy.PROVIDER_FALLBACK,
                    fallback_provider=provider
                ))
        
        return actions
    
    def should_attempt_recovery(self, exception: Exception, attempt_count: int) -> bool:
        """Determine if recovery should be attempted based on error type and attempts."""
        # Don't retry beyond max attempts
        if attempt_count >= self.max_retry_attempts:
            return False
            
        # Some errors should not be retried
        if isinstance(exception, (AuthenticationError, DataNotFoundError)):
            # Only allow fallback, not retry of same operation
            return attempt_count == 0
            
        return True


class ErrorRecoveryManager:
    """
    Comprehensive error recovery manager.
    
    Orchestrates error recovery using multiple strategies and policies.
    """
    
    def __init__(self, recovery_policy: Optional[RecoveryPolicy] = None):
        self.recovery_policy = recovery_policy or DataProviderRecoveryPolicy()
        self._recovery_stats: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        
        logger.info("ErrorRecoveryManager initialized",
                   policy_type=type(self.recovery_policy).__name__)
    
    @with_correlation(operation='error_recovery')
    def attempt_recovery(
        self,
        operation: Callable,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs
    ) -> RecoveryResult:
        """
        Attempt to recover from an error using available strategies.
        
        Args:
            operation: The operation that failed
            exception: The exception that occurred
            context: Additional context about the failure
            *args, **kwargs: Arguments for the operation
            
        Returns:
            RecoveryResult with details of the recovery attempt
        """
        start_time = time.time()
        context = context or {}
        operation_name = getattr(operation, '__name__', 'unknown_operation')
        
        logger.warning("Starting error recovery",
                      operation=operation_name,
                      exception_type=type(exception).__name__,
                      exception_message=str(exception))
        
        # Analyze the error and get recovery actions
        recovery_actions = self.recovery_policy.analyze_error(exception, context)
        
        if not recovery_actions:
            logger.info("No recovery actions available for error",
                       exception_type=type(exception).__name__)
            return RecoveryResult(
                success=False,
                strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
                attempts_made=0,
                total_time=time.time() - start_time,
                final_exception=exception
            )
        
        # Try recovery actions in order
        attempt_count = 0
        final_exception = exception
        
        for action in recovery_actions:
            if not self.recovery_policy.should_attempt_recovery(exception, attempt_count):
                logger.info("Recovery policy indicates no more attempts should be made",
                           attempt_count=attempt_count)
                break
                
            attempt_count += 1
            
            try:
                result = self._execute_recovery_action(
                    action, operation, context, *args, **kwargs
                )
                
                # Recovery successful
                total_time = time.time() - start_time
                logger.info("Error recovery successful",
                           strategy=action.strategy.value,
                           attempt_count=attempt_count,
                           total_time=total_time)
                
                self._record_recovery_stats(operation_name, action.strategy, True, total_time)
                
                return RecoveryResult(
                    success=True,
                    strategy_used=action.strategy,
                    attempts_made=attempt_count,
                    total_time=total_time,
                    metadata=action.metadata
                )
                
            except Exception as e:
                final_exception = e
                logger.warning("Recovery attempt failed",
                              strategy=action.strategy.value,
                              attempt_count=attempt_count,
                              exception_type=type(e).__name__)
                continue
        
        # All recovery attempts failed
        total_time = time.time() - start_time
        logger.error("All recovery attempts failed",
                    operation=operation_name,
                    attempts_made=attempt_count,
                    total_time=total_time,
                    final_exception_type=type(final_exception).__name__)
        
        self._record_recovery_stats(operation_name, RecoveryStrategy.MANUAL_INTERVENTION, False, total_time)
        
        return RecoveryResult(
            success=False,
            strategy_used=RecoveryStrategy.MANUAL_INTERVENTION,
            attempts_made=attempt_count,
            total_time=total_time,
            final_exception=final_exception
        )
    
    def _execute_recovery_action(
        self,
        action: RecoveryAction,
        operation: Callable,
        context: Dict[str, Any],
        *args,
        **kwargs
    ) -> Any:
        """Execute a specific recovery action."""
        logger.debug("Executing recovery action",
                    strategy=action.strategy.value,
                    delay=action.delay,
                    metadata=action.metadata)
        
        if action.strategy == RecoveryStrategy.IMMEDIATE_RETRY:
            return operation(*args, **kwargs)
        
        elif action.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            if action.delay > 0:
                logger.debug(f"Waiting {action.delay} seconds before retry")
                time.sleep(action.delay)
            return operation(*args, **kwargs)
        
        elif action.strategy == RecoveryStrategy.PROVIDER_FALLBACK:
            if action.fallback_provider:
                logger.info("Attempting provider fallback",
                           fallback_provider=action.fallback_provider)
                # Modify context to use fallback provider
                new_context = context.copy()
                new_context['provider'] = action.fallback_provider
                
                # Update kwargs if they contain provider information
                if 'provider' in kwargs:
                    kwargs = kwargs.copy()
                    kwargs['provider'] = action.fallback_provider
                
                return operation(*args, **kwargs)
            else:
                raise ValueError("Fallback provider not specified")
        
        elif action.strategy == RecoveryStrategy.GRACEFUL_DEGRADATION:
            if action.degraded_operation:
                logger.info("Using degraded operation")
                return action.degraded_operation(*args, **kwargs)
            else:
                raise ValueError("Degraded operation not specified")
        
        elif action.strategy == RecoveryStrategy.CIRCUIT_BREAKER:
            # Use circuit breaker for the operation
            circuit_name = context.get('provider', 'default')
            circuit_breaker = get_circuit_breaker(circuit_name)
            return circuit_breaker.call(operation, *args, **kwargs)
        
        elif action.strategy == RecoveryStrategy.MANUAL_INTERVENTION:
            raise ManualInterventionRequiredException(
                f"Manual intervention required: {action.metadata.get('reason', 'Unknown error')}"
            )
        
        else:
            raise ValueError(f"Unknown recovery strategy: {action.strategy}")
    
    def _record_recovery_stats(
        self,
        operation: str,
        strategy: RecoveryStrategy,
        success: bool,
        duration: float
    ):
        """Record statistics about recovery attempts."""
        with self._lock:
            if operation not in self._recovery_stats:
                self._recovery_stats[operation] = {
                    'total_attempts': 0,
                    'successful_recoveries': 0,
                    'failed_recoveries': 0,
                    'strategies_used': {},
                    'total_recovery_time': 0.0,
                    'last_recovery': None
                }
            
            stats = self._recovery_stats[operation]
            stats['total_attempts'] += 1
            stats['total_recovery_time'] += duration
            stats['last_recovery'] = datetime.now().isoformat()
            
            if success:
                stats['successful_recoveries'] += 1
            else:
                stats['failed_recoveries'] += 1
            
            strategy_name = strategy.value
            if strategy_name not in stats['strategies_used']:
                stats['strategies_used'][strategy_name] = {'attempts': 0, 'successes': 0}
            
            stats['strategies_used'][strategy_name]['attempts'] += 1
            if success:
                stats['strategies_used'][strategy_name]['successes'] += 1
    
    def get_recovery_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get recovery statistics."""
        with self._lock:
            return self._recovery_stats.copy()
    
    def reset_stats(self):
        """Reset recovery statistics."""
        with self._lock:
            self._recovery_stats.clear()
            logger.info("Recovery statistics reset")


class ManualInterventionRequiredException(VortexError):
    """Raised when manual intervention is required to resolve an error."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            help_text="This error requires manual intervention to resolve",
            error_code="MANUAL_INTERVENTION_REQUIRED",
            **kwargs
        )


def with_error_recovery(
    recovery_policy: Optional[RecoveryPolicy] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator to add error recovery to a function.
    
    Args:
        recovery_policy: Custom recovery policy to use
        context: Additional context for recovery decisions
    """
    def decorator(func: Callable) -> Callable:
        recovery_manager = ErrorRecoveryManager(recovery_policy)
        
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Attempt recovery
                recovery_result = recovery_manager.attempt_recovery(
                    func, e, context, *args, **kwargs
                )
                
                if recovery_result.success:
                    # Recovery successful - we should have a result
                    # This would need to be implemented based on specific recovery logic
                    logger.info("Function execution recovered successfully")
                    return None  # Placeholder - actual implementation would return result
                else:
                    # Recovery failed - re-raise the final exception
                    raise recovery_result.final_exception
        
        return wrapper
    return decorator