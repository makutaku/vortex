import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from vortex.infrastructure.resilience.circuit_breaker import (
    CircuitState, CircuitBreakerConfig, CircuitBreaker, CircuitOpenException,
    get_circuit_breaker, get_circuit_breaker_stats, reset_all_circuit_breakers,
    CircuitBreakerRegistry, CallResult
)
from vortex.exceptions import (
    VortexError, DataProviderError, AuthenticationError, 
    RateLimitError, ConnectionError, DataNotFoundError,
    AllowanceLimitExceededError
)


class TestCircuitState:
    def test_circuit_state_enum_values(self):
        """Test CircuitState enum has expected values."""
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"

    def test_circuit_state_membership(self):
        """Test all expected states are in enum."""
        states = [s.value for s in CircuitState]
        assert "closed" in states
        assert "open" in states
        assert "half_open" in states


class TestCircuitBreakerConfig:
    def test_config_creation(self):
        """Test CircuitBreakerConfig creation."""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            timeout=120.0,
            success_threshold=3
        )
        
        assert config.failure_threshold == 10
        assert config.timeout == 120.0
        assert config.success_threshold == 3

    def test_config_defaults(self):
        """Test CircuitBreakerConfig default values."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.timeout == 30
        assert config.success_threshold == 3

    def test_config_validation(self):
        """Test CircuitBreakerConfig validation."""
        # Valid config
        config = CircuitBreakerConfig(failure_threshold=1, timeout=1.0)
        assert config.failure_threshold >= 1
        assert config.timeout > 0

    def test_config_with_custom_values(self):
        """Test CircuitBreakerConfig with various custom values."""
        config = CircuitBreakerConfig(
            failure_threshold=15,
            timeout=300.0,
            success_threshold=5
        )
        
        assert config.failure_threshold == 15
        assert config.timeout == 300.0
        assert config.success_threshold == 5


class TestCallResult:
    def test_call_result_success(self):
        """Test CallResult for successful calls."""
        timestamp = datetime.now()
        result = CallResult(
            timestamp=timestamp,
            success=True,
            duration=1.5,
            exception=None
        )
        
        assert result.success is True
        assert result.timestamp == timestamp
        assert result.duration == 1.5
        assert result.exception is None

    def test_call_result_failure(self):
        """Test CallResult for failed calls."""
        timestamp = datetime.now()
        exception = ConnectionError("Failed")
        result = CallResult(
            timestamp=timestamp,
            success=False,
            duration=0.5,
            exception=exception
        )
        
        assert result.success is False
        assert result.timestamp == timestamp
        assert result.duration == 0.5
        assert result.exception == exception


class TestCircuitOpenException:
    def test_circuit_open_exception_creation(self):
        """Test CircuitOpenException creation."""
        exception = CircuitOpenException("test_circuit")
        
        assert "test_circuit" in str(exception)
        assert isinstance(exception, Exception)

    def test_circuit_open_exception_with_custom_message(self):
        """Test CircuitOpenException with custom message."""
        exception = CircuitOpenException("service", "Custom message")
        
        assert "service" in str(exception)
        assert "Custom message" in str(exception)


class TestCircuitBreaker:
    @pytest.fixture
    def circuit_breaker(self):
        """Create CircuitBreaker with default config."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout=1.0,  # Short timeout for testing
            success_threshold=2
        )
        return CircuitBreaker("test_circuit", config)

    @pytest.fixture
    def custom_circuit_breaker(self):
        """Create CircuitBreaker with custom config."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout=0.1,  # Very short for testing
            success_threshold=1
        )
        return CircuitBreaker("custom_circuit", config)

    def test_circuit_breaker_initialization(self, circuit_breaker):
        """Test CircuitBreaker initialization."""
        assert circuit_breaker.name == "test_circuit"
        assert isinstance(circuit_breaker.config, CircuitBreakerConfig)
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_name_and_config(self, custom_circuit_breaker):
        """Test CircuitBreaker with custom name and config."""
        assert custom_circuit_breaker.name == "custom_circuit"
        assert custom_circuit_breaker.config.failure_threshold == 2
        assert custom_circuit_breaker.config.timeout == 0.1

    def test_is_closed_state(self, circuit_breaker):
        """Test state checking methods."""
        assert circuit_breaker.state == CircuitState.CLOSED
        
        # Test state checking methods if they exist
        if hasattr(circuit_breaker, 'is_closed'):
            assert circuit_breaker.is_closed() is True
        if hasattr(circuit_breaker, 'is_open'):
            assert circuit_breaker.is_open() is False
        if hasattr(circuit_breaker, 'is_half_open'):
            assert circuit_breaker.is_half_open() is False

    def test_execute_success_in_closed_state(self, circuit_breaker):
        """Test successful execution in CLOSED state."""
        def successful_function():
            return "success"
        
        result = circuit_breaker.call(successful_function)
        
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_execute_failure_in_closed_state(self, circuit_breaker):
        """Test failed execution in CLOSED state."""
        def failing_function():
            raise ConnectionError("Network error")
        
        with pytest.raises(ConnectionError):
            circuit_breaker.call(failing_function)
        
        # Circuit should still be closed after single failure
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_state_transitions_with_failures(self, circuit_breaker):
        """Test circuit breaker state transitions with multiple failures."""
        def failing_function():
            raise ConnectionError("Network error")
        
        # Generate failures up to threshold
        for i in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(ConnectionError):
                circuit_breaker.call(failing_function)
        
        # Circuit should be open after threshold failures
        assert circuit_breaker.state == CircuitState.OPEN

    def test_execute_in_open_state_fails_fast(self, circuit_breaker):
        """Test execution in OPEN state fails fast."""
        # Force circuit to OPEN state by exceeding failure threshold
        def failing_function():
            raise ConnectionError("Network error")
        
        for _ in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(ConnectionError):
                circuit_breaker.call(failing_function)
        
        # Circuit should be open
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Now any call should fail fast with CircuitOpenException
        def test_function():
            return "should_not_execute"
        
        with pytest.raises(CircuitOpenException):
            circuit_breaker.call(test_function)

    def test_function_with_arguments(self, circuit_breaker):
        """Test circuit breaker with function arguments."""
        def add_numbers(a, b, multiplier=1):
            return (a + b) * multiplier
        
        result = circuit_breaker.call(add_numbers, 5, 3, multiplier=2)
        
        assert result == 16  # (5 + 3) * 2

    def test_get_stats(self, circuit_breaker):
        """Test getting circuit breaker statistics."""
        # Generate some activity
        def successful_function():
            return "success"
        
        def failing_function():
            raise ConnectionError("Network error")
        
        # Execute some successful calls
        circuit_breaker.call(successful_function)
        circuit_breaker.call(successful_function)
        
        # Execute a failing call
        with pytest.raises(ConnectionError):
            circuit_breaker.call(failing_function)
        
        # Get stats
        stats = circuit_breaker.stats
        
        # Should have recorded the calls
        assert isinstance(stats, dict)
        assert 'total_calls' in stats or 'success_count' in stats or 'failure_count' in stats

    def test_reset_circuit_breaker(self, circuit_breaker):
        """Test resetting circuit breaker."""
        # Force to OPEN state
        def failing_function():
            raise ConnectionError("Network error")
        
        for _ in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(ConnectionError):
                circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Reset circuit breaker
        circuit_breaker.reset()
        
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_half_open_state_recovery(self, circuit_breaker):
        """Test recovery through HALF_OPEN state."""
        # Force to OPEN state
        def failing_function():
            raise ConnectionError("Network error")
        
        for _ in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(ConnectionError):
                circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Wait for timeout to allow transition to HALF_OPEN
        time.sleep(circuit_breaker.config.recovery_timeout + 0.1)
        
        # Next successful call should help recover
        def successful_function():
            return "recovered"
        
        # This might transition through HALF_OPEN to CLOSED
        result = circuit_breaker.call(successful_function)
        assert result == "recovered"

    def test_thread_safety(self, circuit_breaker):
        """Test circuit breaker thread safety."""
        results = []
        errors = []
        
        def test_function(thread_id):
            try:
                return f"thread_{thread_id}_success"
            except Exception as e:
                errors.append(e)
                raise
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(
                target=lambda tid=i: results.append(circuit_breaker.call(test_function, tid))
            )
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # All should succeed
        assert len(results) == 5
        assert len(errors) == 0


class TestCircuitBreakerRegistry:
    def test_circuit_breaker_registry_singleton(self):
        """Test CircuitBreakerRegistry global instance behavior."""
        from vortex.infrastructure.resilience.circuit_breaker import _registry
        
        # Access global registry multiple times
        registry1 = _registry
        registry2 = _registry
        
        # Should be the same instance
        assert registry1 is registry2

    def test_registry_get_breaker(self):
        """Test registry get_breaker functionality."""
        registry = CircuitBreakerRegistry()
        
        # Get circuit breaker for service
        breaker1 = registry.get_breaker("test_service")
        breaker2 = registry.get_breaker("test_service")
        
        # Should return same instance
        assert breaker1 is breaker2
        assert breaker1.name == "test_service"

    def test_registry_different_services(self):
        """Test registry with different service names."""
        registry = CircuitBreakerRegistry()
        
        breaker1 = registry.get_breaker("service1")
        breaker2 = registry.get_breaker("service2")
        
        # Should be different instances
        assert breaker1 is not breaker2
        assert breaker1.name == "service1"
        assert breaker2.name == "service2"

    def test_registry_with_custom_config(self):
        """Test registry with custom configuration."""
        registry = CircuitBreakerRegistry()
        config = CircuitBreakerConfig(failure_threshold=10)
        
        breaker = registry.get_breaker("custom_service", config)
        
        assert breaker.name == "custom_service"
        assert breaker.config.failure_threshold == 10


class TestModuleFunctions:
    def test_get_circuit_breaker_function(self):
        """Test get_circuit_breaker module function."""
        breaker1 = get_circuit_breaker("test_service")
        breaker2 = get_circuit_breaker("test_service")
        
        # Should return the same instance
        assert breaker1 is breaker2
        assert breaker1.name == "test_service"

    def test_get_circuit_breaker_with_config(self):
        """Test get_circuit_breaker with custom config."""
        config = CircuitBreakerConfig(failure_threshold=7)
        breaker = get_circuit_breaker("configured_service", config)
        
        assert breaker.name == "configured_service"
        assert breaker.config.failure_threshold == 7

    def test_get_circuit_breaker_stats_function(self):
        """Test get_circuit_breaker_stats module function."""
        # Create a circuit breaker and generate some activity
        breaker = get_circuit_breaker("stats_test")
        
        def test_function():
            return "success"
        
        breaker.call(test_function)
        
        # Get stats for all circuit breakers
        all_stats = get_circuit_breaker_stats()
        
        assert isinstance(all_stats, dict)
        assert "stats_test" in all_stats

    def test_reset_all_circuit_breakers_function(self):
        """Test reset_all_circuit_breakers module function."""
        # Create some circuit breakers and put them in OPEN state
        breaker1 = get_circuit_breaker("reset_test1")
        breaker2 = get_circuit_breaker("reset_test2")
        
        # Force them to OPEN state
        def failing_function():
            raise ConnectionError("Error")
        
        for breaker in [breaker1, breaker2]:
            for _ in range(breaker.config.failure_threshold):
                with pytest.raises(ConnectionError):
                    breaker.call(failing_function)
            assert breaker.state == CircuitState.OPEN
        
        # Reset all circuit breakers
        reset_all_circuit_breakers()
        
        # All should be CLOSED
        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED


class TestIntegration:
    def test_full_circuit_breaker_workflow(self):
        """Test complete circuit breaker workflow."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # Short for testing
            success_threshold=1
        )
        breaker = CircuitBreaker("integration_test", config)
        
        call_count = 0
        def unstable_service():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError(f"Failure {call_count}")
            return f"Success on call {call_count}"
        
        # First two calls should fail and open circuit
        for _ in range(2):
            with pytest.raises(ConnectionError):
                breaker.call(unstable_service)
        
        # Circuit should be open
        assert breaker.state == CircuitState.OPEN
        
        # Next call should fail fast
        with pytest.raises(CircuitOpenException):
            breaker.call(unstable_service)
        
        # Wait for recovery timeout
        time.sleep(0.2)
        
        # Next call should succeed (after recovery timeout)
        result = breaker.call(unstable_service)
        assert "Success" in result

    def test_circuit_breaker_with_different_exception_types(self):
        """Test circuit breaker with various exception types."""
        breaker = CircuitBreaker("exception_test", CircuitBreakerConfig(failure_threshold=3))
        
        # Test various exceptions
        exceptions = [
            ConnectionError("Network"),
            RateLimitError("test", wait_time=30),
            DataProviderError("test", "Provider error")
        ]
        
        for exception in exceptions:
            def failing_function():
                raise exception
            
            with pytest.raises(type(exception)):
                breaker.call(failing_function)

    def test_multiple_circuit_breakers_independence(self):
        """Test that multiple circuit breakers operate independently."""
        breaker1 = get_circuit_breaker("independent1")
        breaker2 = get_circuit_breaker("independent2")
        
        # Fail one circuit breaker
        def failing_function():
            raise ConnectionError("Error")
        
        for _ in range(breaker1.config.failure_threshold):
            with pytest.raises(ConnectionError):
                breaker1.call(failing_function)
        
        # breaker1 should be open, breaker2 should still be closed
        assert breaker1.state == CircuitState.OPEN
        assert breaker2.state == CircuitState.CLOSED
        
        # breaker2 should still work
        def successful_function():
            return "success"
        
        result = breaker2.call(successful_function)
        assert result == "success"

    def test_circuit_breaker_error_handling(self):
        """Test circuit breaker error handling and logging."""
        breaker = CircuitBreaker("error_test", CircuitBreakerConfig(failure_threshold=2))
        
        # Test with various error conditions
        def different_errors(error_type):
            if error_type == "connection":
                raise ConnectionError("Network error")
            elif error_type == "rate_limit": 
                raise RateLimitError("test", wait_time=60)
            elif error_type == "data_provider":
                raise DataProviderError("test", "Provider error")
            else:
                raise ValueError("Non-monitored error")
        
        # Test monitored exceptions
        for error_type in ["connection", "rate_limit"]:
            with pytest.raises((ConnectionError, RateLimitError)):
                breaker.call(different_errors, error_type)
        
        # Circuit should be open after monitored failures
        assert breaker.state == CircuitState.OPEN

    def test_circuit_breaker_performance_under_load(self):
        """Test circuit breaker performance characteristics."""
        breaker = CircuitBreaker("performance_test", CircuitBreakerConfig(failure_threshold=5))
        
        start_time = time.time()
        success_count = 0
        
        def fast_operation():
            return "fast_result"
        
        # Execute many operations
        for _ in range(100):
            result = breaker.call(fast_operation)
            if result == "fast_result":
                success_count += 1
        
        end_time = time.time()
        
        # Should complete quickly and successfully
        assert success_count == 100
        assert (end_time - start_time) < 1.0  # Should be very fast
        
        # Circuit should remain closed
        assert breaker.state == CircuitState.CLOSED