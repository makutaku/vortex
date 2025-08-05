import pytest
import time
import random
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Any, Callable

from vortex.infrastructure.resilience.retry import (
    RetryStrategy, RetryPolicy, RetryAttempt,
    BackoffStrategy, ExponentialBackoffStrategy, LinearBackoffStrategy, FixedDelayStrategy,
    RetryManager, ProviderRetryManager, retry_with_backoff, provider_retry
)
from vortex.exceptions import (
    VortexError, DataProviderError, AuthenticationError, 
    RateLimitError, ConnectionError, DataNotFoundError,
    AllowanceLimitExceededError
)


class TestRetryStrategy:
    def test_retry_strategy_enum_values(self):
        """Test RetryStrategy enum has expected values."""
        assert RetryStrategy.FIXED_DELAY.value == "fixed_delay"
        assert RetryStrategy.LINEAR_BACKOFF.value == "linear_backoff"
        assert RetryStrategy.EXPONENTIAL_BACKOFF.value == "exponential_backoff"
        assert RetryStrategy.EXPONENTIAL_BACKOFF_JITTER.value == "exponential_backoff_jitter"

    def test_retry_strategy_enum_membership(self):
        """Test all expected strategies are in enum."""
        strategies = [s.value for s in RetryStrategy]
        assert "fixed_delay" in strategies
        assert "linear_backoff" in strategies
        assert "exponential_backoff" in strategies
        assert "exponential_backoff_jitter" in strategies


class TestRetryPolicy:
    def test_retry_policy_defaults(self):
        """Test RetryPolicy default values."""
        policy = RetryPolicy()
        
        assert policy.max_attempts == 3
        assert policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF_JITTER
        assert policy.base_delay == 1.0
        assert policy.max_delay == 60.0
        assert policy.multiplier == 2.0
        assert policy.jitter_max == 0.1

    def test_retry_policy_custom_values(self):
        """Test RetryPolicy with custom values."""
        policy = RetryPolicy(
            max_attempts=5,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=2.0,
            max_delay=120.0,
            multiplier=3.0,
            jitter_max=0.2
        )
        
        assert policy.max_attempts == 5
        assert policy.strategy == RetryStrategy.FIXED_DELAY
        assert policy.base_delay == 2.0
        assert policy.max_delay == 120.0
        assert policy.multiplier == 3.0
        assert policy.jitter_max == 0.2

    def test_retry_policy_retryable_exceptions(self):
        """Test RetryPolicy retryable exception configuration."""
        policy = RetryPolicy()
        
        assert ConnectionError in policy.retryable_exceptions
        assert RateLimitError in policy.retryable_exceptions
        assert DataProviderError in policy.retryable_exceptions

    def test_retry_policy_non_retryable_exceptions(self):
        """Test RetryPolicy non-retryable exception configuration."""
        policy = RetryPolicy()
        
        assert AuthenticationError in policy.non_retryable_exceptions
        assert DataNotFoundError in policy.non_retryable_exceptions
        assert AllowanceLimitExceededError in policy.non_retryable_exceptions


class TestRetryAttempt:
    def test_retry_attempt_creation(self):
        """Test RetryAttempt creation and attributes."""
        timestamp = datetime.now()
        exception = ConnectionError("Network error")
        
        attempt = RetryAttempt(
            attempt_number=2,
            delay=1.5,
            exception=exception,
            timestamp=timestamp,
            total_elapsed=3.2
        )
        
        assert attempt.attempt_number == 2
        assert attempt.delay == 1.5
        assert attempt.exception == exception
        assert attempt.timestamp == timestamp
        assert attempt.total_elapsed == 3.2

    def test_retry_attempt_optional_exception(self):
        """Test RetryAttempt with None exception."""
        attempt = RetryAttempt(
            attempt_number=1,
            delay=0.0,
            exception=None,
            timestamp=datetime.now(),
            total_elapsed=1.0
        )
        
        assert attempt.exception is None
        assert attempt.attempt_number == 1


class TestBackoffStrategies:
    def test_fixed_delay_strategy(self):
        """Test FixedDelayStrategy."""
        strategy = FixedDelayStrategy()
        
        # Should always return base_delay (or max_delay if smaller)
        assert strategy.calculate_delay(1, 2.0, 60.0) == 2.0
        assert strategy.calculate_delay(5, 2.0, 60.0) == 2.0
        assert strategy.calculate_delay(10, 2.0, 60.0) == 2.0
        
        # Should respect max_delay
        assert strategy.calculate_delay(1, 100.0, 50.0) == 50.0

    def test_linear_backoff_strategy(self):
        """Test LinearBackoffStrategy."""
        strategy = LinearBackoffStrategy()
        
        # Should increase linearly
        assert strategy.calculate_delay(1, 1.0, 60.0) == 1.0  # base_delay * 1
        assert strategy.calculate_delay(2, 1.0, 60.0) == 2.0  # base_delay * 2
        assert strategy.calculate_delay(3, 1.0, 60.0) == 3.0  # base_delay * 3
        
        # Should respect max_delay
        assert strategy.calculate_delay(100, 1.0, 5.0) == 5.0

    def test_exponential_backoff_strategy_without_jitter(self):
        """Test ExponentialBackoffStrategy without jitter."""
        strategy = ExponentialBackoffStrategy(multiplier=2.0, jitter=False)
        
        # Should increase exponentially
        delay1 = strategy.calculate_delay(1, 1.0, 60.0)
        delay2 = strategy.calculate_delay(2, 1.0, 60.0) 
        delay3 = strategy.calculate_delay(3, 1.0, 60.0)
        
        assert delay1 == 1.0  # base_delay * multiplier^0
        assert delay2 == 2.0  # base_delay * multiplier^1
        assert delay3 == 4.0  # base_delay * multiplier^2

    def test_exponential_backoff_strategy_with_jitter(self):
        """Test ExponentialBackoffStrategy with jitter."""
        strategy = ExponentialBackoffStrategy(multiplier=2.0, jitter=True, jitter_max=0.1)
        
        # Test multiple calls to verify jitter variation
        base_delay = 10.0
        delays = [strategy.calculate_delay(1, base_delay, 60.0) for _ in range(10)]
        
        # All delays should be >= base_delay (jitter adds to delay)
        assert all(delay >= base_delay for delay in delays)
        
        # Should have some variation due to jitter
        assert len(set(delays)) > 1

    def test_exponential_backoff_strategy_max_delay(self):
        """Test ExponentialBackoffStrategy respects max_delay."""
        strategy = ExponentialBackoffStrategy(multiplier=2.0, jitter=False)
        
        # Large attempt should be capped by max_delay
        delay = strategy.calculate_delay(10, 1.0, 5.0)
        assert delay == 5.0


class TestRetryManager:
    @pytest.fixture
    def retry_manager(self):
        """Create RetryManager with default policy."""
        return RetryManager()

    @pytest.fixture
    def custom_retry_manager(self):
        """Create RetryManager with custom policy."""
        policy = RetryPolicy(
            max_attempts=2,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.1
        )
        return RetryManager(policy)

    def test_retry_manager_initialization(self, retry_manager):
        """Test RetryManager initialization."""
        assert isinstance(retry_manager.policy, RetryPolicy)
        assert retry_manager.policy.max_attempts == 3  # Default

    def test_retry_manager_custom_policy(self, custom_retry_manager):
        """Test RetryManager with custom policy."""
        assert custom_retry_manager.policy.max_attempts == 2
        assert custom_retry_manager.policy.strategy == RetryStrategy.FIXED_DELAY

    def test_retry_manager_strategy_mapping(self, retry_manager):
        """Test that strategy mapping is properly initialized."""
        assert RetryStrategy.FIXED_DELAY in retry_manager.strategy_map
        assert RetryStrategy.LINEAR_BACKOFF in retry_manager.strategy_map
        assert RetryStrategy.EXPONENTIAL_BACKOFF in retry_manager.strategy_map
        assert RetryStrategy.EXPONENTIAL_BACKOFF_JITTER in retry_manager.strategy_map
        
        # Test strategy instances
        assert isinstance(retry_manager.strategy_map[RetryStrategy.FIXED_DELAY], FixedDelayStrategy)
        assert isinstance(retry_manager.strategy_map[RetryStrategy.LINEAR_BACKOFF], LinearBackoffStrategy)
        assert isinstance(retry_manager.strategy_map[RetryStrategy.EXPONENTIAL_BACKOFF], ExponentialBackoffStrategy)
        assert isinstance(retry_manager.strategy_map[RetryStrategy.EXPONENTIAL_BACKOFF_JITTER], ExponentialBackoffStrategy)

    def test_should_retry_retryable_exceptions(self, retry_manager):
        """Test _should_retry with retryable exceptions."""
        retryable_exceptions = [
            ConnectionError("Network error"),
            RateLimitError("test", wait_time=60),
            DataProviderError("test", "Temporary error")
        ]
        
        for exception in retryable_exceptions:
            assert retry_manager._should_retry(exception, attempt=1) is True

    def test_should_retry_non_retryable_exceptions(self, retry_manager):
        """Test _should_retry with non-retryable exceptions."""
        non_retryable_exceptions = [
            AuthenticationError("test"),
            DataNotFoundError(
                provider="test", symbol="TEST", period="1d",
                start_date=datetime.now(), end_date=datetime.now()
            ),
            AllowanceLimitExceededError("test", current_allowance=0, max_allowance=100)
        ]
        
        for exception in non_retryable_exceptions:
            assert retry_manager._should_retry(exception, attempt=1) is False

    def test_should_retry_max_attempts_exceeded(self, retry_manager):
        """Test _should_retry when max attempts exceeded."""
        exception = ConnectionError("Network error")
        
        assert retry_manager._should_retry(exception, attempt=3) is False  # At max
        assert retry_manager._should_retry(exception, attempt=4) is False  # Over max

    def test_calculate_delay_uses_strategy(self, retry_manager):
        """Test _calculate_delay uses configured strategy."""
        retry_manager.policy.strategy = RetryStrategy.FIXED_DELAY
        retry_manager.policy.base_delay = 2.0
        
        delay = retry_manager._calculate_delay(1)
        assert delay == 2.0

    def test_calculate_delay_rate_limit_fallback_to_strategy(self, retry_manager):
        """Test _calculate_delay falls back to strategy for RateLimitError without wait_time."""
        # Create RateLimitError (doesn't expose wait_time attribute)
        rate_limit_error = RateLimitError("test", wait_time=30)
        
        # Configure policy 
        retry_manager.policy.strategy = RetryStrategy.FIXED_DELAY
        retry_manager.policy.base_delay = 2.0
        
        delay = retry_manager._calculate_delay(1, rate_limit_error)
        
        # Should fall back to strategy since wait_time isn't accessible
        assert delay == 2.0

    @patch('time.sleep')
    def test_execute_with_retry_success_first_attempt(self, mock_sleep, retry_manager):
        """Test execute_with_retry succeeds on first attempt."""
        def successful_function():
            return "success"
        
        result = retry_manager.execute_with_retry(successful_function)
        
        assert result == "success"
        assert mock_sleep.call_count == 0  # No sleep needed

    @patch('time.sleep')
    def test_execute_with_retry_success_after_retries(self, mock_sleep, retry_manager):
        """Test execute_with_retry succeeds after retries."""
        call_count = 0
        
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary error")
            return "success"
        
        result = retry_manager.execute_with_retry(flaky_function)
        
        assert result == "success"
        assert mock_sleep.call_count == 1  # One retry delay

    @patch('time.sleep')
    def test_execute_with_retry_failure_max_attempts(self, mock_sleep, retry_manager):
        """Test execute_with_retry fails after max attempts."""
        def always_fails():
            raise ConnectionError("Persistent error")
        
        with pytest.raises(ConnectionError) as exc_info:
            retry_manager.execute_with_retry(always_fails)
        
        assert "Persistent error" in str(exc_info.value)
        assert mock_sleep.call_count == 2  # 2 retry delays for 3 total attempts

    @patch('time.sleep')
    def test_execute_with_retry_non_retryable_exception(self, mock_sleep, retry_manager):
        """Test execute_with_retry with non-retryable exception."""
        def auth_error():
            raise AuthenticationError("test")
        
        with pytest.raises(AuthenticationError):
            retry_manager.execute_with_retry(auth_error)
        
        assert mock_sleep.call_count == 0  # No retries for non-retryable

    def test_execute_with_retry_function_with_args(self, retry_manager):
        """Test execute_with_retry with function arguments."""
        def add_numbers(a, b, multiplier=1):
            return (a + b) * multiplier
        
        result = retry_manager.execute_with_retry(
            add_numbers, 3, 4, multiplier=2
        )
        
        assert result == 14  # (3 + 4) * 2

    def test_callable_decorator(self, retry_manager):
        """Test RetryManager as decorator."""
        @retry_manager
        def test_function():
            return "decorated"
        
        result = test_function()
        assert result == "decorated"

    @patch('time.sleep')
    def test_decorator_with_retries(self, mock_sleep, custom_retry_manager):
        """Test decorator functionality with retries."""
        call_count = 0
        
        @custom_retry_manager
        def flaky_decorated():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Error")
            return "success"
        
        result = flaky_decorated()
        assert result == "success"
        assert mock_sleep.call_count == 1


class TestProviderRetryManager:
    def test_provider_retry_manager_barchart(self):
        """Test ProviderRetryManager with Barchart-specific policy."""
        manager = ProviderRetryManager("barchart")
        
        assert manager.provider_name == "barchart"
        assert manager.policy.max_attempts == 5
        assert manager.policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF_JITTER
        assert manager.policy.base_delay == 2.0
        assert manager.policy.max_delay == 120.0

    def test_provider_retry_manager_yahoo(self):
        """Test ProviderRetryManager with Yahoo-specific policy."""
        manager = ProviderRetryManager("yahoo")
        
        assert manager.provider_name == "yahoo"
        assert manager.policy.max_attempts == 3
        assert manager.policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert manager.policy.base_delay == 1.0
        assert manager.policy.max_delay == 30.0

    def test_provider_retry_manager_ibkr(self):
        """Test ProviderRetryManager with IBKR-specific policy."""
        manager = ProviderRetryManager("ibkr")
        
        assert manager.provider_name == "ibkr"
        assert manager.policy.max_attempts == 4
        assert manager.policy.strategy == RetryStrategy.LINEAR_BACKOFF
        assert manager.policy.base_delay == 1.5
        assert manager.policy.max_delay == 60.0

    def test_provider_retry_manager_unknown_provider(self):
        """Test ProviderRetryManager with unknown provider uses defaults."""
        manager = ProviderRetryManager("unknown")
        
        assert manager.provider_name == "unknown"
        assert manager.policy.max_attempts == 3  # Default
        assert manager.policy.strategy == RetryStrategy.EXPONENTIAL_BACKOFF_JITTER

    def test_provider_retry_manager_custom_policy_override(self):
        """Test ProviderRetryManager with custom policy override."""
        custom_policy = RetryPolicy(max_attempts=10, base_delay=5.0)
        manager = ProviderRetryManager("barchart", custom_policy)
        
        # Should use custom policy instead of provider-specific one
        assert manager.policy.max_attempts == 10
        assert manager.policy.base_delay == 5.0


class TestRetryDecorators:
    def test_retry_with_backoff_decorator(self):
        """Test retry_with_backoff decorator."""
        @retry_with_backoff(max_attempts=2, base_delay=0.01)
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"

    def test_retry_with_backoff_decorator_custom_strategy(self):
        """Test retry_with_backoff with custom strategy."""
        @retry_with_backoff(
            max_attempts=3,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.1
        )
        def test_function():
            return "fixed"
        
        result = test_function()
        assert result == "fixed"

    def test_provider_retry_decorator(self):
        """Test provider_retry decorator."""
        @provider_retry("yahoo")
        def test_function():
            return "provider_success"
        
        result = test_function()
        assert result == "provider_success"

    def test_provider_retry_decorator_with_overrides(self):
        """Test provider_retry decorator with parameter overrides."""
        @provider_retry("barchart", max_attempts=2, base_delay=0.1)
        def test_function():
            return "override_success"
        
        result = test_function()
        assert result == "override_success"

    @patch('time.sleep')
    def test_decorator_retry_behavior(self, mock_sleep):
        """Test decorator retry behavior."""
        call_count = 0
        
        @retry_with_backoff(max_attempts=2, base_delay=0.01)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Error")
            return "eventual_success"
        
        result = flaky_function()
        assert result == "eventual_success"
        assert mock_sleep.call_count == 1


class TestIntegration:
    @patch('time.sleep')
    def test_full_retry_workflow(self, mock_sleep):
        """Test complete retry workflow integration."""
        policy = RetryPolicy(
            max_attempts=3,
            strategy=RetryStrategy.FIXED_DELAY,
            base_delay=0.01
        )
        manager = RetryManager(policy)
        
        call_count = 0
        def unstable_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError(f"Attempt {call_count} failed")
            return f"Success after {call_count} attempts"
        
        result = manager.execute_with_retry(unstable_operation)
        
        assert "Success after 3 attempts" in result
        assert mock_sleep.call_count == 2  # 2 retries

    def test_retry_with_different_exception_types(self):
        """Test retry behavior with various exception types."""
        manager = RetryManager()
        
        # Test retryable exception gets retries
        @patch('time.sleep')
        def test_retryable(mock_sleep):
            def connection_error():
                raise ConnectionError("Network issue")
            
            with pytest.raises(ConnectionError):
                manager.execute_with_retry(connection_error)
            
            assert mock_sleep.call_count == 2  # Should retry
        
        test_retryable()
        
        # Test non-retryable exception doesn't get retries
        @patch('time.sleep')
        def test_non_retryable(mock_sleep):  
            def auth_error():
                raise AuthenticationError("test")
            
            with pytest.raises(AuthenticationError):
                manager.execute_with_retry(auth_error)
            
            assert mock_sleep.call_count == 0  # Should not retry
        
        test_non_retryable()