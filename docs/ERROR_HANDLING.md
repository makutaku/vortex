# Comprehensive Error Handling & Resilience System

Vortex now includes a sophisticated error handling and resilience system designed to provide robust operation in the face of network failures, API issues, and other transient problems.

## Overview

The resilience system consists of several integrated components:

- **Enhanced Exception Hierarchy**: Rich context and user-friendly error messages
- **Circuit Breaker Pattern**: Failure isolation and service protection
- **Intelligent Retry Logic**: Exponential backoff with jitter and provider-specific policies
- **Correlation ID Tracking**: Request tracing across components
- **Error Recovery Strategies**: Automated recovery with fallback mechanisms
- **Structured Logging**: Comprehensive error context and debugging information

## Exception System

### Enhanced VortexError Base Class

All exceptions now include comprehensive context:

```python
class VortexError(Exception):
    def __init__(
        self, 
        message: str, 
        help_text: Optional[str] = None, 
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        user_action: Optional[str] = None,
        technical_details: Optional[str] = None,
        correlation_id: Optional[str] = None
    ):
        # Rich context and tracking
```

### Key Features

- **Correlation IDs**: Unique identifiers for tracking errors across logs
- **User Actions**: Specific steps users can take to resolve issues
- **Technical Details**: Debug information for developers
- **Context Information**: Structured data about the error circumstances
- **Help Text**: Human-readable guidance

### Example Usage

```python
from vortex.exceptions import AuthenticationError

try:
    provider.authenticate()
except AuthenticationError as e:
    print(f"Error: {e.message}")
    print(f"Action: {e.user_action}")
    print(f"Help: {e.help_text}")
    print(f"Error ID: {e.correlation_id}")
```

## Circuit Breaker Pattern

### Purpose

Circuit breakers prevent cascading failures by monitoring error rates and temporarily disabling failing services.

### States

- **CLOSED**: Normal operation, requests pass through
- **OPEN**: Service failing, requests blocked immediately
- **HALF_OPEN**: Testing if service has recovered

### Configuration

```python
from vortex.resilience.circuit_breaker import CircuitBreakerConfig, get_circuit_breaker

config = CircuitBreakerConfig(
    failure_threshold=5,          # Failures before opening
    recovery_timeout=60,          # Seconds before testing recovery
    success_threshold=3,          # Successes to close circuit
    sliding_window_size=100       # Size of failure tracking window
)

breaker = get_circuit_breaker("my_service", config)
```

### Usage

```python
# Decorator usage
@breaker
def risky_operation():
    # This operation is protected by circuit breaker
    pass

# Direct usage
try:
    result = breaker.call(risky_operation)
except CircuitOpenException:
    print("Service is currently unavailable")
```

## Retry Logic

### Retry Strategies

- **FIXED_DELAY**: Constant delay between retries
- **LINEAR_BACKOFF**: Linear increase in delay
- **EXPONENTIAL_BACKOFF**: Exponential increase (recommended)
- **EXPONENTIAL_BACKOFF_JITTER**: Exponential with randomization to prevent thundering herd

### Provider-Specific Policies

```python
from vortex.resilience.retry import provider_retry, RetryStrategy

@provider_retry(
    provider_name="barchart",
    max_attempts=5,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF_JITTER,
    base_delay=2.0,
    max_delay=120.0
)
def fetch_data():
    # This function will be retried with provider-specific logic
    pass
```

### Custom Retry Configuration

```python
from vortex.resilience.retry import RetryPolicy, RetryManager

policy = RetryPolicy(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF_JITTER,
    base_delay=1.0,
    max_delay=60.0,
    retryable_exceptions=(ConnectionError, RateLimitError),
    non_retryable_exceptions=(AuthenticationError,)
)

retry_manager = RetryManager(policy)

@retry_manager
def my_function():
    # Function with custom retry logic
    pass
```

## Correlation ID Tracking

### Purpose

Correlation IDs enable tracking requests across different components and external services, making debugging much easier.

### Usage

```python
from vortex.resilience.correlation import CorrelationIdManager, with_correlation

# Context manager
with CorrelationIdManager.correlation_context(
    operation="data_download",
    provider="yahoo"
) as context:
    # All operations in this block share the correlation ID
    result = download_data()

# Decorator
@with_correlation(operation="fetch_data", provider="barchart")
def fetch_data():
    # This function automatically gets correlation context
    pass

# Adding metadata
CorrelationIdManager.add_context_metadata(
    symbol="AAPL",
    date_range="2024-01-01 to 2024-12-31"
)
```

### Accessing Current Context

```python
correlation_id = CorrelationIdManager.get_current_id()
context = CorrelationIdManager.get_current_context()
```

## Error Recovery Strategies

### Available Strategies

- **IMMEDIATE_RETRY**: Retry immediately
- **EXPONENTIAL_BACKOFF**: Retry with increasing delays
- **PROVIDER_FALLBACK**: Switch to alternative data provider
- **GRACEFUL_DEGRADATION**: Use reduced functionality
- **CIRCUIT_BREAKER**: Use circuit breaker protection
- **MANUAL_INTERVENTION**: Requires user action

### Recovery Manager

```python
from vortex.resilience.recovery import ErrorRecoveryManager, DataProviderRecoveryPolicy

# Create recovery policy with fallback providers
policy = DataProviderRecoveryPolicy(
    max_retry_attempts=3,
    fallback_providers=["yahoo", "alpha_vantage"]
)

recovery_manager = ErrorRecoveryManager(policy)

# Attempt recovery
try:
    result = risky_operation()
except Exception as e:
    recovery_result = recovery_manager.attempt_recovery(
        risky_operation, e, {"provider": "barchart"}
    )
    if recovery_result.success:
        print(f"Recovered using {recovery_result.strategy_used}")
    else:
        print("Recovery failed - manual intervention required")
```

## Integration Example

Here's how to integrate all resilience patterns in a data provider:

```python
from vortex.resilience import *

class ResilientDataProvider:
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        
        # Circuit breaker for failure isolation
        self.circuit_breaker = get_circuit_breaker(
            f"provider_{provider_name}",
            CircuitBreakerConfig(failure_threshold=3)
        )
        
        # Error recovery with fallbacks
        self.recovery_manager = ErrorRecoveryManager(
            DataProviderRecoveryPolicy(fallback_providers=["yahoo", "barchart"])
        )
    
    @provider_retry(provider_name="my_provider")
    @with_correlation(operation="fetch_data")
    def fetch_data(self, symbol: str):
        correlation_id = CorrelationIdManager.get_current_id()
        
        try:
            # Use circuit breaker protection
            return self.circuit_breaker.call(self._do_fetch, symbol)
        except Exception as e:
            # Enhance error with context
            if hasattr(e, 'add_context'):
                e.add_context(
                    provider=self.provider_name,
                    symbol=symbol,
                    correlation_id=correlation_id
                )
            
            # Attempt recovery
            recovery_result = self.recovery_manager.attempt_recovery(
                self._do_fetch, e, {"provider": self.provider_name}
            )
            
            if not recovery_result.success:
                raise
                
    def _do_fetch(self, symbol: str):
        # Actual implementation
        pass
```

## CLI Integration

### Error Display

The CLI now shows comprehensive error information:

```
🔐 Authentication Failed: Invalid credentials provided

💡 Help: Verify your barchart credentials are correct and active
🔧 Action: Run: vortex config --provider barchart --set-credentials
📋 Details: HTTP 401 Unauthorized - Invalid credentials
🔍 Error ID: a7b9c1d2
```

### Resilience Commands

Monitor system health and resilience:

```bash
# Show circuit breaker status
vortex resilience status

# Show system health
vortex resilience health

# Reset circuit breakers
vortex resilience reset

# Show recovery statistics
vortex resilience recovery

# Quick status check
vortex resilience-status
```

## Monitoring and Debugging

### Structured Logging

All errors are logged with comprehensive context:

```json
{
  "timestamp": "2024-08-04T10:30:45Z",
  "level": "ERROR",
  "correlation_id": "a7b9c1d2",
  "operation": "fetch_data",
  "provider": "barchart",
  "error_type": "AuthenticationError",
  "error_code": "AUTH_FAILED",
  "context": {
    "symbol": "AAPL",
    "http_code": 401,
    "provider": "barchart"
  }
}
```

### Circuit Breaker Statistics

```python
from vortex.resilience.circuit_breaker import get_circuit_breaker_stats

stats = get_circuit_breaker_stats()
print(f"Total calls: {stats['provider_barchart']['total_calls']}")
print(f"Failure rate: {stats['provider_barchart']['failure_rate']*100:.1f}%")
```

### Recovery Metrics

```python
recovery_stats = recovery_manager.get_recovery_stats()
for operation, stats in recovery_stats.items():
    print(f"{operation}: {stats['successful_recoveries']}/{stats['total_attempts']} recoveries")
```

## Best Practices

### 1. Use Correlation IDs Consistently

Always use correlation context for operations that span multiple components:

```python
@with_correlation(operation="download_portfolio")
def download_portfolio(symbols):
    for symbol in symbols:
        # Each symbol download shares the same correlation ID
        download_symbol(symbol)
```

### 2. Configure Circuit Breakers Appropriately

Set thresholds based on your service characteristics:

```python
# For critical services - fail fast
critical_config = CircuitBreakerConfig(
    failure_threshold=2,
    recovery_timeout=120
)

# For less critical services - more tolerant
relaxed_config = CircuitBreakerConfig(
    failure_threshold=10,
    recovery_timeout=30
)
```

### 3. Provide Meaningful Error Context

Always add relevant context to exceptions:

```python
try:
    data = fetch_data(symbol)
except Exception as e:
    if hasattr(e, 'add_context'):
        e.add_context(
            symbol=symbol,
            date_range=f"{start_date} to {end_date}",
            provider=provider_name
        )
    raise
```

### 4. Use Provider-Specific Retry Policies

Different providers have different characteristics:

```python
# High-volume free provider - be gentle
@provider_retry("yahoo", max_attempts=2, base_delay=5.0)
def fetch_from_yahoo():
    pass

# Premium provider - more aggressive
@provider_retry("bloomberg", max_attempts=5, base_delay=1.0)
def fetch_from_bloomberg():
    pass
```

### 5. Monitor System Health

Regularly check resilience metrics:

```bash
# Add to monitoring scripts
vortex resilience health --format json | jq '.health_score'
```

## Migration Guide

### From Legacy Exceptions

Old code:
```python
from vortex.data_providers.data_provider import DownloadError

try:
    data = provider.fetch()
except DownloadError as e:
    print(f"Error: {e.msg}")
```

New code:
```python
from vortex.exceptions import DataProviderError

try:
    data = provider.fetch()
except DataProviderError as e:
    print(f"Error: {e.message}")
    if e.user_action:
        print(f"Action: {e.user_action}")
    print(f"Error ID: {e.correlation_id}")
```

### Adding Resilience to Existing Providers

1. **Add circuit breaker protection**:
```python
self.circuit_breaker = get_circuit_breaker(f"provider_{self.name}")
```

2. **Add retry logic**:
```python
@provider_retry(self.name)
def fetch_data(self):
    # existing implementation
```

3. **Add correlation tracking**:
```python
@with_correlation(operation="fetch_data", provider=self.name)
def fetch_data(self):
    # existing implementation
```

4. **Enhance error handling**:
```python
except Exception as e:
    if hasattr(e, 'add_context'):
        e.add_context(provider=self.name, symbol=symbol)
    raise
```

## Testing

### Testing Resilience Patterns

```python
import pytest
from vortex.resilience.circuit_breaker import CircuitOpenException

def test_circuit_breaker_opens_on_failures():
    breaker = get_circuit_breaker("test", CircuitBreakerConfig(failure_threshold=2))
    
    # Cause failures to open circuit
    for _ in range(3):
        with pytest.raises(Exception):
            breaker.call(lambda: exec('raise Exception("test")'))
    
    # Circuit should now be open
    with pytest.raises(CircuitOpenException):
        breaker.call(lambda: "success")
```

### Testing Recovery Logic

```python
def test_provider_fallback():
    recovery_manager = ErrorRecoveryManager(
        DataProviderRecoveryPolicy(fallback_providers=["yahoo"])
    )
    
    def failing_operation():
        raise ConnectionError("primary", "Connection failed")
    
    result = recovery_manager.attempt_recovery(
        failing_operation,
        ConnectionError("primary", "Connection failed"),
        {"provider": "primary"}
    )
    
    # Recovery should attempt fallback
    assert "fallback" in [action.strategy for action in result.attempted_strategies]
```

## Performance Impact

The resilience system is designed to have minimal performance impact:

- **Circuit breakers**: ~1μs overhead per call when closed
- **Correlation IDs**: ~10μs to generate and propagate
- **Retry logic**: Only active during failures
- **Error recovery**: Only active during failures

For high-frequency operations, you can disable certain features:

```python
# Minimal overhead configuration
lightweight_config = CircuitBreakerConfig(
    failure_threshold=20,  # Higher threshold
    minimum_calls=50       # More calls before evaluation
)
```

This comprehensive error handling and resilience system makes Vortex much more robust and production-ready, with clear error messages, intelligent recovery, and comprehensive monitoring capabilities.