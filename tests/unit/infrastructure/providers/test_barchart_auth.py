"""
Unit tests for Barchart authentication module.

Tests the BarchartAuth class including session management, login/logout, 
and token extraction functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from bs4 import BeautifulSoup

from vortex.infrastructure.providers.barchart.auth import BarchartAuth
from vortex.exceptions.config import ConfigurationValidationError


@pytest.mark.unit
class TestBarchartAuth:
    """Test BarchartAuth class initialization and configuration."""
    
    def test_init_valid_credentials(self):
        """Test initialization with valid credentials."""
        auth = BarchartAuth("testuser@example.com", "testpass123")
        
        assert auth.username == "testuser@example.com"
        assert auth.password == "testpass123"
        assert isinstance(auth.session, requests.Session)
    
    def test_init_empty_username(self):
        """Test initialization fails with empty username."""
        with pytest.raises(ConfigurationValidationError, match="Username validation failed"):
            BarchartAuth("", "testpass123")
    
    def test_init_empty_password(self):
        """Test initialization fails with empty password."""
        with pytest.raises(ConfigurationValidationError, match="Password validation failed"):
            BarchartAuth("testuser@example.com", "")
    
    def test_init_none_credentials(self):
        """Test initialization fails with None credentials."""
        with pytest.raises(ConfigurationValidationError):
            BarchartAuth(None, None)
    
    def test_create_session(self):
        """Test session creation with proper headers."""
        auth = BarchartAuth("testuser@example.com", "testpass123")
        session = auth._create_session()
        
        assert isinstance(session, requests.Session)
        assert "User-Agent" in session.headers
        assert "Mozilla/5.0" in session.headers["User-Agent"]
        # bc-utils uses a simple Mozilla User-Agent, not Chrome


@pytest.mark.unit
class TestBarchartAuthLogin:
    """Test login functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.object(BarchartAuth, '_create_session'):
            self.auth = BarchartAuth("testuser", "testpass")
            self.auth.session = Mock(spec=requests.Session)
    
    def test_login_success(self):
        """Test successful login flow."""
        # Mock the GET response for login page
        mock_get_response = Mock()
        mock_get_response.text = '<meta name="csrf-token" content="test-csrf-token">'
        self.auth.session.get.return_value = mock_get_response
        
        # Mock the POST response for login
        mock_post_response = Mock()
        mock_post_response.url = "https://www.barchart.com/dashboard"  # Different from login URL
        mock_post_response.status_code = 200
        self.auth.session.post.return_value = mock_post_response
        
        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_meta = Mock()
            mock_meta.get.return_value = 'test-csrf-token'
            mock_soup.return_value.find.return_value = mock_meta
            
            # Should not raise exception
            self.auth.login()
            
            # Verify session calls
            self.auth.session.get.assert_called_once_with(self.auth.BARCHART_LOGIN_URL, timeout=30)
            self.auth.session.post.assert_called_once()
    
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        # Mock the GET response
        mock_get_response = Mock()
        mock_get_response.text = '<input type="hidden" name="_token" value="test-csrf-token">'
        self.auth.session.get.return_value = mock_get_response
        
        # Mock POST response that stays on login page (indicating failure)
        mock_post_response = Mock()
        mock_post_response.url = self.auth.BARCHART_LOGIN_URL  # Same as login URL
        self.auth.session.post.return_value = mock_post_response
        
        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_tag = Mock()
            mock_tag.attrs = {'value': 'test-csrf-token'}
            mock_soup.return_value.find.return_value = mock_tag
            
            with pytest.raises(Exception, match="Invalid Barchart credentials"):
                self.auth.login()
    
    def test_login_csrf_token_extraction(self):
        """Test CSRF token extraction during login."""
        mock_get_response = Mock()
        mock_get_response.text = '<meta name="csrf-token" content="extracted-token">'
        self.auth.session.get.return_value = mock_get_response
        
        mock_post_response = Mock()
        mock_post_response.url = "https://www.barchart.com/dashboard"
        mock_post_response.status_code = 200
        self.auth.session.post.return_value = mock_post_response
        
        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_meta = Mock()
            mock_meta.get.return_value = 'extracted-token'
            mock_soup.return_value.find.return_value = mock_meta
            
            self.auth.login()
            
            # Verify POST was called with correct payload
            call_args = self.auth.session.post.call_args
            posted_data = call_args[1]['data']
            assert posted_data['_token'] == 'extracted-token'
            assert posted_data['email'] == 'testuser'
            assert posted_data['password'] == 'testpass'
    
    def test_logout_success(self):
        """Test successful logout."""
        self.auth.logout()
        
        self.auth.session.get.assert_called_once_with(self.auth.BARCHART_LOGOUT_URL, timeout=10)


@pytest.mark.unit
class TestBarchartAuthMethods:
    """Test new bc-utils methodology methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.object(BarchartAuth, '_create_session'):
            self.auth = BarchartAuth("testuser", "testpass")
            self.auth.session = Mock(spec=requests.Session)
    
    def test_get_api_headers(self):
        """Test API headers generation."""
        # Mock cookies
        self.auth.session.cookies = {'XSRF-TOKEN': 'test%20token'}
        
        headers = self.auth.get_api_headers()
        
        assert 'User-Agent' in headers
        assert headers['Accept'] == 'application/json'
        assert headers['Content-Type'] == 'application/json'
        assert headers['X-Requested-With'] == 'XMLHttpRequest'
        assert headers['X-XSRF-TOKEN'] == 'test token'  # URL decoded
    
    def test_get_xsrf_token_from_cookies(self):
        """Test XSRF token extraction from cookies."""
        self.auth.session.cookies = {'XSRF-TOKEN': 'test%20token%20123'}
        
        token = self.auth.get_xsrf_token()
        
        assert token == 'test token 123'
    
    def test_make_api_request_success(self):
        """Test successful API request."""
        # Mock response
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'data': 'test'}
        mock_response.raise_for_status = Mock()
        
        self.auth.session.get.return_value = mock_response
        self.auth.session.cookies = {'XSRF-TOKEN': 'test-token'}
        
        result = self.auth.make_api_request('https://test.com/api')
        
        assert result == {'data': 'test'}
        mock_response.raise_for_status.assert_called_once()


@pytest.mark.unit
class TestBarchartAuthEdgeCases:
    """Test edge cases and error scenarios."""
    
    def test_login_with_network_error(self):
        """Test login behavior when network error occurs."""
        with patch.object(BarchartAuth, '_create_session'):
            auth = BarchartAuth("testuser", "testpass")
            auth.session = Mock(spec=requests.Session)
            auth.session.get.side_effect = requests.RequestException("Network error")
            
            with pytest.raises(requests.RequestException):
                auth.login()
    
    def test_logout_with_timeout(self):
        """Test logout with timeout parameter."""
        with patch.object(BarchartAuth, '_create_session'):
            auth = BarchartAuth("testuser", "testpass")
            auth.session = Mock(spec=requests.Session)
            
            auth.logout()
            
            auth.session.get.assert_called_once_with(auth.BARCHART_LOGOUT_URL, timeout=10)
    
    def test_session_headers_configuration(self):
        """Test that session is configured with proper headers."""
        auth = BarchartAuth("testuser", "testpass")
        
        user_agent = auth.session.headers.get('User-Agent')
        assert user_agent is not None
        assert 'Mozilla/5.0' in user_agent
    
    def test_url_constants(self):
        """Test URL constants are properly defined."""
        assert BarchartAuth.BARCHART_URL == 'https://www.barchart.com'
        assert BarchartAuth.BARCHART_LOGIN_URL == 'https://www.barchart.com/login'
        assert BarchartAuth.BARCHART_LOGOUT_URL == 'https://www.barchart.com/logout'


@pytest.mark.unit
class TestBarchartAuthErrorScenarios:
    """Test error handling and edge cases in authentication."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch.object(BarchartAuth, '_create_session'):
            self.auth = BarchartAuth("testuser", "testpass")
            self.auth.session = Mock(spec=requests.Session)
    
    def test_login_csrf_token_not_found(self):
        """Test login when CSRF token cannot be found."""
        # Mock response without CSRF token
        mock_get_response = Mock()
        mock_get_response.text = '<html><body>No token here</body></html>'
        self.auth.session.get.return_value = mock_get_response
        
        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_soup.return_value.find.return_value = None  # No token found
            
            with pytest.raises(ValueError, match="CSRF token not found"):
                self.auth.login()
    
    def test_login_bad_status_code(self):
        """Test login with bad HTTP status code."""
        from vortex.exceptions.providers import AuthenticationError
        
        # Mock successful GET for login page
        mock_get_response = Mock()
        mock_get_response.text = '<meta name="csrf-token" content="test-token">'
        self.auth.session.get.return_value = mock_get_response
        
        # Mock POST with bad status
        mock_post_response = Mock()
        mock_post_response.url = "https://www.barchart.com/dashboard"
        mock_post_response.status_code = 500
        self.auth.session.post.return_value = mock_post_response
        
        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_meta = Mock()
            mock_meta.get.return_value = 'test-token'
            mock_soup.return_value.find.return_value = mock_meta
            
            with pytest.raises(AuthenticationError, match="Login failed with status code: 500"):
                self.auth.login()
    
    def test_login_missing_session_cookie_warning(self):
        """Test login warning when laravel_session cookie is missing."""
        # Mock successful GET and POST
        mock_get_response = Mock()
        mock_get_response.text = '<meta name="csrf-token" content="test-token">'
        self.auth.session.get.return_value = mock_get_response
        
        mock_post_response = Mock()
        mock_post_response.url = "https://www.barchart.com/dashboard"
        mock_post_response.status_code = 200
        self.auth.session.post.return_value = mock_post_response
        
        # Mock cookies without laravel_session
        self.auth.session.cookies = {'other_cookie': 'value'}
        
        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_meta = Mock()
            mock_meta.get.return_value = 'test-token'
            mock_soup.return_value.find.return_value = mock_meta
            
            with patch('logging.getLogger') as mock_logger:
                mock_logger_instance = Mock()
                mock_logger.return_value = mock_logger_instance
                
                self.auth.login()
                
                mock_logger_instance.warning.assert_called_once()
                args = mock_logger_instance.warning.call_args[0]
                assert 'missing expected laravel_session cookie' in args[0]
    
    def test_get_xsrf_token_fallback_success(self):
        """Test XSRF token fallback when not in initial cookies."""
        # Initially no XSRF token
        self.auth.session.cookies = {}
        
        # Mock the fallback request that gets the token
        mock_response = Mock()
        
        def side_effect_get(*args, **kwargs):
            # Simulate getting the token after visiting main page
            self.auth.session.cookies = {'XSRF-TOKEN': 'fallback%20token'}
            return mock_response
        
        self.auth.session.get.side_effect = side_effect_get
        
        with patch('urllib.parse.unquote', return_value='fallback token'):
            token = self.auth.get_xsrf_token()
            assert token == 'fallback token'
    
    def test_get_xsrf_token_failure(self):
        """Test XSRF token failure when token cannot be obtained."""
        # No XSRF token in cookies initially
        self.auth.session.cookies = {}
        
        # Mock the fallback request that still doesn't get the token
        mock_response = Mock()
        self.auth.session.get.return_value = mock_response
        
        with pytest.raises(ValueError, match="Unable to obtain XSRF token"):
            self.auth.get_xsrf_token()
    
    def test_make_api_request_timeout_error(self):
        """Test API request timeout handling."""
        self.auth.session.cookies = {'XSRF-TOKEN': 'test-token'}
        self.auth.session.get.side_effect = requests.exceptions.Timeout("Request timeout")
        
        with pytest.raises(requests.exceptions.Timeout):
            self.auth.make_api_request('https://test.com/api')
    
    def test_make_api_request_connection_error(self):
        """Test API request connection error handling."""
        self.auth.session.cookies = {'XSRF-TOKEN': 'test-token'}
        self.auth.session.get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with pytest.raises(requests.exceptions.ConnectionError):
            self.auth.make_api_request('https://test.com/api')
    
    def test_make_api_request_http_error(self):
        """Test API request HTTP error handling."""
        self.auth.session.cookies = {'XSRF-TOKEN': 'test-token'}
        
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = requests.exceptions.HTTPError("Not found")
        http_error.response = mock_response
        self.auth.session.get.side_effect = http_error
        
        with pytest.raises(requests.exceptions.HTTPError):
            self.auth.make_api_request('https://test.com/api')
    
    def test_make_api_request_unexpected_error(self):
        """Test API request unexpected error handling."""
        self.auth.session.cookies = {'XSRF-TOKEN': 'test-token'}
        self.auth.session.get.side_effect = Exception("Unexpected error")
        
        with pytest.raises(Exception, match="Unexpected error"):
            self.auth.make_api_request('https://test.com/api')
    
    def test_make_api_request_with_params(self):
        """Test API request with parameters."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'application/json'}
        mock_response.json.return_value = {'success': True}
        mock_response.raise_for_status = Mock()
        
        self.auth.session.get.return_value = mock_response
        self.auth.session.cookies = {'XSRF-TOKEN': 'test-token'}
        
        params = {'symbol': 'AAPL', 'period': '1d'}
        result = self.auth.make_api_request('https://test.com/api', params=params)
        
        assert result == {'success': True}
        # Verify params were passed
        call_args = self.auth.session.get.call_args
        assert 'params' in call_args[1]
        assert call_args[1]['params'] == params
    
    def test_make_api_request_csv_response(self):
        """Test API request with CSV response."""
        mock_response = Mock()
        mock_response.headers = {'content-type': 'text/csv'}
        mock_response.text = 'Date,Open,High,Low,Close\n2024-01-01,100,105,99,104'
        mock_response.raise_for_status = Mock()
        
        self.auth.session.get.return_value = mock_response
        self.auth.session.cookies = {'XSRF-TOKEN': 'test-token'}
        
        result = self.auth.make_api_request('https://test.com/api')
        
        assert 'data' in result
        assert 'content_type' in result
        assert result['content_type'] == 'text/csv'
        assert 'Date,Open,High,Low,Close' in result['data']


@pytest.mark.unit
class TestBarchartAuthIntegration:
    """Test integration scenarios with realistic data."""
    
    def test_full_login_flow_with_realistic_html(self):
        """Test login with realistic HTML response."""
        with patch.object(BarchartAuth, '_create_session'):
            auth = BarchartAuth("testuser", "testpass")
            auth.session = Mock(spec=requests.Session)
            
            # Mock realistic login page HTML with csrf meta tag
            login_page_html = '''
            <html>
            <head>
                <meta name="csrf-token" content="csrf-token-12345">
            </head>
            <body>
                <form>
                    <input type="email" name="email">
                    <input type="password" name="password">
                </form>
            </body>
            </html>
            '''
            
            mock_get_response = Mock()
            mock_get_response.text = login_page_html
            auth.session.get.return_value = mock_get_response
            
            # Mock successful login redirect
            mock_post_response = Mock()
            mock_post_response.url = "https://www.barchart.com/dashboard"
            mock_post_response.status_code = 200
            auth.session.post.return_value = mock_post_response
            auth.session.cookies = {'laravel_session': 'test-session'}
            
            auth.login()
            
            # Verify the flow
            auth.session.get.assert_called_once_with('https://www.barchart.com/login', timeout=30)
            auth.session.post.assert_called_once()
            
            # Verify payload structure
            call_args = auth.session.post.call_args
            payload = call_args[1]['data']
            assert '_token' in payload
            assert payload['email'] == 'testuser'
            assert payload['password'] == 'testpass'
            assert payload['remember'] == '1'  # bc-utils uses '1' instead of 'on'