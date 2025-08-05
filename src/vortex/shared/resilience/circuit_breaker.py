"""
Circuit Breaker Pattern Implementation.

Provides failure isolation by monitoring error rates and temporarily disabling
failing services to prevent cascading failures.
"""

import time
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional, Dict, List
from collections import deque

from vortex.shared.exceptions import DataProviderError, ConnectionError, RateLimitError

# Optional logging - graceful fallback if not available
try:
    from vortex.shared.logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"           # Failing, requests blocked
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5          # Failures before opening circuit
    recovery_timeout: int = 60          # Seconds before trying half-open
    success_threshold: int = 3          # Successes to close from half-open
    timeout: int = 30                   # Request timeout in seconds
    monitored_exceptions: tuple = (
        ConnectionError, 
        DataProviderError
    )
    
    # Advanced configuration
    sliding_window_size: int = 100      # Size of failure tracking window
    minimum_calls: int = 10             # Minimum calls before evaluation


@dataclass
class CallResult:
    """Result of a circuit breaker call."""
    timestamp: datetime
    success: bool
    duration: float
    exception: Optional[Exception] = None


class CircuitBreaker:
    """
    Circuit breaker implementation with sliding window failure tracking.
    
    Monitors service calls and opens the circuit when failure rates exceed
    thresholds, preventing cascading failures and allowing services to recover.
    """
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # Circuit state management
        self._state = CircuitState.CLOSED
        self._state_lock = threading.RLock()
        
        # Failure tracking with sliding window
        self._call_results: deque = deque(maxlen=self.config.sliding_window_size)
        self._last_failure_time: Optional[datetime] = None
        self._failure_count = 0
        self._success_count = 0
        
        # Statistics
        self._total_calls = 0
        self._total_failures = 0
        self._circuit_opened_count = 0
        
        logger.info(f"Circuit breaker '{name}' initialized", 
                   failure_threshold=self.config.failure_threshold,
                   recovery_timeout=self.config.recovery_timeout)
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._state_lock:
            return self._state
    
    @property
    def failure_rate(self) -> float:
        """Calculate current failure rate from sliding window."""
        with self._state_lock:
            if len(self._call_results) < self.config.minimum_calls:
                return 0.0
            
            failures = sum(1 for result in self._call_results if not result.success)
            return failures / len(self._call_results)
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        with self._state_lock:
            return {
                'name': self.name,
                'state': self._state.value,
                'total_calls': self._total_calls,
                'total_failures': self._total_failures,
                'failure_rate': self.failure_rate,
                'circuit_opened_count': self._circuit_opened_count,
                'last_failure_time': self._last_failure_time.isoformat() if self._last_failure_time else None,
                'calls_in_window': len(self._call_results)
            }
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator to wrap function calls with circuit breaker."""
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function call through the circuit breaker.
        
        Args:
            func: Function to call
            *args, **kwargs: Arguments to pass to function
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenException: When circuit is open
            Original exception: When function fails
        """
        with self._state_lock:
            self._total_calls += 1
            
            # Check if circuit should allow the call
            if not self._should_allow_call():
                logger.warning(f"Circuit breaker '{self.name}' is OPEN, blocking call")
                raise CircuitOpenException(f"Circuit breaker '{self.name}' is open")
            
            # Execute the call
            start_time = time.time()
            call_success = False
            exception = None
            
            try:
                result = func(*args, **kwargs)
                call_success = True
                self._record_success()
                logger.debug(f"Circuit breaker '{self.name}' call succeeded", 
                           duration=time.time() - start_time)
                return result
                
            except Exception as e:
                exception = e
                call_success = False
                
                # Only record as failure if it's a monitored exception
                if isinstance(e, self.config.monitored_exceptions):
                    self._record_failure(e)
                    logger.warning(f"Circuit breaker '{self.name}' recorded failure",
                                 exception_type=type(e).__name__,
                                 failure_count=self._failure_count)
                else:
                    # Still record the call result but don't count as failure
                    self._record_call_result(True, time.time() - start_time)
                    logger.debug(f"Circuit breaker '{self.name}' non-monitored exception",
                               exception_type=type(e).__name__)
                
                raise
            
            finally:
                # Always record the call result
                duration = time.time() - start_time
                self._record_call_result(call_success, duration, exception)
    
    def _should_allow_call(self) -> bool:
        """Determine if the circuit should allow a call."""
        if self._state == CircuitState.CLOSED:
            return True
        
        elif self._state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if (self._last_failure_time and 
                datetime.now() - self._last_failure_time >= timedelta(seconds=self.config.recovery_timeout)):
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False
        
        elif self._state == CircuitState.HALF_OPEN:
            # Allow limited calls to test recovery
            return True
            
        return False
    
    def _record_success(self):
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
    
    def _record_failure(self, exception: Exception):
        """Record a failed call."""
        self._total_failures += 1
        self._failure_count += 1
        self._last_failure_time = datetime.now()
        
        # Check if we should open the circuit
        if (self._state == CircuitState.CLOSED and 
            self._failure_count >= self.config.failure_threshold):
            self._transition_to(CircuitState.OPEN)
        
        elif self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._transition_to(CircuitState.OPEN)
    
    def _record_call_result(self, success: bool, duration: float, exception: Optional[Exception] = None):
        """Record call result in sliding window."""
        result = CallResult(
            timestamp=datetime.now(),
            success=success,
            duration=duration,
            exception=exception
        )
        self._call_results.append(result)
    
    def _transition_to(self, new_state: CircuitState):
        """Transition circuit to new state."""
        old_state = self._state
        self._state = new_state
        
        if new_state == CircuitState.OPEN:
            self._circuit_opened_count += 1
            self._success_count = 0
            logger.warning(f"Circuit breaker '{self.name}' opened",
                         failure_count=self._failure_count,
                         failure_rate=self.failure_rate)
        
        elif new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
            logger.info(f"Circuit breaker '{self.name}' closed - service recovered")
        
        elif new_state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker '{self.name}' half-open - testing recovery")
        
        logger.info(f"Circuit breaker '{self.name}' state transition",
                   old_state=old_state.value,
                   new_state=new_state.value)
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        with self._state_lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._call_results.clear()
            logger.info(f"Circuit breaker '{self.name}' manually reset")
    
    def force_open(self):
        """Force circuit breaker to open state."""
        with self._state_lock:
            self._transition_to(CircuitState.OPEN)
            logger.warning(f"Circuit breaker '{self.name}' manually opened")


class CircuitOpenException(Exception):
    """Raised when circuit breaker is open and blocking calls."""
    pass


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Provides centralized management and monitoring of circuit breakers
    across different providers and services.
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.RLock()
    
    def get_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Get or create a circuit breaker by name."""
        with self._lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(name, config)
                logger.info(f"Created new circuit breaker: {name}")
            return self._breakers[name]
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        with self._lock:
            return {name: breaker.stats for name, breaker in self._breakers.items()}
    
    def reset_all(self):
        """Reset all circuit breakers."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            logger.info("All circuit breakers reset")
    
    def get_healthy_breakers(self) -> List[str]:
        """Get list of circuit breakers in closed state."""
        with self._lock:
            return [name for name, breaker in self._breakers.items() 
                   if breaker.state == CircuitState.CLOSED]
    
    def get_failing_breakers(self) -> List[str]:
        """Get list of circuit breakers in open state."""
        with self._lock:
            return [name for name, breaker in self._breakers.items() 
                   if breaker.state == CircuitState.OPEN]


# Global circuit breaker registry
_registry = CircuitBreakerRegistry()

def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get a circuit breaker from the global registry."""
    return _registry.get_breaker(name, config)

def get_circuit_breaker_stats() -> Dict[str, Dict[str, Any]]:
    """Get statistics for all circuit breakers."""
    return _registry.get_stats()

def reset_all_circuit_breakers():
    """Reset all circuit breakers in the registry."""
    _registry.reset_all()