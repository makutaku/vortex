import pytest
from datetime import datetime
from unittest.mock import Mock

from vortex.exceptions.providers import (
    DataProviderError,
    AuthenticationError,
    RateLimitError,
    VortexConnectionError,
    DataNotFoundError,
    AllowanceLimitExceededError
)
from vortex.exceptions.base import VortexError
from vortex.exceptions.templates import ErrorCodes


class TestDataProviderError:
    def test_basic_provider_error(self):
        """Test basic DataProviderError creation."""
        error = DataProviderError("barchart", "Test message")
        
        assert isinstance(error, VortexError)
        assert error.provider == "barchart"
        assert "Provider barchart: Test message" in str(error)

    def test_provider_error_with_help_text(self):
        """Test DataProviderError with help text."""
        error = DataProviderError("yahoo", "Test message", "Check your settings")
        
        assert error.help_text == "Check your settings"

    def test_provider_error_with_error_code(self):
        """Test DataProviderError with error code."""
        error = DataProviderError("ibkr", "Test message", error_code="TEST_001")
        
        assert error.error_code == "TEST_001"


class TestAuthenticationError:
    def test_basic_authentication_error(self):
        """Test basic AuthenticationError creation."""
        error = AuthenticationError("barchart")
        
        assert isinstance(error, DataProviderError)
        assert error.provider == "barchart"
        assert "Authentication failed" in str(error)
        assert error.error_code == ErrorCodes.PROVIDER_AUTH_FAILED

    def test_authentication_error_with_details(self):
        """Test AuthenticationError with details."""
        error = AuthenticationError("yahoo", "Invalid API key")
        
        assert "Authentication failed - Invalid API key" in str(error)

    def test_authentication_error_with_http_401(self):
        """Test AuthenticationError with HTTP 401."""
        error = AuthenticationError("barchart", "Unauthorized", 401)
        
        assert error.technical_details == "HTTP 401 Unauthorized - Invalid credentials"
        assert error.context["http_code"] == 401

    def test_authentication_error_with_http_403(self):
        """Test AuthenticationError with HTTP 403."""
        error = AuthenticationError("barchart", "Forbidden", 403)
        
        assert error.technical_details == "HTTP 403 Forbidden - Valid credentials but insufficient permissions"
        assert error.context["http_code"] == 403

    def test_authentication_error_with_http_429(self):
        """Test AuthenticationError with HTTP 429."""
        error = AuthenticationError("barchart", "Rate limited", 429)
        
        assert error.technical_details == "HTTP 429 Too Many Requests - Authentication rate limited"
        assert error.context["http_code"] == 429

    def test_authentication_error_with_unknown_http_code(self):
        """Test AuthenticationError with unknown HTTP code."""
        error = AuthenticationError("barchart", "Server error", 500)
        
        assert error.technical_details is None
        assert error.context["http_code"] == 500

    def test_authentication_error_recovery_suggestions(self):
        """Test that authentication error includes recovery suggestions."""
        error = AuthenticationError("barchart")
        
        assert error.user_action == "Run: vortex config --provider barchart --set-credentials"
        assert "Verify your barchart credentials" in error.help_text

    def test_authentication_error_context_updates(self):
        """Test that authentication error updates context correctly."""
        error = AuthenticationError("yahoo", "Invalid key", 401)
        
        assert error.context["provider"] == "yahoo"
        assert error.context["http_code"] == 401


class TestRateLimitError:
    def test_basic_rate_limit_error(self):
        """Test basic RateLimitError creation."""
        error = RateLimitError("barchart")
        
        assert isinstance(error, DataProviderError)
        assert error.provider == "barchart"
        assert "Rate limit exceeded" in str(error)

    def test_rate_limit_error_with_daily_limit(self):
        """Test RateLimitError with daily limit."""
        error = RateLimitError("yahoo", daily_limit=1000)
        
        assert "Rate limit exceeded (daily limit: 1000)" in str(error)

    def test_rate_limit_error_with_wait_time(self):
        """Test RateLimitError with wait time."""
        error = RateLimitError("barchart", wait_time=300)
        
        assert "suggested wait: 300 seconds" in error.help_text

    def test_rate_limit_error_with_both_params(self):
        """Test RateLimitError with both wait time and daily limit."""
        error = RateLimitError("ibkr", wait_time=60, daily_limit=500)
        
        assert "Rate limit exceeded (daily limit: 500)" in str(error)
        assert "suggested wait: 60 seconds" in error.help_text
        assert "check your ibkr subscription limits" in error.help_text

    def test_rate_limit_error_code(self):
        """Test RateLimitError has correct error code."""
        error = RateLimitError("barchart")
        
        assert error.error_code == "RATE_LIMIT"


class TestVortexConnectionError:
    def test_basic_connection_error(self):
        """Test basic VortexConnectionError creation."""
        error = VortexConnectionError("yahoo")
        
        assert isinstance(error, DataProviderError)
        assert error.provider == "yahoo"
        assert "Connection failed" in str(error)

    def test_connection_error_with_details(self):
        """Test VortexConnectionError with details."""
        error = VortexConnectionError("barchart", "Timeout after 30 seconds")
        
        assert "Connection failed: Timeout after 30 seconds" in str(error)

    def test_connection_error_help_text(self):
        """Test VortexConnectionError help text."""
        error = VortexConnectionError("ibkr", "Network unreachable")
        
        assert "Check your internet connection and ibkr service status" in error.help_text

    def test_connection_error_code(self):
        """Test VortexConnectionError has correct error code."""
        error = VortexConnectionError("yahoo")
        
        assert error.error_code == "CONNECTION_FAILED"


class TestDataNotFoundError:
    def test_basic_data_not_found_error(self):
        """Test basic DataNotFoundError creation."""
        mock_period = Mock()
        mock_period.__str__ = Mock(return_value="1d")
        
        start_date = datetime(2024, 1, 1, 10, 0, 0)
        end_date = datetime(2024, 1, 31, 16, 0, 0)
        
        error = DataNotFoundError("yahoo", "AAPL", mock_period, start_date, end_date)
        
        assert isinstance(error, DataProviderError)
        assert error.provider == "yahoo"
        assert error.symbol == "AAPL"
        assert error.period == mock_period
        assert error.start_date == start_date
        assert error.end_date == end_date
        
        expected_message = "No data found for AAPL (1d) from 2024-01-01 to 2024-01-31"
        assert expected_message in str(error)

    def test_data_not_found_error_with_http_code(self):
        """Test DataNotFoundError with HTTP code."""
        mock_period = Mock()
        mock_period.__str__ = Mock(return_value="1h")
        
        start_date = datetime(2024, 2, 1)
        end_date = datetime(2024, 2, 28)
        
        error = DataNotFoundError("barchart", "GC", mock_period, start_date, end_date, 404)
        
        assert error.http_code == 404
        assert "No data found for GC (1h) from 2024-02-01 to 2024-02-28 (HTTP 404)" in str(error)

    def test_data_not_found_error_help_text(self):
        """Test DataNotFoundError help text."""
        mock_period = Mock()
        mock_period.__str__ = Mock(return_value="5m")
        
        start_date = datetime(2024, 3, 1)
        end_date = datetime(2024, 3, 15)
        
        error = DataNotFoundError("ibkr", "ES", mock_period, start_date, end_date)
        
        expected_help = "Verify that ES is valid and data exists for the requested date range on ibkr"
        assert expected_help in error.help_text

    def test_data_not_found_error_code(self):
        """Test DataNotFoundError has correct error code."""
        mock_period = Mock()
        mock_period.__str__ = Mock(return_value="1d")
        
        error = DataNotFoundError("yahoo", "MSFT", mock_period, datetime.now(), datetime.now())
        
        assert error.error_code == "DATA_NOT_FOUND"

    def test_data_not_found_error_dataclass_behavior(self):
        """Test that DataNotFoundError behaves as expected with dataclass decorator."""
        mock_period = Mock()
        mock_period.__str__ = Mock(return_value="1d")
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        error = DataNotFoundError("yahoo", "GOOGL", mock_period, start_date, end_date, 404)
        
        # Test that all fields are accessible
        assert error.symbol == "GOOGL"
        assert error.period == mock_period
        assert error.start_date == start_date
        assert error.end_date == end_date
        assert error.http_code == 404
        assert error.provider == "yahoo"


class TestAllowanceLimitExceededError:
    def test_basic_allowance_limit_error(self):
        """Test basic AllowanceLimitExceededError creation."""
        error = AllowanceLimitExceededError("barchart", 150, 150)
        
        assert isinstance(error, DataProviderError)
        assert error.provider == "barchart"
        assert error.current_allowance == 150
        assert error.max_allowance == 150

    def test_allowance_limit_error_message(self):
        """Test AllowanceLimitExceededError message formatting."""
        error = AllowanceLimitExceededError("yahoo", 95, 100)
        
        assert "Allowance limit exceeded: 95/100" in str(error)

    def test_allowance_limit_error_help_text(self):
        """Test AllowanceLimitExceededError help text."""
        error = AllowanceLimitExceededError("ibkr", 200, 200)
        
        assert "Wait for allowance reset or upgrade your ibkr subscription" in error.help_text

    def test_allowance_limit_error_code(self):
        """Test AllowanceLimitExceededError has correct error code."""
        error = AllowanceLimitExceededError("barchart", 100, 100)
        
        assert error.error_code == "ALLOWANCE_EXCEEDED"

    def test_allowance_limit_error_attributes(self):
        """Test AllowanceLimitExceededError stores attributes correctly."""
        error = AllowanceLimitExceededError("yahoo", 75, 100)
        
        assert error.current_allowance == 75
        assert error.max_allowance == 100
        assert error.provider == "yahoo"


class TestProviderErrorInheritance:
    def test_all_provider_errors_inherit_from_data_provider_error(self):
        """Test that all provider errors inherit from DataProviderError."""
        mock_period = Mock()
        mock_period.__str__ = Mock(return_value="1d")
        
        errors = [
            AuthenticationError("test"),
            RateLimitError("test"),
            VortexConnectionError("test"),
            DataNotFoundError("test", "SYM", mock_period, datetime.now(), datetime.now()),
            AllowanceLimitExceededError("test", 10, 100)
        ]
        
        for error in errors:
            assert isinstance(error, DataProviderError)
            assert isinstance(error, VortexError)
            assert hasattr(error, 'provider')

    def test_all_provider_errors_have_provider_attribute(self):
        """Test that all provider errors have provider attribute."""
        mock_period = Mock()
        mock_period.__str__ = Mock(return_value="1d")
        
        errors = [
            ("auth", AuthenticationError("auth")),
            ("rate", RateLimitError("rate")),
            ("conn", VortexConnectionError("conn")),
            ("data", DataNotFoundError("data", "SYM", mock_period, datetime.now(), datetime.now())),
            ("allow", AllowanceLimitExceededError("allow", 10, 100))
        ]
        
        for expected_provider, error in errors:
            assert error.provider == expected_provider