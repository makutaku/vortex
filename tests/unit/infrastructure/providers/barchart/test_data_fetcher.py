"""
Tests for Barchart data fetcher module.

Provides comprehensive coverage for data fetching strategies and methodology
used by the Barchart provider for different instrument types.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import pandas as pd
import requests

from vortex.infrastructure.providers.barchart.data_fetcher import BarchartDataFetcher
from vortex.infrastructure.providers.barchart.auth import BarchartAuth
from vortex.infrastructure.providers.barchart.client import BarchartClient
from vortex.infrastructure.providers.barchart.parser import BarchartParser
from vortex.models.future import Future
from vortex.models.stock import Stock
from vortex.models.forex import Forex
from vortex.models.period import Period, FrequencyAttributes
from vortex.exceptions.providers import DataNotFoundError, DataProviderError


@pytest.fixture
def mock_auth():
    """Mock Barchart authentication."""
    auth = Mock(spec=BarchartAuth)
    auth.session = Mock(spec=requests.Session)
    return auth


@pytest.fixture
def mock_client():
    """Mock Barchart client."""
    return Mock(spec=BarchartClient)


@pytest.fixture
def mock_parser():
    """Mock Barchart parser."""
    parser = Mock(spec=BarchartParser)
    parser.convert_downloaded_csv_to_df.return_value = pd.DataFrame({
        'Date': ['2024-01-01'], 
        'Open': [100.0], 
        'High': [105.0], 
        'Low': [99.0], 
        'Close': [104.0]
    })
    return parser


@pytest.fixture
def data_fetcher(mock_auth, mock_client, mock_parser):
    """Create BarchartDataFetcher instance with mocked dependencies."""
    return BarchartDataFetcher(mock_auth, mock_client, mock_parser)


@pytest.fixture
def frequency_attributes():
    """Create frequency attributes for testing."""
    return FrequencyAttributes(frequency=Period.Daily)


@pytest.fixture
def date_range():
    """Create date range for testing."""
    return datetime(2024, 1, 1), datetime(2024, 1, 31)


class TestBarchartDataFetcher:
    """Test BarchartDataFetcher initialization and basic functionality."""
    
    def test_initialization(self, mock_auth, mock_client, mock_parser):
        """Test BarchartDataFetcher initialization."""
        fetcher = BarchartDataFetcher(mock_auth, mock_client, mock_parser)
        
        assert fetcher.auth is mock_auth
        assert fetcher.client is mock_client
        assert fetcher.parser is mock_parser
        assert fetcher.logger is not None


class TestFetchHistoricalData:
    """Test fetch_historical_data method and instrument type routing."""
    
    def test_fetch_future_data(self, data_fetcher, frequency_attributes, date_range):
        """Test fetching data for Future instruments."""
        future = Mock(spec=Future)
        future.get_symbol.return_value = "GC=F"
        
        with patch.object(data_fetcher, '_fetch_future_data') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            result = data_fetcher.fetch_historical_data(
                future, frequency_attributes, *date_range
            )
            
            mock_fetch.assert_called_once_with(
                future, frequency_attributes, *date_range
            )
    
    def test_fetch_stock_data(self, data_fetcher, frequency_attributes, date_range):
        """Test fetching data for Stock instruments."""
        stock = Mock(spec=Stock)
        stock.get_symbol.return_value = "AAPL"
        
        with patch.object(data_fetcher, '_fetch_stock_data') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            result = data_fetcher.fetch_historical_data(
                stock, frequency_attributes, *date_range
            )
            
            mock_fetch.assert_called_once_with(
                stock, frequency_attributes, *date_range
            )
    
    def test_fetch_forex_data(self, data_fetcher, frequency_attributes, date_range):
        """Test fetching data for Forex instruments."""
        forex = Mock(spec=Forex)
        forex.get_symbol.return_value = "EURUSD=X"
        
        with patch.object(data_fetcher, '_fetch_forex_data') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            result = data_fetcher.fetch_historical_data(
                forex, frequency_attributes, *date_range
            )
            
            mock_fetch.assert_called_once_with(
                forex, frequency_attributes, *date_range
            )
    
    def test_fetch_generic_data(self, data_fetcher, frequency_attributes, date_range):
        """Test fetching data for generic string instruments."""
        instrument = "GENERIC_SYMBOL"
        
        with patch.object(data_fetcher, '_fetch_generic_data') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            result = data_fetcher.fetch_historical_data(
                instrument, frequency_attributes, *date_range
            )
            
            mock_fetch.assert_called_once_with(
                instrument, frequency_attributes, *date_range
            )


class TestInstrumentSpecificFetching:
    """Test instrument-specific data fetching methods."""
    
    def test_fetch_future_data_with_symbol_method(self, data_fetcher, frequency_attributes, date_range):
        """Test future data fetching when instrument has get_symbol method."""
        future = Mock(spec=Future)
        future.get_symbol.return_value = "GC=F"
        
        with patch.object(data_fetcher, '_fetch_via_bc_utils_download') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            result = data_fetcher._fetch_future_data(future, frequency_attributes, *date_range)
            
            mock_fetch.assert_called_once_with(
                "GC=F", frequency_attributes, *date_range, "US/Central"
            )
    
    def test_fetch_future_data_with_str_fallback(self, data_fetcher, frequency_attributes, date_range):
        """Test future data fetching with string fallback."""
        future = Mock(spec=Future)
        del future.get_symbol  # Remove the method to test fallback
        future.__str__ = Mock(return_value="GC")
        
        with patch.object(data_fetcher, '_fetch_via_bc_utils_download') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            result = data_fetcher._fetch_future_data(future, frequency_attributes, *date_range)
            
            # Should use str(instrument) as fallback
            mock_fetch.assert_called_once()
            args = mock_fetch.call_args[0]
            assert str(future) in str(args[0])
    
    def test_fetch_stock_data_with_symbol_method(self, data_fetcher, frequency_attributes, date_range):
        """Test stock data fetching when instrument has get_symbol method."""
        stock = Mock(spec=Stock)
        stock.get_symbol.return_value = "AAPL"
        
        with patch.object(data_fetcher, '_fetch_via_bc_utils_download') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            result = data_fetcher._fetch_stock_data(stock, frequency_attributes, *date_range)
            
            mock_fetch.assert_called_once_with(
                "AAPL", frequency_attributes, *date_range, "America/New_York"
            )
    
    def test_fetch_forex_data_with_symbol_method(self, data_fetcher, frequency_attributes, date_range):
        """Test forex data fetching when instrument has get_symbol method."""
        forex = Mock(spec=Forex)
        forex.get_symbol.return_value = "EURUSD=X"
        
        with patch.object(data_fetcher, '_fetch_via_bc_utils_download') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            result = data_fetcher._fetch_forex_data(forex, frequency_attributes, *date_range)
            
            mock_fetch.assert_called_once_with(
                "EURUSD=X", frequency_attributes, *date_range, "America/New_York"
            )
    
    def test_fetch_generic_data_string_instrument(self, data_fetcher, frequency_attributes, date_range):
        """Test generic data fetching with string instrument."""
        instrument = "TEST_SYMBOL"
        
        with patch.object(data_fetcher, '_fetch_via_bc_utils_download') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            result = data_fetcher._fetch_generic_data(instrument, frequency_attributes, *date_range)
            
            mock_fetch.assert_called_once_with(
                "TEST_SYMBOL", frequency_attributes, *date_range, "America/New_York"
            )


class TestBcUtilsDownloadMethod:
    """Test the bc-utils download methodology."""
    
    def test_successful_bc_utils_download(self, data_fetcher, frequency_attributes, date_range):
        """Test successful bc-utils download flow."""
        # Mock successful home page response
        home_response = Mock()
        home_response.status_code = 200
        home_response.text = '<meta name="csrf-token" content="test-csrf-token">'
        data_fetcher.auth.session.get.return_value = home_response
        
        # Mock successful data download
        with patch.object(data_fetcher, '_perform_bc_utils_download') as mock_download:
            mock_download.return_value = pd.DataFrame()
            
            result = data_fetcher._fetch_via_bc_utils_download(
                "AAPL", frequency_attributes, *date_range, "America/New_York"
            )
            
            # Verify home page was requested
            data_fetcher.auth.session.get.assert_called_once()
            
            # Verify download was attempted with extracted token
            mock_download.assert_called_once()
            assert "test-csrf-token" in str(mock_download.call_args)
    
    def test_home_page_request_failure(self, data_fetcher, frequency_attributes, date_range):
        """Test handling of home page request failure."""
        # Mock failed home page response
        home_response = Mock()
        home_response.status_code = 500
        data_fetcher.auth.session.get.return_value = home_response
        
        result = data_fetcher._fetch_via_bc_utils_download(
            "AAPL", frequency_attributes, *date_range, "America/New_York"
        )
        
        assert result is None
    
    def test_csrf_token_not_found(self, data_fetcher, frequency_attributes, date_range):
        """Test handling when CSRF token is not found."""
        # Mock home page response without CSRF token
        home_response = Mock()
        home_response.status_code = 200
        home_response.text = '<html><body>No token here</body></html>'
        data_fetcher.auth.session.get.return_value = home_response
        
        with patch.object(data_fetcher, '_extract_csrf_token') as mock_extract:
            mock_extract.return_value = None
            
            result = data_fetcher._fetch_via_bc_utils_download(
                "AAPL", frequency_attributes, *date_range, "America/New_York"
            )
            
            assert result is None
    
    def test_download_exception_handling(self, data_fetcher, frequency_attributes, date_range):
        """Test exception handling during download."""
        # Mock exception during home page request
        data_fetcher.auth.session.get.side_effect = requests.RequestException("Network error")
        
        with pytest.raises(DataProviderError) as exc_info:
            data_fetcher._fetch_via_bc_utils_download(
                "AAPL", frequency_attributes, *date_range, "America/New_York"
            )
        
        assert "Failed to fetch data for AAPL" in str(exc_info.value)


class TestPerformBcUtilsDownload:
    """Test the actual bc-utils download implementation."""
    
    def test_successful_download(self, data_fetcher, frequency_attributes, date_range):
        """Test successful bc-utils download with proper payload."""
        # Mock successful download response
        download_response = Mock()
        download_response.status_code = 200
        download_response.text = "Date,Open,High,Low,Close\n2024-01-01,100,105,99,104"
        data_fetcher.auth.session.post.return_value = download_response
        
        # Mock parser
        expected_df = pd.DataFrame({'Date': ['2024-01-01'], 'Close': [104.0]})
        with patch.object(data_fetcher, '_process_bc_utils_csv_response') as mock_process:
            mock_process.return_value = expected_df
            
            result = data_fetcher._perform_bc_utils_download(
                "AAPL", frequency_attributes, *date_range, "test-csrf-token"
            )
            
            # Verify POST request was made
            data_fetcher.auth.session.post.assert_called_once()
            call_args = data_fetcher.auth.session.post.call_args
            
            # Verify payload contains required fields
            payload = call_args[1]['data']
            assert payload['_token'] == 'test-csrf-token'
            assert payload['symbol'] == 'AAPL'
            assert payload['startDate'] == '2024-01-01'
            assert payload['endDate'] == '2024-01-31'
            assert 'method' in payload
            
            # Verify headers
            headers = call_args[1]['headers']
            assert headers['X-CSRF-TOKEN'] == 'test-csrf-token'
            assert 'Content-Type' in headers
            
            assert result is expected_df
    
    def test_download_404_not_found(self, data_fetcher, frequency_attributes, date_range):
        """Test handling of 404 Not Found response."""
        # Mock 404 response
        download_response = Mock()
        download_response.status_code = 404
        data_fetcher.auth.session.post.return_value = download_response
        
        with pytest.raises(DataNotFoundError) as exc_info:
            data_fetcher._perform_bc_utils_download(
                "INVALID", frequency_attributes, *date_range, "test-csrf-token"
            )
        
        assert "No data found for INVALID" in str(exc_info.value)
    
    def test_download_other_error_status(self, data_fetcher, frequency_attributes, date_range):
        """Test handling of other HTTP error statuses."""
        # Mock 500 response
        download_response = Mock()
        download_response.status_code = 500
        data_fetcher.auth.session.post.return_value = download_response
        
        result = data_fetcher._perform_bc_utils_download(
            "AAPL", frequency_attributes, *date_range, "test-csrf-token"
        )
        
        assert result is None
    
    def test_download_exception(self, data_fetcher, frequency_attributes, date_range):
        """Test exception handling during download POST."""
        # Mock exception during POST request
        data_fetcher.auth.session.post.side_effect = requests.RequestException("Connection timeout")
        
        result = data_fetcher._perform_bc_utils_download(
            "AAPL", frequency_attributes, *date_range, "test-csrf-token"
        )
        
        assert result is None
    
    def test_daily_frequency_file_suffix(self, data_fetcher, frequency_attributes, date_range):
        """Test that daily frequency uses correct file suffix."""
        download_response = Mock()
        download_response.status_code = 200
        download_response.text = "csv,data"
        data_fetcher.auth.session.post.return_value = download_response
        
        with patch.object(data_fetcher, '_process_bc_utils_csv_response'):
            data_fetcher._perform_bc_utils_download(
                "AAPL", frequency_attributes, *date_range, "test-csrf-token"
            )
            
            call_args = data_fetcher.auth.session.post.call_args
            payload = call_args[1]['data']
            assert "Daily_Historical+Data" in payload['fileName']
    
    def test_intraday_frequency_file_suffix(self, data_fetcher, date_range):
        """Test that intraday frequency uses correct file suffix."""
        hourly_freq = FrequencyAttributes(frequency=Period.Hourly)
        
        download_response = Mock()
        download_response.status_code = 200
        download_response.text = "csv,data"
        data_fetcher.auth.session.post.return_value = download_response
        
        with patch.object(data_fetcher, '_process_bc_utils_csv_response'):
            data_fetcher._perform_bc_utils_download(
                "AAPL", hourly_freq, *date_range, "test-csrf-token"
            )
            
            call_args = data_fetcher.auth.session.post.call_args
            payload = call_args[1]['data']
            assert "Intraday_Historical+Data" in payload['fileName']


class TestCSRFTokenExtraction:
    """Test CSRF token extraction from HTML."""
    
    def test_extract_csrf_token_success(self, data_fetcher):
        """Test successful CSRF token extraction."""
        home_response = Mock()
        home_response.text = '<html><meta name="csrf-token" content="valid-token-123"></html>'
        
        token = data_fetcher._extract_csrf_token(home_response)
        
        assert token == "valid-token-123"
    
    def test_extract_csrf_token_not_found(self, data_fetcher):
        """Test CSRF token extraction when token not found."""
        home_response = Mock()
        home_response.text = '<html><body>No token here</body></html>'
        
        token = data_fetcher._extract_csrf_token(home_response)
        
        assert token is None
    
    def test_extract_csrf_token_parsing_error(self, data_fetcher):
        """Test CSRF token extraction with parsing error."""
        home_response = Mock()
        home_response.text = "Invalid HTML <<<"
        
        token = data_fetcher._extract_csrf_token(home_response)
        
        assert token is None


class TestFrequencyConversion:
    """Test frequency conversion methods."""
    
    def test_get_bc_utils_frequency_mapping(self, data_fetcher):
        """Test bc-utils frequency string conversion."""
        # Test Period objects with value attribute
        daily_period = Mock()
        daily_period.value = "1d"
        assert data_fetcher._get_bc_utils_frequency(daily_period) == "daily"
        
        hourly_period = Mock()
        hourly_period.value = "1h"
        assert data_fetcher._get_bc_utils_frequency(hourly_period) == "hourly"
        
        weekly_period = Mock()
        weekly_period.value = "1W"
        assert data_fetcher._get_bc_utils_frequency(weekly_period) == "weekly"
        
        monthly_period = Mock()
        monthly_period.value = "1M"
        assert data_fetcher._get_bc_utils_frequency(monthly_period) == "monthly"
    
    def test_get_bc_utils_frequency_string_input(self, data_fetcher):
        """Test bc-utils frequency conversion with string input."""
        assert data_fetcher._get_bc_utils_frequency("daily") == "daily"
        assert data_fetcher._get_bc_utils_frequency("hourly") == "hourly"
        assert data_fetcher._get_bc_utils_frequency("unknown") == "daily"  # default
    
    def test_get_barchart_period_mapping(self, data_fetcher):
        """Test Barchart period string conversion."""
        # Test Period objects with value attribute
        daily_period = Mock()
        daily_period.value = "1d"
        assert data_fetcher._get_barchart_period(daily_period) == "daily"
        
        hourly_period = Mock()
        hourly_period.value = "1h"
        assert data_fetcher._get_barchart_period(hourly_period) == "hourly"
    
    def test_get_barchart_period_string_input(self, data_fetcher):
        """Test Barchart period conversion with string input."""
        assert data_fetcher._get_barchart_period("daily") == "daily"
        assert data_fetcher._get_barchart_period("1d") == "daily"
        assert data_fetcher._get_barchart_period("unknown") == "daily"  # default
    
    def test_get_barchart_period_case_insensitive(self, data_fetcher):
        """Test Barchart period conversion is case insensitive."""
        assert data_fetcher._get_barchart_period("DAILY") == "daily"
        assert data_fetcher._get_barchart_period("Daily") == "daily"


class TestCSVResponseProcessing:
    """Test CSV response processing."""
    
    def test_process_csv_response_success(self, data_fetcher, mock_parser):
        """Test successful CSV response processing."""
        csv_data = "Date,Open,High,Low,Close\n2024-01-01,100,105,99,104"
        expected_df = pd.DataFrame({'Date': ['2024-01-01'], 'Close': [104.0]})
        mock_parser.convert_downloaded_csv_to_df.return_value = expected_df
        
        result = data_fetcher._process_bc_utils_csv_response(
            csv_data, "daily", "America/New_York"
        )
        
        # Verify parser was called with correct Period
        mock_parser.convert_downloaded_csv_to_df.assert_called_once()
        call_args = mock_parser.convert_downloaded_csv_to_df.call_args[0]
        assert call_args[0] == Period.Daily  # period
        assert call_args[1] == csv_data      # csv_data
        assert call_args[2] == "America/New_York"  # timezone
        
        assert result is expected_df
    
    def test_process_csv_response_frequency_mapping(self, data_fetcher, mock_parser):
        """Test CSV processing with different frequency mappings."""
        csv_data = "test,data"
        mock_parser.convert_downloaded_csv_to_df.return_value = pd.DataFrame()
        
        # Test hourly frequency
        data_fetcher._process_bc_utils_csv_response(csv_data, "hourly", "America/New_York")
        call_args = mock_parser.convert_downloaded_csv_to_df.call_args[0]
        assert call_args[0] == Period.Hourly
        
        # Test weekly frequency
        data_fetcher._process_bc_utils_csv_response(csv_data, "weekly", "America/New_York")
        call_args = mock_parser.convert_downloaded_csv_to_df.call_args[0]
        assert call_args[0] == Period.Weekly
        
        # Test monthly frequency
        data_fetcher._process_bc_utils_csv_response(csv_data, "monthly", "America/New_York")
        call_args = mock_parser.convert_downloaded_csv_to_df.call_args[0]
        assert call_args[0] == Period.Monthly
        
        # Test unknown frequency (defaults to daily)
        data_fetcher._process_bc_utils_csv_response(csv_data, "unknown", "America/New_York")
        call_args = mock_parser.convert_downloaded_csv_to_df.call_args[0]
        assert call_args[0] == Period.Daily
    
    def test_process_csv_response_parser_exception(self, data_fetcher, mock_parser):
        """Test CSV processing when parser raises exception."""
        csv_data = "invalid,csv,data"
        mock_parser.convert_downloaded_csv_to_df.side_effect = ValueError("Invalid CSV format")
        
        result = data_fetcher._process_bc_utils_csv_response(
            csv_data, "daily", "America/New_York"
        )
        
        assert result is None


class TestDataFetcherIntegration:
    """Integration tests for complete data fetching workflows."""
    
    def test_end_to_end_future_download(self, data_fetcher, mock_parser):
        """Test end-to-end future data download."""
        future = Mock(spec=Future)
        future.get_symbol.return_value = "GC=F"
        
        # Mock successful authentication and download
        home_response = Mock()
        home_response.status_code = 200
        home_response.text = '<meta name="csrf-token" content="token-123">'
        data_fetcher.auth.session.get.return_value = home_response
        
        download_response = Mock()
        download_response.status_code = 200
        download_response.text = "csv,data"
        data_fetcher.auth.session.post.return_value = download_response
        
        expected_df = pd.DataFrame({'Date': ['2024-01-01'], 'Close': [104.0]})
        mock_parser.convert_downloaded_csv_to_df.return_value = expected_df
        
        frequency_attrs = FrequencyAttributes(frequency=Period.Daily)
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        result = data_fetcher.fetch_historical_data(future, frequency_attrs, start_date, end_date)
        
        # Verify the complete flow
        assert data_fetcher.auth.session.get.called
        assert data_fetcher.auth.session.post.called
        assert mock_parser.convert_downloaded_csv_to_df.called
        assert result is expected_df
    
    def test_end_to_end_download_with_data_not_found(self, data_fetcher):
        """Test end-to-end download that results in 404 Not Found."""
        stock = Mock(spec=Stock)
        stock.get_symbol.return_value = "INVALID"
        
        # Mock successful home page but 404 download
        home_response = Mock()
        home_response.status_code = 200
        home_response.text = '<meta name="csrf-token" content="token-123">'
        data_fetcher.auth.session.get.return_value = home_response
        
        download_response = Mock()
        download_response.status_code = 404
        data_fetcher.auth.session.post.return_value = download_response
        
        frequency_attrs = FrequencyAttributes(frequency=Period.Daily)
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        with pytest.raises(DataNotFoundError):
            data_fetcher.fetch_historical_data(stock, frequency_attrs, start_date, end_date)


class TestDataFetcherEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_instrument_without_get_symbol_method(self, data_fetcher, frequency_attributes, date_range):
        """Test handling of instruments without get_symbol method."""
        # Create a mock object without get_symbol method
        instrument = Mock()
        instrument.__str__ = Mock(return_value="TEST_SYMBOL")
        
        with patch.object(data_fetcher, '_fetch_via_bc_utils_download') as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()
            
            # Test with future type but no get_symbol method
            instrument.__class__ = Future
            data_fetcher._fetch_future_data(instrument, frequency_attributes, *date_range)
            
            # Should use str(instrument) as fallback
            mock_fetch.assert_called_once()
    
    def test_empty_csv_response(self, data_fetcher, mock_parser):
        """Test handling of empty CSV response."""
        mock_parser.convert_downloaded_csv_to_df.return_value = pd.DataFrame()
        
        result = data_fetcher._process_bc_utils_csv_response("", "daily", "America/New_York")
        
        # Should handle empty response gracefully
        assert isinstance(result, pd.DataFrame)
    
    def test_malformed_html_csrf_extraction(self, data_fetcher):
        """Test CSRF extraction with malformed HTML."""
        home_response = Mock()
        home_response.text = "<html><meta name='csrf-token' content='token-without-quotes'></html>"
        
        token = data_fetcher._extract_csrf_token(home_response)
        
        # Should still extract token correctly
        assert token == "token-without-quotes"