import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Any

from pandas import DataFrame

from vortex.models.instrument import Instrument
from vortex.models.period import Period, FrequencyAttributes
from vortex.exceptions.providers import (
    DataProviderError, DataNotFoundError, AllowanceLimitExceededError,
    VortexConnectionError as ConnectionError, AuthenticationError, RateLimitError
)
from vortex.core.error_handling.strategies import (
    StandardizedErrorHandler, ErrorContext, ErrorHandlingStrategy
)
from vortex.infrastructure.resilience.circuit_breaker import get_circuit_breaker, CircuitBreakerConfig
from vortex.core.correlation import with_correlation, CorrelationIdManager
from .metrics import get_metrics_collector, ProviderMetricsCollector
from retrying import retry
import logging




class HistoricalDataResult(enum.Enum):
    NONE = 1
    OK = 2
    EXISTS = 3
    EXCEED = 4
    LOW = 5


def should_retry(exception: Exception) -> bool:
    """Determine if an exception should trigger a retry.
    
    Standardized retry logic for all providers:
    
    Do not retry for:
    - Data not found (permanent condition)
    - Allowance limits exceeded (need to wait or upgrade)
    - Authentication failures (need credential fix)
    - Configuration/validation errors (permanent condition)
    
    Do retry for:
    - Connection errors (transient network issues)
    - Rate limit errors (temporary API throttling)
    - General data provider errors (may be transient)
    """
    # Never retry these permanent failures
    permanent_failures = (
        DataNotFoundError, 
        AllowanceLimitExceededError, 
        AuthenticationError,
        ValueError,  # Configuration/validation errors
        TypeError,   # Programming errors
        AttributeError,  # Programming errors
    )
    
    return not isinstance(exception, permanent_failures)


class DataProvider(ABC):
    """Enhanced abstract base class for all data providers.
    
    This class provides default implementations for common provider functionality,
    standardized error handling, circuit breaker integration, and observability.
    
    Note: This class is aligned with the DataProviderProtocol to ensure
    consistency between interface definition and implementation.
    """

    def __init__(self, circuit_breaker_config: Optional[CircuitBreakerConfig] = None):
        """Initialize the data provider with enhanced capabilities."""
        self.logger = logging.getLogger(self.__class__.__name__)
        self._error_handler = StandardizedErrorHandler(self.logger)
        # Standard Python loggers don't support direct structured logging
        # Always use string formatting approach for compatibility
        self._has_structured_logging = False
        
        # Initialize circuit breaker for this provider
        cb_config = circuit_breaker_config or CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60,
            success_threshold=2,
            monitored_exceptions=(DataProviderError, ConnectionError, RateLimitError)
        )
        self._circuit_breaker = get_circuit_breaker(
            f"provider_{self.get_name().lower()}", cb_config
        )
        
        # Initialize metrics collector for this provider
        self._metrics_collector = get_metrics_collector(self.get_name().lower())

    def _log_with_context(self, level: str, message: str, **extra_data):
        """Log message with context, handling both structured and standard loggers."""
        if self._has_structured_logging:
            # Use structured logging with extra parameter - pass as 'extra' dict
            getattr(self.logger, level)(message, extra=extra_data)
        else:
            # Format as string for standard logger
            context_parts = [f"{k}={v}" for k, v in extra_data.items() if v is not None]
            if context_parts:
                full_message = f"{message} ({', '.join(context_parts)})"
            else:
                full_message = message
            getattr(self.logger, level)(full_message)

    def __str__(self) -> str:
        """String representation of the provider."""
        return self.get_name()

    @abstractmethod
    def get_name(self) -> str:
        """Get the provider name.
        
        Returns:
            The name of this data provider
        """
        pass

    def login(self) -> None:
        """Authenticate with the data provider.
        
        Default implementation is a no-op for providers that don't require authentication.
        Providers requiring authentication should override this method.
        """
        pass

    def logout(self) -> None:
        """End the session with the data provider.
        
        Default implementation is a no-op for providers that don't require session management.
        Providers with sessions should override this method.
        """
        pass

    def get_supported_timeframes(self) -> List[Period]:
        """Get list of supported time periods.
        
        Default implementation extracts periods from frequency attributes.
        
        Returns:
            List of Period objects supported by this provider
        """
        freq_dict = self._get_frequency_attr_dict()
        return list(freq_dict.keys())

    def get_max_range(self, period: Period) -> Optional[timedelta]:
        """Get maximum date range for a given period.
        
        Args:
            period: The time period to check
            
        Returns:
            Maximum timedelta for the period, or None if unlimited
        """
        freq_dict = self._get_frequency_attr_dict()
        freq_attr = freq_dict.get(period)
        return freq_attr.max_window if freq_attr else None

    def get_min_start(self, period: Period) -> Optional[datetime]:
        """Get minimum start date for a given period.
        
        Args:
            period: The time period to check
            
        Returns:
            Minimum start datetime for the period, or None if no limit
        """
        freq_dict = self._get_frequency_attr_dict()
        freq_attr = freq_dict.get(period)
        return freq_attr.get_min_start() if freq_attr else None

    @with_correlation(operation="fetch_historical_data")
    def fetch_historical_data(self,
                              instrument: Instrument,
                              period: Period,
                              start_date: datetime, end_date: datetime) -> Optional[DataFrame]:
        """Fetch historical data with enhanced error handling and circuit breaker protection.
        
        This method includes retry logic, circuit breaker protection, correlation tracking,
        and standardized error handling.
        
        Args:
            instrument: The financial instrument to fetch data for
            period: The time period/frequency for the data
            start_date: Start date for the data range
            end_date: End date for the data range
            
        Returns:
            DataFrame with OHLCV data, or None if no data available
            
        Raises:
            DataProviderError: For provider-specific errors
            DataNotFoundError: When no data is available
            ConnectionError: For network connectivity issues
        """
        correlation_id = CorrelationIdManager.get_current_id()
        
        # Add operation context for observability
        CorrelationIdManager.add_context_metadata(
            provider=self.get_name(),
            symbol=getattr(instrument, 'symbol', str(instrument)),
            period=str(period),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat()
        )
        
        self._log_with_context(
            "info",
            f"Starting data fetch for {getattr(instrument, 'symbol', str(instrument))}",
            provider=self.get_name(),
            correlation_id=correlation_id,
            period=str(period)
        )
        
        # Validate period support BEFORE retry mechanism to avoid retrying validation errors
        freq_dict = self._get_frequency_attr_dict()
        freq_attr = freq_dict.get(period)
        if freq_attr is None:
            # Use standardized error handling for validation errors (no retry)
            validation_error = ValueError(f"Period {period} is not supported by provider {self.get_name()}")
            return self._handle_provider_error(
                validation_error,
                "fetch_historical_data",
                ErrorHandlingStrategy.FAIL_FAST,
                instrument=instrument,
                period=period,
                correlation_id=correlation_id
            )
        
        # Track the entire operation with metrics
        with self._metrics_collector.track_operation(
            'fetch_historical_data',
            correlation_id=correlation_id,
            symbol=getattr(instrument, 'symbol', str(instrument)),
            period=str(period)
        ):
            return self._fetch_historical_data_with_retry(
                instrument, freq_attr, start_date, end_date, correlation_id
            )

    @retry(wait_exponential_multiplier=2000,
           stop_max_attempt_number=5,
           retry_on_exception=should_retry)
    def _fetch_historical_data_with_retry(self,
                                          instrument: Instrument,
                                          freq_attr: FrequencyAttributes,
                                          start_date: datetime,
                                          end_date: datetime,
                                          correlation_id: str) -> Optional[DataFrame]:
        """Internal method that handles the retryable portion of data fetching.
        
        This method only includes operations that should be retried (network calls, etc.)
        and excludes validation errors that should fail immediately.
        """
        try:
            # Use circuit breaker for the actual fetch operation
            result = self._circuit_breaker.call(
                self._fetch_historical_data_with_validation,
                instrument, freq_attr, start_date, end_date, correlation_id
            )
            
            self._log_with_context(
                "info",
                f"Data fetch completed successfully",
                provider=self.get_name(),
                correlation_id=correlation_id,
                rows_fetched=len(result) if result is not None else 0
            )
            
            return result
            
        except Exception as e:
            self._log_with_context(
                "error",
                f"Data fetch failed: {str(e)}",
                provider=self.get_name(),
                correlation_id=correlation_id,
                exception_type=type(e).__name__
            )
            
            # Enhanced exception context
            if hasattr(e, 'add_context'):
                e.add_context(
                    provider=self.get_name(),
                    symbol=getattr(instrument, 'symbol', str(instrument)),
                    operation="fetch_historical_data",
                    correlation_id=correlation_id
                )
            
            # Use standardized error handling
            return self._handle_provider_error(
                e,
                "fetch_historical_data",
                ErrorHandlingStrategy.FAIL_FAST,
                instrument=instrument,
                period=freq_attr.frequency,
                correlation_id=correlation_id
            )

    def validate_configuration(self) -> bool:
        """Validate provider configuration.
        
        Default implementation returns True for providers that don't require configuration.
        Providers with specific configuration requirements should override this method.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        return True

    def get_required_config_fields(self) -> List[str]:
        """Get list of required configuration fields.
        
        Default implementation returns empty list for providers that don't require configuration.
        Providers with configuration requirements should override this method.
        
        Returns:
            List of required configuration field names
        """
        return []

    def _validate_fetched_data(
        self, 
        df: 'DataFrame', 
        instrument: 'Instrument', 
        period: 'Period',
        start_date=None,
        end_date=None
    ) -> 'DataFrame':
        """Standardized data validation for all providers.
        
        Performs consistent validation across all providers:
        1. Empty data validation
        2. Required column validation  
        3. Data type validation
        4. Data quality checks
        
        Args:
            df: DataFrame to validate
            instrument: Instrument that was fetched
            period: Time period that was fetched
            start_date: Optional start date for context
            end_date: Optional end date for context
            
        Returns:
            DataFrame: Validated DataFrame
            
        Raises:
            DataNotFoundError: If data is empty or insufficient
            DataProviderError: If validation fails with unrecoverable errors
        """
        import logging
        from vortex.models.columns import (
            validate_required_columns, get_provider_expected_columns,
            validate_column_data_types, ValidationIssueType
        )
        
        logger = logging.getLogger(__name__)
        provider_name = self.get_name().lower()
        
        # 1. Check for empty data (critical - always fail fast)
        if df is None or df.empty:
            raise self._create_data_not_found_error(
                instrument, period, start_date, end_date,
                f"{self.get_name()} returned empty dataset"
            )
        
        # 2. Validate required columns (critical - always fail fast)  
        required_cols, optional_cols = get_provider_expected_columns(provider_name)
        missing_cols, found_cols = validate_required_columns(df.columns, required_cols, case_insensitive=True)
        if missing_cols:
            from vortex.exceptions.providers import DataProviderError
            symbol = instrument.get_symbol() if hasattr(instrument, 'get_symbol') else str(instrument)
            raise DataProviderError(
                provider=self.get_name().lower(),
                message=f"Data validation failed: Missing required columns {missing_cols} "
                        f"for {symbol}. Found columns: {list(df.columns)}"
            )
        
        # 3. Log missing optional columns (informational only)
        missing_optional = set(optional_cols) - set(df.columns)
        if missing_optional:
            logger.debug(f"{self.get_name()}: Missing optional columns {missing_optional}")
        
        # 4. Perform data type validation (quality - warn but continue)
        try:
            is_valid, issues = validate_column_data_types(df, strict=False)
            if issues:
                # Categorize issues by severity
                critical_issues = [issue for issue in issues if issue.type in [
                    ValidationIssueType.INDEX_TYPE_MISMATCH,
                    ValidationIssueType.COLUMN_TYPE_MISMATCH
                ]]
                quality_issues = [issue for issue in issues if issue not in critical_issues]
                
                # Critical data type issues - log as warnings but continue
                for issue in critical_issues:
                    logger.warning(f"{self.get_name()} data type issue: {issue}")
                
                # Quality issues - log as debug
                for issue in quality_issues:
                    logger.debug(f"{self.get_name()} data quality issue: {issue}")
                    
        except Exception as validation_error:
            # Don't fail the entire fetch due to validation infrastructure issues
            logger.warning(f"{self.get_name()} data type validation failed: {validation_error}")
        
        logger.debug(f"{self.get_name()} data validation passed: {df.shape} rows, columns: {list(df.columns)}")
        return df

    def _handle_provider_error(
        self, 
        error: Exception, 
        operation: str, 
        strategy: ErrorHandlingStrategy = ErrorHandlingStrategy.FAIL_FAST,
        **context_kwargs
    ) -> Any:
        """Standardized error handling for provider operations.
        
        Args:
            error: The exception that occurred
            operation: Name of the operation that failed
            strategy: Error handling strategy to use
            **context_kwargs: Additional context information
            
        Returns:
            Result based on the error handling strategy
        """
        # Filter context_kwargs to only include parameters ErrorContext accepts
        valid_context_keys = {'error_type', 'default_value', 'correlation_id'}
        filtered_kwargs = {k: v for k, v in context_kwargs.items() if k in valid_context_keys}
        
        context = ErrorContext(
            operation=operation,
            component=self.get_name(),
            **filtered_kwargs
        )
        return self._error_handler.handle_error(error, context, strategy)

    def _create_data_not_found_error(
        self, 
        instrument: Instrument, 
        period: Period, 
        start_date: datetime, 
        end_date: datetime,
        details: Optional[str] = None
    ) -> DataNotFoundError:
        """Create a standardized DataNotFoundError with consistent context.
        
        Args:
            instrument: The instrument for which data was not found
            period: The period for which data was requested
            start_date: Start date of the request
            end_date: End date of the request
            details: Optional additional details
            
        Returns:
            DataNotFoundError with consistent formatting
        """
        symbol = instrument.get_symbol() if hasattr(instrument, 'get_symbol') else str(instrument)
        error = DataNotFoundError(
            provider=self.get_name().lower(),
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date
        )
        if details:
            error.technical_details = details
        return error

    def _create_connection_error(self, details: str, operation: Optional[str] = None) -> ConnectionError:
        """Create a standardized connection error.
        
        Args:
            details: Details about the connection failure
            operation: Optional operation that was being performed
            
        Returns:
            ConnectionError with consistent formatting
        """
        if operation:
            details = f"{operation}: {details}"
        return ConnectionError(self.get_name().lower(), details)

    def _create_auth_error(self, details: str, http_code: Optional[int] = None) -> AuthenticationError:
        """Create a standardized authentication error.
        
        Args:
            details: Details about the authentication failure
            http_code: Optional HTTP status code
            
        Returns:
            AuthenticationError with consistent formatting
        """
        return AuthenticationError(self.get_name().lower(), details, http_code)

    def _fetch_historical_data_with_validation(
        self, 
        instrument: Instrument, 
        frequency_attributes: FrequencyAttributes,
        start_date: datetime, 
        end_date: datetime,
        correlation_id: Optional[str] = None
    ) -> Optional[DataFrame]:
        """Wrapper method that adds validation to the abstract fetch method.
        
        This method calls the provider-specific implementation and applies
        standardized validation to the results.
        
        Args:
            instrument: The financial instrument to fetch data for
            frequency_attributes: Detailed frequency information
            start_date: Start date for the data range
            end_date: End date for the data range
            correlation_id: Optional correlation ID for tracking
            
        Returns:
            DataFrame with validated OHLCV data, or None if no data available
        """
        try:
            # Call the provider-specific implementation
            result = self._fetch_historical_data(instrument, frequency_attributes, start_date, end_date)
            
            # Apply standardized validation if data was returned
            if result is not None and not result.empty:
                result = self._validate_fetched_data(
                    result, instrument, frequency_attributes.frequency, start_date, end_date
                )
            
            return result
            
        except Exception as e:
            # Log with correlation context
            self._log_with_context(
                "error",
                f"Provider-specific fetch failed: {str(e)}",
                provider=self.get_name(),
                correlation_id=correlation_id,
                exception_type=type(e).__name__
            )
            raise

    def get_health_status(self) -> dict:
        """Get comprehensive provider health status.
        
        Returns:
            Dictionary with health status information including metrics
        """
        metrics = self._metrics_collector.get_metrics()
        active_ops = self._metrics_collector.get_active_operations()
        
        return {
            'provider': self.get_name(),
            'circuit_breaker': self._circuit_breaker.stats,
            'metrics': metrics.to_dict(),
            'active_operations': active_ops,
            'health_score': self._calculate_health_score(),
            'metrics_health_score': self._metrics_collector.get_health_score()
        }
    
    def _calculate_health_score(self) -> float:
        """Calculate a health score based on circuit breaker metrics."""
        cb_stats = self._circuit_breaker.stats
        
        if cb_stats['state'] == 'closed':
            # Healthy state - score based on failure rate
            failure_rate = cb_stats.get('failure_rate', 0.0)
            return max(0.0, 100.0 - (failure_rate * 100))
        elif cb_stats['state'] == 'half_open':
            # Testing recovery - medium score
            return 50.0
        else:
            # Open circuit - unhealthy
            return 0.0
    
    def get_metrics(self):
        """Get provider metrics."""
        return self._metrics_collector.get_metrics()
    
    def get_active_operations(self):
        """Get currently active operations."""
        return self._metrics_collector.get_active_operations()
    
    def reset_metrics(self):
        """Reset provider metrics (useful for testing)."""
        self._metrics_collector.reset_metrics()

    def _get_frequency_attr_dict(self) -> dict:
        """Build a dictionary mapping periods to their frequency attributes.
        
        Returns:
            Dictionary with Period objects as keys and FrequencyAttributes as values
        """
        freq_dict = {attr.frequency: attr for attr in self._get_frequency_attributes()}
        return freq_dict

    @abstractmethod
    def _get_frequency_attributes(self) -> List[FrequencyAttributes]:
        """Get the frequency attributes supported by this provider.
        
        This is an internal method that subclasses must implement to define
        the time periods and their properties supported by the provider.
        
        Returns:
            List of FrequencyAttributes defining supported periods
        """
        pass

    @abstractmethod
    def _fetch_historical_data(self,
                               instrument: Instrument,
                               frequency_attributes: FrequencyAttributes,
                               start_date: datetime, end_date: datetime) -> Optional[DataFrame]:
        """Internal method to fetch historical data.
        
        This is the actual implementation method that subclasses must implement.
        It receives frequency attributes instead of just the period for more context.
        
        Args:
            instrument: The financial instrument to fetch data for
            frequency_attributes: Detailed frequency information including properties
            start_date: Start date for the data range
            end_date: End date for the data range
            
        Returns:
            DataFrame with OHLCV data, or None if no data available
        """
        pass
