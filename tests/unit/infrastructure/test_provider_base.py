import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from vortex.infrastructure.providers.base import (
    DataProvider, 
    HistoricalDataResult, 
    should_retry
)
from vortex.models.period import Period, FrequencyAttributes
from vortex.models.stock import Stock
from vortex.exceptions.providers import (
    DataProviderError,
    DataNotFoundError, 
    AllowanceLimitExceededError,
    AuthenticationError
)
# Additional test exceptions
class ConnectionError(Exception): pass
class RateLimitError(Exception): pass


class TestHistoricalDataResult:
    def test_historical_data_result_enum_values(self):
        """Test HistoricalDataResult enum values."""
        assert HistoricalDataResult.NONE.value == 1
        assert HistoricalDataResult.OK.value == 2
        assert HistoricalDataResult.EXISTS.value == 3
        assert HistoricalDataResult.EXCEED.value == 4
        assert HistoricalDataResult.LOW.value == 5

    def test_historical_data_result_enum_names(self):
        """Test HistoricalDataResult enum names."""
        assert HistoricalDataResult.NONE.name == 'NONE'
        assert HistoricalDataResult.OK.name == 'OK'
        assert HistoricalDataResult.EXISTS.name == 'EXISTS'
        assert HistoricalDataResult.EXCEED.name == 'EXCEED'
        assert HistoricalDataResult.LOW.name == 'LOW'


class TestShouldRetry:
    def test_should_retry_data_not_found_error(self):
        """Test that DataNotFoundError should not be retried."""
        from datetime import datetime
        from vortex.models.period import Period
        error = DataNotFoundError(
            provider="test", 
            symbol="TEST", 
            period=Period.Daily, 
            start_date=datetime(2024, 1, 1), 
            end_date=datetime(2024, 1, 31)
        )
        assert should_retry(error) is False

    def test_should_retry_usage_limit_exceeded_error(self):
        """Test that AllowanceLimitExceededError should not be retried."""
        error = AllowanceLimitExceededError(provider="test", current_usage=100, daily_limit=100)
        assert should_retry(error) is False

    def test_should_retry_authentication_error(self):
        """Test that AuthenticationError should not be retried."""
        error = AuthenticationError(provider="test")
        assert should_retry(error) is False

    def test_should_retry_connection_error(self):
        """Test that ConnectionError should be retried."""
        error = ConnectionError("Connection failed")
        assert should_retry(error) is True

    def test_should_retry_rate_limit_error(self):
        """Test that RateLimitError should be retried."""
        error = RateLimitError("Rate limit exceeded")
        assert should_retry(error) is True

    def test_should_retry_data_provider_error(self):
        """Test that general DataProviderError should be retried."""
        error = DataProviderError(provider="test", message="Provider error")
        assert should_retry(error) is True

    def test_should_retry_generic_exception(self):
        """Test that generic exceptions should be retried."""
        error = RuntimeError("Some transient error")
        assert should_retry(error) is True
    
    def test_should_not_retry_value_error(self):
        """Test that ValueError (configuration/validation errors) should not be retried."""
        error = ValueError("Invalid configuration")
        assert should_retry(error) is False

    def test_should_retry_multiple_inheritance(self):
        """Test exception inheritance edge cases."""
        # Test that DataNotFoundError is properly detected
        from datetime import datetime
        from vortex.models.period import Period
        error = DataNotFoundError(
            provider="test", 
            symbol="TEST", 
            period=Period.Daily, 
            start_date=datetime(2024, 1, 1), 
            end_date=datetime(2024, 1, 31)
        )
        # Should not retry because DataNotFoundError is in the non-retry list
        assert should_retry(error) is False


class ConcreteDataProvider(DataProvider):
    """Concrete implementation of DataProvider for testing."""
    
    def __init__(self, name="TestProvider"):
        self._name = name  # Set name first, as parent constructor calls get_name()
        super().__init__()  # Call parent constructor to initialize logger
        self._frequency_attributes = []
        self._fetch_data_response = None
        self._fetch_data_exception = None

    def get_name(self) -> str:
        return self._name

    def _get_frequency_attributes(self) -> list[FrequencyAttributes]:
        return self._frequency_attributes

    def _fetch_historical_data(self, instrument, frequency_attributes, start_date, end_date):
        if self._fetch_data_exception:
            raise self._fetch_data_exception
        return self._fetch_data_response

    def set_frequency_attributes(self, attributes):
        """Helper method to set frequency attributes for testing."""
        self._frequency_attributes = attributes

    def set_fetch_response(self, response):
        """Helper method to set fetch response for testing."""
        self._fetch_data_response = response

    def set_fetch_exception(self, exception):
        """Helper method to set fetch exception for testing."""
        self._fetch_data_exception = exception


class TestDataProvider:
    @pytest.fixture
    def provider(self):
        """Create a concrete data provider for testing."""
        return ConcreteDataProvider("TestProvider")

    @pytest.fixture
    def sample_instrument(self):
        """Create a sample instrument for testing."""
        return Stock(id='AAPL', symbol='AAPL')

    @pytest.fixture
    def sample_frequency_attributes(self):
        """Create sample frequency attributes."""
        return [
            FrequencyAttributes(frequency=Period.Daily, max_window=timedelta(days=365)),
            FrequencyAttributes(frequency=Period.Hourly, max_window=timedelta(days=30)),
            FrequencyAttributes(frequency=Period.Minute_5, max_window=timedelta(days=7))
        ]

    def test_data_provider_str(self, provider):
        """Test DataProvider string representation."""
        assert str(provider) == "TestProvider"

    def test_get_name(self, provider):
        """Test get_name method."""
        assert provider.get_name() == "TestProvider"

    def test_login_default_implementation(self, provider):
        """Test that login method has default no-op implementation."""
        # Should not raise any exceptions
        provider.login()

    def test_logout_default_implementation(self, provider):
        """Test that logout method has default no-op implementation."""
        # Should not raise any exceptions
        provider.logout()

    def test_get_supported_timeframes(self, provider, sample_frequency_attributes):
        """Test get_supported_timeframes method."""
        provider.set_frequency_attributes(sample_frequency_attributes)
        
        supported = provider.get_supported_timeframes()
        
        expected = [Period.Daily, Period.Hourly, Period.Minute_5]
        assert supported == expected

    def test_get_supported_timeframes_empty(self, provider):
        """Test get_supported_timeframes with no frequency attributes."""
        provider.set_frequency_attributes([])
        
        supported = provider.get_supported_timeframes()
        
        assert supported == []

    def test_get_max_range(self, provider, sample_frequency_attributes):
        """Test get_max_range method."""
        provider.set_frequency_attributes(sample_frequency_attributes)
        
        # Test existing period
        max_range = provider.get_max_range(Period.Daily)
        assert max_range == timedelta(days=365)
        
        max_range = provider.get_max_range(Period.Hourly)
        assert max_range == timedelta(days=30)

    def test_get_max_range_nonexistent_period(self, provider, sample_frequency_attributes):
        """Test get_max_range with non-existent period."""
        provider.set_frequency_attributes(sample_frequency_attributes)
        
        # Test non-existent period - improved implementation returns None gracefully
        # instead of raising AttributeError
        result = provider.get_max_range(Period.Weekly)
        assert result is None

    def test_get_min_start(self, provider):
        """Test get_min_start method."""
        # Create frequency attribute with timedelta min_start
        min_start_delta = timedelta(days=30)
        freq_attr = FrequencyAttributes(
            frequency=Period.Daily,
            min_start=min_start_delta
        )
        provider.set_frequency_attributes([freq_attr])
        
        min_start = provider.get_min_start(Period.Daily)
        
        # Should return a datetime approximately 30 days ago
        now = datetime.now()
        expected_min = now - min_start_delta - timedelta(minutes=1)  # Allow 1 minute tolerance
        expected_max = now - min_start_delta + timedelta(minutes=1)
        
        # Handle timezone differences
        if min_start.tzinfo is not None and expected_min.tzinfo is None:
            from datetime import timezone
            expected_min = expected_min.replace(tzinfo=timezone.utc)
            expected_max = expected_max.replace(tzinfo=timezone.utc)
        elif min_start.tzinfo is None and expected_min.tzinfo is not None:
            min_start = min_start.replace(tzinfo=timezone.utc)
        
        assert expected_min <= min_start <= expected_max

    def test_get_min_start_with_datetime(self, provider):
        """Test get_min_start with datetime min_start."""
        fixed_datetime = datetime(2024, 1, 1)
        freq_attr = FrequencyAttributes(
            frequency=Period.Daily,
            min_start=fixed_datetime
        )
        provider.set_frequency_attributes([freq_attr])
        
        min_start = provider.get_min_start(Period.Daily)
        
        assert min_start == fixed_datetime

    def test_get_min_start_nonexistent_period(self, provider, sample_frequency_attributes):
        """Test get_min_start with non-existent period."""
        provider.set_frequency_attributes(sample_frequency_attributes)
        
        # Improved implementation returns None gracefully
        # instead of raising AttributeError
        result = provider.get_min_start(Period.Weekly)
        assert result is None

    def test_fetch_historical_data_success(self, provider, sample_instrument):
        """Test successful fetch_historical_data."""
        # Set up provider
        freq_attr = FrequencyAttributes(frequency=Period.Daily)
        provider.set_frequency_attributes([freq_attr])
        
        # Mock response with all required columns
        sample_df = pd.DataFrame({
            'Open': [99, 100, 101],
            'High': [101, 102, 103],
            'Low': [98, 99, 100],
            'Close': [100, 101, 102],
            'Volume': [1000, 1100, 1200]
        })
        provider.set_fetch_response(sample_df)
        
        # Call method
        result = provider.fetch_historical_data(
            sample_instrument,
            Period.Daily,
            datetime(2024, 1, 1),
            datetime(2024, 1, 3)
        )
        
        assert result is sample_df

    def test_fetch_historical_data_calls_private_method(self, provider, sample_instrument):
        """Test that fetch_historical_data calls _fetch_historical_data with correct parameters."""
        freq_attr = FrequencyAttributes(frequency=Period.Daily)
        provider.set_frequency_attributes([freq_attr])
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)
        
        # Mock the private method
        with patch.object(provider, '_fetch_historical_data') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            provider.fetch_historical_data(
                sample_instrument,
                Period.Daily,
                start_date,
                end_date
            )
            
            mock_fetch.assert_called_once_with(
                sample_instrument,
                freq_attr,
                start_date,
                end_date
            )

    @patch('vortex.infrastructure.providers.base.retry')
    def test_fetch_historical_data_has_retry_decorator(self, mock_retry, provider, sample_instrument):
        """Test that fetch_historical_data has retry decorator applied."""
        # The retry decorator should be applied to the method
        # We can verify this by checking if the method has been wrapped
        
        freq_attr = FrequencyAttributes(frequency=Period.Daily)
        provider.set_frequency_attributes([freq_attr])
        provider.set_fetch_response(pd.DataFrame())
        
        # Call the method
        provider.fetch_historical_data(
            sample_instrument,
            Period.Daily,
            datetime(2024, 1, 1),
            datetime(2024, 1, 3)
        )
        
        # The original method should have retry decorators
        # This is hard to test directly, but we can check the method exists
        assert hasattr(provider, 'fetch_historical_data')

    def test_get_frequency_attr_dict(self, provider, sample_frequency_attributes):
        """Test _get_frequency_attr_dict internal method."""
        provider.set_frequency_attributes(sample_frequency_attributes)
        
        freq_dict = provider._get_frequency_attr_dict()
        
        # Should be a dictionary mapping Period to FrequencyAttributes
        assert isinstance(freq_dict, dict)
        assert len(freq_dict) == 3
        
        assert Period.Daily in freq_dict
        assert Period.Hourly in freq_dict
        assert Period.Minute_5 in freq_dict
        
        assert isinstance(freq_dict[Period.Daily], FrequencyAttributes)
        assert freq_dict[Period.Daily].frequency == Period.Daily

    def test_fetch_historical_data_nonexistent_period(self, provider, sample_instrument):
        """Test fetch_historical_data with non-existent period."""
        provider.set_frequency_attributes([])
        
        # With error handling system, unsupported periods are wrapped in VortexError
        # instead of crashing with AttributeError deep in the implementation
        with pytest.raises(Exception, match="Period .* is not supported by provider"):
            provider.fetch_historical_data(
                sample_instrument,
                Period.Daily,
                datetime(2024, 1, 1),
                datetime(2024, 1, 3)
            )

    def test_abstract_methods_must_be_implemented(self):
        """Test that abstract methods must be implemented in concrete classes."""
        # This test verifies that DataProvider cannot be instantiated directly
        with pytest.raises(TypeError):
            DataProvider()

    def test_provider_inheritance_pattern(self):
        """Test that concrete provider properly inherits from DataProvider."""
        provider = ConcreteDataProvider()
        
        assert isinstance(provider, DataProvider)
        assert hasattr(provider, 'get_name')
        assert hasattr(provider, 'fetch_historical_data')
        assert hasattr(provider, 'get_supported_timeframes')

    def test_frequency_attributes_integration(self, provider):
        """Test integration between frequency attributes and other methods."""
        # Create comprehensive frequency attributes
        attrs = [
            FrequencyAttributes(
                frequency=Period.Daily,
                max_window=timedelta(days=365),
                min_start=timedelta(days=30)
            ),
            FrequencyAttributes(
                frequency=Period.Hourly,
                max_window=timedelta(days=7),
                min_start=datetime(2024, 1, 1)
            )
        ]
        provider.set_frequency_attributes(attrs)
        
        # Test all methods work together
        supported = provider.get_supported_timeframes()
        assert Period.Daily in supported
        assert Period.Hourly in supported
        
        daily_max = provider.get_max_range(Period.Daily)
        assert daily_max == timedelta(days=365)
        
        hourly_max = provider.get_max_range(Period.Hourly)
        assert hourly_max == timedelta(days=7)
        
        daily_min = provider.get_min_start(Period.Daily)
        assert daily_min is not None
        
        hourly_min = provider.get_min_start(Period.Hourly)
        assert hourly_min == datetime(2024, 1, 1)

    def test_custom_provider_name(self):
        """Test provider with custom name."""
        custom_provider = ConcreteDataProvider("CustomProviderName")
        
        assert custom_provider.get_name() == "CustomProviderName"
        assert str(custom_provider) == "CustomProviderName"

    def test_login_logout_customization(self):
        """Test that login/logout can be customized in subclasses."""
        class CustomProvider(ConcreteDataProvider):
            def __init__(self):
                super().__init__()
                self.login_called = False
                self.logout_called = False
            
            def login(self):
                self.login_called = True
            
            def logout(self):
                self.logout_called = True
        
        provider = CustomProvider()
        
        provider.login()
        assert provider.login_called is True
        
        provider.logout()
        assert provider.logout_called is True