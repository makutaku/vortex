"""
Example of integrating resilience patterns into data providers.

This module demonstrates how to use the new resilience system (circuit breakers,
retry logic, correlation IDs, and error recovery) in data provider implementations.
"""

from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import pandas as pd

from .data_provider import DataProvider
from ..instruments.instrument import Instrument
from ..instruments.period import FrequencyAttributes
from ..exceptions import (
    DataProviderError, AuthenticationError, ConnectionError,
    RateLimitError, DataNotFoundError
)
from ..resilience.circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
from ..resilience.retry import provider_retry, RetryStrategy
from ..resilience.correlation import with_correlation, CorrelationIdManager
from ..resilience.recovery import ErrorRecoveryManager, DataProviderRecoveryPolicy
from ..logging import get_logger

logger = get_logger(__name__)


class ResilientDataProvider(DataProvider):
    """
    Example data provider with comprehensive resilience patterns.
    
    Demonstrates integration of:
    - Circuit breakers for failure isolation
    - Intelligent retry with exponential backoff
    - Correlation ID tracking
    - Error recovery strategies
    - Structured error logging
    """
    
    def __init__(self, provider_name: str, fallback_providers: Optional[list] = None):
        self.provider_name = provider_name
        self.fallback_providers = fallback_providers or []
        
        # Initialize circuit breaker with provider-specific config
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
            monitored_exceptions=(ConnectionError, DataProviderError)
        )
        self.circuit_breaker = get_circuit_breaker(f"provider_{provider_name}", cb_config)
        
        # Initialize error recovery manager
        recovery_policy = DataProviderRecoveryPolicy(
            max_retry_attempts=3,
            fallback_providers=self.fallback_providers
        )
        self.recovery_manager = ErrorRecoveryManager(recovery_policy)
        
        logger.info(f"ResilientDataProvider initialized",
                   provider=provider_name,
                   fallback_providers=self.fallback_providers)
    
    def get_name(self) -> str:
        return self.provider_name
    
    @with_correlation(operation="provider_login")
    def login(self):
        """Login with resilience patterns."""
        correlation_id = CorrelationIdManager.get_current_id()
        
        try:
            # Add context about the operation
            CorrelationIdManager.add_context_metadata(
                provider=self.provider_name,
                operation_type="authentication"
            )
            
            # Use circuit breaker for login
            return self.circuit_breaker.call(self._perform_login)
            
        except Exception as e:
            logger.error("Login failed",
                        provider=self.provider_name,
                        correlation_id=correlation_id,
                        exception=str(e))
            
            # Enhance exception with context
            if hasattr(e, 'add_context'):
                e.add_context(
                    provider=self.provider_name,
                    operation="login",
                    correlation_id=correlation_id
                )
            raise
    
    def _perform_login(self):
        """Actual login implementation (placeholder)."""
        # This would contain the actual login logic
        # For demo purposes, we'll simulate various failure scenarios
        import random
        
        rand = random.random()
        if rand < 0.1:  # 10% chance of connection error
            raise ConnectionError(
                self.provider_name,
                "Unable to establish connection to authentication server",
                technical_details="Connection timeout after 30 seconds"
            )
        elif rand < 0.15:  # 5% chance of auth error
            raise AuthenticationError(
                self.provider_name,
                "Invalid credentials provided",
                http_code=401
            )
        elif rand < 0.2:  # 5% chance of rate limit
            raise RateLimitError(
                self.provider_name,
                wait_time=120,
                daily_limit=1000
            )
        
        # Successful login
        logger.info("Login successful", provider=self.provider_name)
    
    @provider_retry(
        provider_name="resilient_provider",
        max_attempts=4,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF_JITTER,
        base_delay=1.0,
        max_delay=30.0
    )
    @with_correlation(operation="fetch_data")
    def _fetch_historical_data(
        self,
        instrument: Instrument, 
        frequency_attributes: FrequencyAttributes,
        start_date: datetime, 
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical data with comprehensive resilience.
        
        This method demonstrates:
        - Retry logic with exponential backoff
        - Circuit breaker protection
        - Correlation ID tracking
        - Error context enhancement
        - Recovery strategy integration
        """
        correlation_id = CorrelationIdManager.get_current_id()
        
        # Add operation context
        CorrelationIdManager.add_context_metadata(
            provider=self.provider_name,
            symbol=instrument.symbol if hasattr(instrument, 'symbol') else 'unknown',
            period=str(frequency_attributes.frequency),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        logger.info("Starting data fetch",
                   provider=self.provider_name,
                   symbol=getattr(instrument, 'symbol', 'unknown'),
                   correlation_id=correlation_id)
        
        try:
            # Use circuit breaker for the actual data fetch
            result = self.circuit_breaker.call(
                self._perform_data_fetch,
                instrument,
                frequency_attributes,
                start_date,
                end_date
            )
            
            logger.info("Data fetch completed successfully",
                       provider=self.provider_name,
                       correlation_id=correlation_id,
                       rows_fetched=len(result) if result is not None else 0)
            
            return result
            
        except Exception as e:
            logger.error("Data fetch failed",
                        provider=self.provider_name,
                        correlation_id=correlation_id,
                        exception_type=type(e).__name__,
                        exception_message=str(e))
            
            # Enhance exception with comprehensive context
            if hasattr(e, 'add_context'):
                e.add_context(
                    provider=self.provider_name,
                    symbol=getattr(instrument, 'symbol', 'unknown'),
                    operation="fetch_historical_data",
                    correlation_id=correlation_id,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat()
                )
            
            # Attempt error recovery if this is a recoverable error
            try:
                recovery_result = self.recovery_manager.attempt_recovery(
                    self._perform_data_fetch,
                    e,
                    {
                        'provider': self.provider_name,
                        'operation': 'fetch_historical_data',
                        'correlation_id': correlation_id
                    },
                    instrument,
                    frequency_attributes,
                    start_date,
                    end_date
                )
                
                if recovery_result.success:
                    logger.info("Data fetch recovered successfully",
                               provider=self.provider_name,
                               correlation_id=correlation_id,
                               recovery_strategy=recovery_result.strategy_used.value)
                    # Note: In a real implementation, you'd return the recovered data
                    # This would require modifying the recovery manager to capture results
                
            except Exception as recovery_error:
                logger.error("Data fetch recovery failed",
                           provider=self.provider_name,
                           correlation_id=correlation_id,
                           recovery_exception=str(recovery_error))
            
            raise
    
    def _perform_data_fetch(
        self,
        instrument: Instrument,
        frequency_attributes: FrequencyAttributes, 
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """Actual data fetch implementation (placeholder)."""
        # This would contain the actual data fetching logic
        # For demo purposes, we'll simulate various scenarios
        import random
        
        symbol = getattr(instrument, 'symbol', 'UNKNOWN')
        
        rand = random.random()
        if rand < 0.05:  # 5% chance of connection error
            raise ConnectionError(
                self.provider_name,
                f"Failed to connect to data API for {symbol}",
                technical_details="Network timeout during data request"
            )
        elif rand < 0.1:  # 5% chance of rate limit
            raise RateLimitError(
                self.provider_name,
                wait_time=60,
                daily_limit=500
            )
        elif rand < 0.15:  # 5% chance of data not found
            from ..instruments.period import Period
            raise DataNotFoundError(
                self.provider_name,
                symbol,
                frequency_attributes.frequency,
                start_date,
                end_date,
                http_code=404
            )
        elif rand < 0.2:  # 5% chance of generic provider error
            raise DataProviderError(
                self.provider_name,
                f"API error while fetching {symbol} data",
                technical_details="Internal server error (HTTP 500)"
            )
        
        # Successful data fetch - return mock data
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        if len(dates) == 0:
            return None
            
        # Create mock OHLCV data
        data = {
            'timestamp': dates,
            'open': [100.0 + i * 0.5 for i in range(len(dates))],
            'high': [105.0 + i * 0.5 for i in range(len(dates))],
            'low': [95.0 + i * 0.5 for i in range(len(dates))],
            'close': [102.0 + i * 0.5 for i in range(len(dates))],
            'volume': [1000000 + i * 10000 for i in range(len(dates))]
        }
        
        return pd.DataFrame(data)
    
    def _get_frequency_attributes(self) -> list[FrequencyAttributes]:
        """Return supported frequency attributes (placeholder)."""
        # This would return actual frequency attributes for the provider
        return []
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get provider health status including resilience metrics."""
        return {
            'provider': self.provider_name,
            'circuit_breaker': self.circuit_breaker.stats,
            'recovery_stats': self.recovery_manager.get_recovery_stats(),
            'fallback_providers': self.fallback_providers,
            'health_score': self._calculate_health_score()
        }
    
    def _calculate_health_score(self) -> float:
        """Calculate a health score based on circuit breaker metrics."""
        cb_stats = self.circuit_breaker.stats
        
        if cb_stats['state'] == 'closed':
            # Healthy state - score based on failure rate
            failure_rate = cb_stats['failure_rate']
            return max(0.0, 100.0 - (failure_rate * 100))
        elif cb_stats['state'] == 'half_open':
            # Testing recovery - medium score
            return 50.0
        else:
            # Open circuit - unhealthy
            return 0.0


# Example usage
def create_resilient_yahoo_provider() -> ResilientDataProvider:
    """Create a resilient Yahoo Finance provider with fallbacks."""
    return ResilientDataProvider(
        provider_name="yahoo",
        fallback_providers=["barchart", "alpha_vantage"]
    )


def create_resilient_barchart_provider() -> ResilientDataProvider:
    """Create a resilient Barchart provider with fallbacks.""" 
    return ResilientDataProvider(
        provider_name="barchart",
        fallback_providers=["yahoo", "ibkr"]
    )