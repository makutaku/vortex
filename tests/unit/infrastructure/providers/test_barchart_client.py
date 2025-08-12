"""
Unit tests for Barchart HTTP client.

Tests the BarchartClient class including download requests, usage checking,
and HTTP request construction.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests

from vortex.infrastructure.providers.barchart.client import BarchartClient
from vortex.infrastructure.providers.barchart.auth import BarchartAuth
from vortex.models.period import Period


@pytest.fixture
def mock_auth():
    """Create a mock BarchartAuth instance."""
    auth = Mock(spec=BarchartAuth)
    auth.session = Mock(spec=requests.Session)
    auth.get_xsrf_token = Mock(return_value="test-xsrf-token")
    return auth


@pytest.fixture
def client(mock_auth):
    """Create a BarchartClient instance with mock auth."""
    return BarchartClient(mock_auth)


@pytest.fixture
def sample_frequency_attributes():
    """Create sample frequency attributes for testing."""
    from datetime import timedelta
    # Create a mock that has the attributes the client code expects
    mock_attrs = Mock()
    mock_attrs.frequency = Period('1d')
    mock_attrs.min_start = timedelta(days=365)
    mock_attrs.max_window = timedelta(days=365)
    mock_attrs.name = Mock(lower=Mock(return_value='daily'))
    mock_attrs.max_records_per_download = 20000
    return mock_attrs


@pytest.mark.unit
class TestBarchartClientInit:
    """Test BarchartClient initialization."""
    
    def test_init_with_auth(self, mock_auth):
        """Test initialization with auth object."""
        client = BarchartClient(mock_auth)
        
        assert client.auth is mock_auth
        assert client.session is mock_auth.session
    
    def test_url_constants(self):
        """Test URL constants are properly defined."""
        assert BarchartClient.BARCHART_URL == 'https://www.barchart.com'
        assert BarchartClient.BARCHART_DOWNLOAD_URL == 'https://www.barchart.com/my/download'
        assert BarchartClient.BARCHART_USAGE_URL == 'https://www.barchart.com/my/download'


@pytest.mark.unit
class TestBarchartClientDownloadRequest:
    """Test download request functionality."""
    
    def test_request_download_success(self, client, sample_frequency_attributes):
        """Test successful download request."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"mock csv data"
        client.session.post.return_value = mock_response
        
        # Test data
        xsrf_token = "test-xsrf-token"
        history_csrf_token = "test-hist-csrf"
        symbol = "AAPL"
        url = "https://www.barchart.com/stocks/quotes/AAPL/historical-download"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        with patch('logging.debug') as mock_debug:
            result = client.request_download(
                xsrf_token, history_csrf_token, symbol, sample_frequency_attributes, 
                url, start_date, end_date
            )
        
        assert result is mock_response
        client.session.post.assert_called_once()
        mock_debug.assert_called_once()
        
        # Verify call arguments
        call_args = client.session.post.call_args
        assert call_args[0][0] == BarchartClient.BARCHART_DOWNLOAD_URL
        assert 'headers' in call_args[1]
        assert 'data' in call_args[1]
    
    def test_request_download_headers_construction(self, client, sample_frequency_attributes):
        """Test that download request headers are properly constructed."""
        mock_response = Mock()
        mock_response.content = b"test data"  # Add content with length
        client.session.post.return_value = mock_response
        
        xsrf_token = "test-xsrf-token"
        history_csrf_token = "test-hist-csrf"
        symbol = "AAPL"
        url = "https://www.barchart.com/stocks/quotes/AAPL/historical-download"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        client.request_download(
            xsrf_token, history_csrf_token, symbol, sample_frequency_attributes, 
            url, start_date, end_date
        )
        
        call_args = client.session.post.call_args
        headers = call_args[1]['headers']
        
        assert headers['Content-Type'] == 'application/x-www-form-urlencoded; charset=UTF-8'
        assert headers['X-CSRF-TOKEN'] == xsrf_token
        assert headers['X-Requested-With'] == 'XMLHttpRequest'
        assert headers['Referer'] == url
    
    def test_request_download_payload_construction(self, client, sample_frequency_attributes):
        """Test that download request payload is properly constructed."""
        mock_response = Mock()
        mock_response.content = b"test payload data"  # Add content with length
        client.session.post.return_value = mock_response
        
        xsrf_token = "test-xsrf-token"
        history_csrf_token = "test-hist-csrf"
        symbol = "AAPL"
        url = "https://www.barchart.com/test"
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        
        client.request_download(
            xsrf_token, history_csrf_token, symbol, sample_frequency_attributes, 
            url, start_date, end_date
        )
        
        call_args = client.session.post.call_args
        payload = call_args[1]['data']
        
        assert payload['_token'] == history_csrf_token
        assert payload['fileName'] == symbol
        assert payload['symbol'] == symbol
        assert payload['startDate'] == "01/01/2024"
        assert payload['endDate'] == "01/31/2024"
        assert payload['period'] == 'daily'
        assert payload['maxRecords'] == 20000
        assert payload['order'] == 'asc'
        assert payload['dividends'] == 'false'
        assert payload['backadjust'] == 'false'
        assert payload['dbar'] == 1
        assert payload['volume'] == 'true'
        assert payload['openInterest'] == 'true'
        assert payload['splits'] == 'true'


@pytest.mark.unit  
class TestBarchartClientUsage:
    """Test usage checking functionality."""
    
    def test_fetch_usage_success(self, client):
        """Test successful usage fetch."""
        # Mock usage response
        usage_data = {"success": True, "count": 50, "limit": 150}
        mock_response = Mock()
        mock_response.text = json.dumps(usage_data)
        client.session.post.return_value = mock_response
        client.auth.get_xsrf_token.return_value = "new-xsrf-token"
        
        url = "https://www.barchart.com/test"
        xsrf_token = "old-xsrf-token"
        
        with patch('logging.debug') as mock_debug:
            result_usage, result_token = client.fetch_usage(url, xsrf_token)
        
        assert result_usage == usage_data
        assert result_token == "new-xsrf-token"
        client.session.post.assert_called_once()
        client.auth.get_xsrf_token.assert_called_once()
        mock_debug.assert_called_once()
    
    def test_fetch_usage_headers(self, client):
        """Test usage request headers construction."""
        mock_response = Mock()
        mock_response.text = '{"success": true}'
        client.session.post.return_value = mock_response
        client.auth.get_xsrf_token.return_value = "token"
        
        url = "https://www.barchart.com/test"
        xsrf_token = "test-token"
        
        client.fetch_usage(url, xsrf_token)
        
        call_args = client.session.post.call_args
        headers = call_args[1]['headers']
        
        assert headers['Content-Type'] == 'application/x-www-form-urlencoded; charset=UTF-8'
        assert headers['X-CSRF-TOKEN'] == xsrf_token
        assert headers['X-Requested-With'] == 'XMLHttpRequest'
        assert headers['Referer'] == url
    
    def test_fetch_usage_payload(self, client):
        """Test usage request payload."""
        mock_response = Mock()
        mock_response.text = '{"success": true}'
        client.session.post.return_value = mock_response
        client.auth.get_xsrf_token.return_value = "token"
        
        client.fetch_usage("http://test.com", "token")
        
        call_args = client.session.post.call_args
        payload = call_args[1]['data']
        
        assert payload == {'type': 'quotes'}


@pytest.mark.unit
class TestBarchartClientStaticMethods:
    """Test static utility methods."""
    
    def test_build_download_request_payload(self, sample_frequency_attributes):
        """Test download request payload construction."""
        history_csrf_token = "test-csrf"
        symbol = "AAPL" 
        start_date = datetime(2024, 3, 15)
        end_date = datetime(2024, 3, 20)
        
        payload = BarchartClient._build_download_request_payload(
            history_csrf_token, symbol, sample_frequency_attributes, start_date, end_date
        )
        
        expected = {
            '_token': 'test-csrf',
            'fileName': 'AAPL',
            'symbol': 'AAPL',
            'startDate': '03/15/2024',
            'endDate': '03/20/2024',
            'period': 'daily',
            'maxRecords': 20000,
            'order': 'asc',
            'dividends': 'false',
            'backadjust': 'false',
            'dbar': 1,
            'custombar': '',
            'volume': 'true',
            'openInterest': 'true',
            'splits': 'true'
        }
        
        assert payload == expected
    
    def test_build_download_request_headers(self):
        """Test download request headers construction."""
        xsrf_token = "test-xsrf-token"
        url = "https://www.barchart.com/test/url"
        
        headers = BarchartClient._build_download_request_headers(xsrf_token, url)
        
        expected = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-CSRF-TOKEN': 'test-xsrf-token',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.barchart.com/test/url'
        }
        
        assert headers == expected
    
    def test_build_usage_request_headers(self):
        """Test usage request headers construction."""
        url = "https://www.barchart.com/usage"
        xsrf_token = "usage-token"
        
        headers = BarchartClient._build_usage_request_headers(url, xsrf_token)
        
        expected = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-CSRF-TOKEN': 'usage-token',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': 'https://www.barchart.com/usage'
        }
        
        assert headers == expected
    
    def test_build_usage_payload(self):
        """Test usage request payload construction."""
        payload = BarchartClient._build_usage_payload()
        
        assert payload == {'type': 'quotes'}


@pytest.mark.unit
class TestBarchartClientIntegration:
    """Test client integration scenarios."""
    
    def test_full_download_request_flow(self, client, sample_frequency_attributes):
        """Test complete download request workflow."""
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"Time,Open,High,Low,Last,Volume\n2024-01-01,100,105,99,104,1000\n"
        client.session.post.return_value = mock_response
        
        # Execute request
        result = client.request_download(
            "xsrf-token", "csrf-token", "AAPL", sample_frequency_attributes,
            "https://www.barchart.com/stocks/quotes/AAPL/historical-download",
            datetime(2024, 1, 1), datetime(2024, 1, 31)
        )
        
        # Verify result
        assert result.status_code == 200
        assert b"Time,Open,High,Low,Last,Volume" in result.content
        
        # Verify session was called correctly
        client.session.post.assert_called_once()
        call_args = client.session.post.call_args
        assert call_args[0][0] == BarchartClient.BARCHART_DOWNLOAD_URL
    
    def test_usage_and_token_refresh_flow(self, client):
        """Test usage check with token refresh."""
        # Mock usage response
        usage_data = {"success": True, "count": 25, "limit": 150}
        mock_response = Mock()
        mock_response.text = json.dumps(usage_data)
        client.session.post.return_value = mock_response
        
        # Mock token extraction
        new_token = "refreshed-xsrf-token"
        client.auth.get_xsrf_token.return_value = new_token
        
        # Execute usage check
        usage, token = client.fetch_usage(
            "https://www.barchart.com/my/download", "old-token"
        )
        
        # Verify results
        assert usage == usage_data
        assert token == new_token
        assert usage["count"] == 25
        assert usage["success"] is True
    
    def test_error_handling_in_requests(self, client):
        """Test error handling in HTTP requests."""
        # Mock network error
        client.session.post.side_effect = requests.RequestException("Network error")
        
        with pytest.raises(requests.RequestException):
            client.request_download(
                "token", "csrf", "AAPL", Mock(), "url", 
                datetime.now(), datetime.now()
            )
    
    def test_different_frequency_attributes(self, client):
        """Test requests with different frequency attributes."""
        from datetime import timedelta
        
        # Test hourly frequency
        hourly_attrs = Mock()
        hourly_attrs.frequency = Period('1h')
        hourly_attrs.min_start = timedelta(days=30)
        hourly_attrs.max_window = timedelta(days=30)
        hourly_attrs.name = Mock(lower=Mock(return_value='hourly'))
        hourly_attrs.max_records_per_download = 5000
        
        mock_response = Mock()
        mock_response.content = b"hourly test data"  # Add content with length
        client.session.post.return_value = mock_response
        
        client.request_download(
            "token", "csrf", "GC", hourly_attrs, "url",
            datetime(2024, 1, 1), datetime(2024, 1, 2)
        )
        
        call_args = client.session.post.call_args
        payload = call_args[1]['data']
        
        assert payload['period'] == 'hourly'
        assert payload['maxRecords'] == 5000
        assert payload['symbol'] == 'GC'