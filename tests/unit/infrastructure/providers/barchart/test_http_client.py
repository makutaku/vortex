"""
Tests for Barchart-specific HTTP client functionality.
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pytest
import requests

from vortex.infrastructure.providers.barchart.http_client import BarchartHttpClient
from vortex.models.period import Period, FrequencyAttributes


class TestBarchartHttpClient:
    """Test Barchart HTTP client initialization and configuration."""
    
    def test_init(self):
        """Test BarchartHttpClient initialization."""
        mock_auth = Mock()
        mock_auth.session = Mock()
        
        client = BarchartHttpClient(mock_auth)
        
        assert client.base_url == 'https://www.barchart.com'
        assert client.auth_handler == mock_auth
        assert client.session == mock_auth.session
        assert client.DOWNLOAD_ENDPOINT == '/my/download'
        assert client.USAGE_ENDPOINT == '/my/download'
    
    def test_endpoints(self):
        """Test endpoint constants."""
        mock_auth = Mock()
        mock_auth.session = Mock()
        
        client = BarchartHttpClient(mock_auth)
        
        assert hasattr(client, 'DOWNLOAD_ENDPOINT')
        assert hasattr(client, 'USAGE_ENDPOINT')
        assert client.DOWNLOAD_ENDPOINT == client.USAGE_ENDPOINT


class TestDownloadData:
    """Test data download functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_auth = Mock()
        self.mock_auth.session = Mock()
        self.client = BarchartHttpClient(self.mock_auth)
        
        # Create test frequency attributes
        self.frequency_attributes = FrequencyAttributes(
            frequency=Period.Daily
        )
        
        self.start_date = datetime(2024, 1, 1)
        self.end_date = datetime(2024, 1, 31)
        self.xsrf_token = "test-xsrf-token"
        self.history_csrf_token = "test-history-csrf-token"
        self.symbol = "AAPL"
    
    @patch.object(BarchartHttpClient, 'post')
    def test_download_data_success(self, mock_post):
        """Test successful data download."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"Date,Open,High,Low,Close,Volume\n2024-01-01,100,110,95,105,1000"
        mock_post.return_value = mock_response
        
        response = self.client.download_data(
            self.symbol,
            self.frequency_attributes,
            self.start_date,
            self.end_date,
            self.xsrf_token,
            self.history_csrf_token
        )
        
        # Verify response
        assert response == mock_response
        assert response.status_code == 200
        
        # Verify post was called with correct parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == '/my/download'  # endpoint
        
        # Verify headers
        headers = call_args.kwargs['headers']
        assert headers['X-XSRF-TOKEN'] == self.xsrf_token
        assert headers['Accept'] == 'application/json'
        assert headers['Content-Type'] == 'application/x-www-form-urlencoded; charset=UTF-8'
        
        # Verify payload
        payload = call_args.kwargs['data']
        assert payload['_token'] == self.history_csrf_token
        assert payload['symbol'] == self.symbol
        assert payload['fileName'] == self.symbol
        assert payload['startDate'] == '01/01/2024'
        assert payload['endDate'] == '01/31/2024'
    
    @patch.object(BarchartHttpClient, 'post')
    def test_download_data_logging(self, mock_post):
        """Test download data logging."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test data"
        mock_post.return_value = mock_response
        
        with patch.object(self.client.logger, 'debug') as mock_debug:
            self.client.download_data(
                self.symbol,
                self.frequency_attributes,
                self.start_date,
                self.end_date,
                self.xsrf_token,
                self.history_csrf_token
            )
            
            # Verify logging
            mock_debug.assert_called_once()
            log_message = mock_debug.call_args[0][0]
            assert self.symbol in log_message
            assert "status=200" in log_message
            assert "size=9 bytes" in log_message


class TestCheckUsage:
    """Test usage checking functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_auth = Mock()
        self.mock_auth.session = Mock()
        self.client = BarchartHttpClient(self.mock_auth)
        self.xsrf_token = "test-xsrf-token"
        self.new_xsrf_token = "new-xsrf-token"
    
    @patch.object(BarchartHttpClient, 'post')
    def test_check_usage_success(self, mock_post):
        """Test successful usage check."""
        # Mock response
        usage_data = {"used": 10, "limit": 150, "remaining": 140}
        mock_response = Mock()
        mock_response.text = json.dumps(usage_data)
        mock_post.return_value = mock_response
        
        # Mock auth handler to return new token
        self.mock_auth.get_xsrf_token.return_value = self.new_xsrf_token
        
        result_data, result_token = self.client.check_usage(self.xsrf_token)
        
        # Verify results
        assert result_data == usage_data
        assert result_token == self.new_xsrf_token
        
        # Verify post was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == '/my/download'  # endpoint
        
        # Verify headers
        headers = call_args.kwargs['headers']
        assert headers['X-XSRF-TOKEN'] == self.xsrf_token
        
        # Verify payload
        payload = call_args.kwargs['data']
        assert payload == {'check': True}
    
    @patch.object(BarchartHttpClient, 'post')
    def test_check_usage_logging_context(self, mock_post):
        """Test usage check with logging context."""
        usage_data = {"used": 5, "limit": 150}
        mock_response = Mock()
        mock_response.text = json.dumps(usage_data)
        mock_post.return_value = mock_response
        self.mock_auth.get_xsrf_token.return_value = self.new_xsrf_token
        
        with patch.object(self.client.logger, 'debug') as mock_debug:
            self.client.check_usage(self.xsrf_token)
            
            # Verify debug logging
            mock_debug.assert_called_once()
            log_message = mock_debug.call_args[0][0]
            assert "Usage data:" in log_message
    
    @patch.object(BarchartHttpClient, 'post')
    def test_check_usage_json_parsing(self, mock_post):
        """Test JSON parsing in usage check."""
        # Complex usage data
        usage_data = {
            "used": 25,
            "limit": 150,
            "remaining": 125,
            "reset_time": "2024-01-01T00:00:00Z",
            "plan": "premium"
        }
        mock_response = Mock()
        mock_response.text = json.dumps(usage_data)
        mock_post.return_value = mock_response
        self.mock_auth.get_xsrf_token.return_value = self.new_xsrf_token
        
        result_data, _ = self.client.check_usage(self.xsrf_token)
        
        # Verify complex data is parsed correctly
        assert result_data == usage_data
        assert result_data["plan"] == "premium"
        assert result_data["reset_time"] == "2024-01-01T00:00:00Z"


class TestHeaderBuilding:
    """Test header building functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_auth = Mock()
        self.mock_auth.session = Mock()
        self.client = BarchartHttpClient(self.mock_auth)
        self.xsrf_token = "test-token"
    
    def test_build_download_headers(self):
        """Test download header construction."""
        headers = self.client._build_download_headers(self.xsrf_token)
        
        expected_headers = {
            'X-XSRF-TOKEN': self.xsrf_token,
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Referer': 'https://www.barchart.com/my/download',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        assert headers == expected_headers
    
    def test_build_usage_headers(self):
        """Test usage header construction."""
        headers = self.client._build_usage_headers(self.xsrf_token)
        
        # Usage headers should be identical to download headers
        expected_headers = self.client._build_download_headers(self.xsrf_token)
        assert headers == expected_headers
    
    def test_header_token_substitution(self):
        """Test that different tokens are properly substituted in headers."""
        token1 = "token-1"
        token2 = "token-2"
        
        headers1 = self.client._build_download_headers(token1)
        headers2 = self.client._build_download_headers(token2)
        
        assert headers1['X-XSRF-TOKEN'] == token1
        assert headers2['X-XSRF-TOKEN'] == token2
        assert headers1['X-XSRF-TOKEN'] != headers2['X-XSRF-TOKEN']


class TestPayloadBuilding:
    """Test payload building functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_auth = Mock()
        self.mock_auth.session = Mock()
        self.client = BarchartHttpClient(self.mock_auth)
        
        self.history_csrf_token = "csrf-token"
        self.symbol = "TSLA"
        self.start_date = datetime(2024, 6, 1)
        self.end_date = datetime(2024, 6, 30)
        
        self.frequency_attributes = FrequencyAttributes(
            frequency=Period.Hourly
        )
    
    def test_build_download_payload_basic(self):
        """Test basic download payload construction."""
        payload = self.client._build_download_payload(
            self.history_csrf_token,
            self.symbol,
            self.frequency_attributes,
            self.start_date,
            self.end_date
        )
        
        expected_payload = {
            '_token': self.history_csrf_token,
            'fileName': self.symbol,
            'symbol': self.symbol,
            'startDate': '06/01/2024',
            'endDate': '06/30/2024',
            'period': '1h',
            'maxRecords': '5000',
            'order': 'asc',
            'dividends': 'false',
            'backadjust': 'false',
            'dbar': '1',
            'custombar': '',
            'volume': 'true',
            'openInterest': 'true',
            'splits': 'true'
        }
        
        assert payload == expected_payload
    
    def test_build_download_payload_date_formatting(self):
        """Test date formatting in payload."""
        # Test different date
        start_date = datetime(2023, 12, 15)
        end_date = datetime(2024, 1, 5)
        
        payload = self.client._build_download_payload(
            self.history_csrf_token,
            self.symbol,
            self.frequency_attributes,
            start_date,
            end_date
        )
        
        assert payload['startDate'] == '12/15/2023'
        assert payload['endDate'] == '01/05/2024'
    
    def test_build_download_payload_frequency_attributes(self):
        """Test frequency attributes handling in payload."""
        # Test with different frequency
        weekly_attrs = FrequencyAttributes(
            frequency=Period.Weekly
        )
        
        payload = self.client._build_download_payload(
            self.history_csrf_token,
            self.symbol,
            weekly_attrs,
            self.start_date,
            self.end_date
        )
        
        assert payload['period'] == '1w'
        assert payload['maxRecords'] == '5000'
    
    def test_build_download_payload_symbol_handling(self):
        """Test symbol handling in payload."""
        symbols = ['AAPL', 'GC', 'ES', 'EURUSD']
        
        for symbol in symbols:
            payload = self.client._build_download_payload(
                self.history_csrf_token,
                symbol,
                self.frequency_attributes,
                self.start_date,
                self.end_date
            )
            
            assert payload['symbol'] == symbol
            assert payload['fileName'] == symbol
    
    def test_build_download_payload_fixed_values(self):
        """Test that fixed payload values remain constant."""
        payload = self.client._build_download_payload(
            self.history_csrf_token,
            self.symbol,
            self.frequency_attributes,
            self.start_date,
            self.end_date
        )
        
        # Verify fixed configuration values
        assert payload['order'] == 'asc'
        assert payload['dividends'] == 'false'
        assert payload['backadjust'] == 'false'
        assert payload['dbar'] == '1'
        assert payload['custombar'] == ''
        assert payload['volume'] == 'true'
        assert payload['openInterest'] == 'true'
        assert payload['splits'] == 'true'


class TestIntegration:
    """Test integration scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_auth = Mock()
        self.mock_auth.session = Mock()
        self.client = BarchartHttpClient(self.mock_auth)
    
    @patch.object(BarchartHttpClient, 'post')
    def test_full_download_workflow(self, mock_post):
        """Test complete download workflow."""
        # Setup
        symbol = "GOOGL"
        frequency_attrs = FrequencyAttributes(
            frequency=Period.Daily
        )
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 3, 31)
        xsrf_token = "workflow-xsrf-token"
        csrf_token = "workflow-csrf-token"
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"Date,Open,High,Low,Close,Volume\n2024-01-01,150,160,145,155,2000"
        mock_post.return_value = mock_response
        
        # Execute download
        response = self.client.download_data(
            symbol, frequency_attrs, start_date, end_date,
            xsrf_token, csrf_token
        )
        
        # Verify the complete flow
        assert response.status_code == 200
        assert len(response.content) > 0
        
        # Verify post call
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Verify endpoint
        assert call_args[0][0] == '/my/download'
        
        # Verify headers contain all required fields
        headers = call_args.kwargs['headers']
        required_headers = ['X-XSRF-TOKEN', 'Accept', 'Content-Type', 'Referer']
        for header in required_headers:
            assert header in headers
        
        # Verify payload contains all required fields  
        payload = call_args.kwargs['data']
        required_fields = ['_token', 'symbol', 'startDate', 'endDate', 'period']
        for field in required_fields:
            assert field in payload
    
    @patch.object(BarchartHttpClient, 'post')
    def test_full_usage_workflow(self, mock_post):
        """Test complete usage check workflow."""
        xsrf_token = "usage-xsrf-token"
        new_token = "new-usage-token"
        
        # Mock usage response
        usage_data = {"used": 50, "limit": 150, "remaining": 100}
        mock_response = Mock()
        mock_response.text = json.dumps(usage_data)
        mock_post.return_value = mock_response
        
        # Mock auth handler
        self.mock_auth.get_xsrf_token.return_value = new_token
        
        # Execute usage check
        result_data, result_token = self.client.check_usage(xsrf_token)
        
        # Verify results
        assert result_data == usage_data
        assert result_token == new_token
        
        # Verify auth handler was called
        self.mock_auth.get_xsrf_token.assert_called_once()
        
        # Verify post parameters
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == '/my/download'
        assert call_args.kwargs['data'] == {'check': True}


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_auth = Mock()
        self.mock_auth.session = Mock()
        self.client = BarchartHttpClient(self.mock_auth)
    
    @patch.object(BarchartHttpClient, 'post')
    def test_download_network_error_propagation(self, mock_post):
        """Test that network errors are properly propagated."""
        # Mock network error
        mock_post.side_effect = requests.RequestException("Network error")
        
        frequency_attrs = FrequencyAttributes(
            frequency=Period.Daily
        )
        
        with pytest.raises(requests.RequestException):
            self.client.download_data(
                "AAPL",
                frequency_attrs,
                datetime(2024, 1, 1),
                datetime(2024, 1, 31),
                "token",
                "csrf"
            )
    
    @patch.object(BarchartHttpClient, 'post')
    def test_usage_check_json_error_propagation(self, mock_post):
        """Test that JSON parsing errors are properly propagated."""
        # Mock invalid JSON response
        mock_response = Mock()
        mock_response.text = "invalid json data"
        mock_post.return_value = mock_response
        
        self.mock_auth.get_xsrf_token.return_value = "new-token"
        
        with pytest.raises(json.JSONDecodeError):
            self.client.check_usage("test-token")
    
    def test_auth_handler_error_propagation(self):
        """Test that auth handler errors are properly propagated."""
        # Mock auth handler that raises error
        self.mock_auth.get_xsrf_token.side_effect = ValueError("Auth error")
        
        with patch.object(self.client, 'post') as mock_post:
            mock_response = Mock()
            mock_response.text = '{"used": 10}'
            mock_post.return_value = mock_response
            
            with pytest.raises(ValueError):
                self.client.check_usage("test-token")