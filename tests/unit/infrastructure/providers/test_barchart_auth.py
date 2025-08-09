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


@pytest.mark.unit
class TestBarchartAuth:
    """Test BarchartAuth class initialization and configuration."""
    
    def test_init_valid_credentials(self):
        """Test initialization with valid credentials."""
        auth = BarchartAuth("testuser", "testpass")
        
        assert auth.username == "testuser"
        assert auth.password == "testpass"
        assert isinstance(auth.session, requests.Session)
    
    def test_init_empty_username(self):
        """Test initialization fails with empty username."""
        with pytest.raises(Exception, match="Barchart credentials are required"):
            BarchartAuth("", "testpass")
    
    def test_init_empty_password(self):
        """Test initialization fails with empty password."""
        with pytest.raises(Exception, match="Barchart credentials are required"):
            BarchartAuth("testuser", "")
    
    def test_init_none_credentials(self):
        """Test initialization fails with None credentials."""
        with pytest.raises(Exception, match="Barchart credentials are required"):
            BarchartAuth(None, None)
    
    def test_create_session(self):
        """Test session creation with proper headers."""
        auth = BarchartAuth("testuser", "testpass")
        session = auth._create_session()
        
        assert isinstance(session, requests.Session)
        assert "User-Agent" in session.headers
        assert "Mozilla/5.0" in session.headers["User-Agent"]
        assert "Chrome" in session.headers["User-Agent"]


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
        mock_get_response.text = '<input type="hidden" name="_token" value="test-csrf-token">'
        self.auth.session.get.return_value = mock_get_response
        
        # Mock the POST response for login
        mock_post_response = Mock()
        mock_post_response.url = "https://www.barchart.com/dashboard"  # Different from login URL
        self.auth.session.post.return_value = mock_post_response
        
        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_tag = Mock()
            mock_tag.attrs = {'value': 'test-csrf-token'}
            mock_soup.return_value.find.return_value = mock_tag
            
            # Should not raise exception
            self.auth.login()
            
            # Verify session calls
            self.auth.session.get.assert_called_once_with(self.auth.BARCHART_LOGIN_URL)
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
        mock_get_response.text = '<input type="hidden" name="_token" value="extracted-token">'
        self.auth.session.get.return_value = mock_get_response
        
        mock_post_response = Mock()
        mock_post_response.url = "https://www.barchart.com/dashboard"
        self.auth.session.post.return_value = mock_post_response
        
        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_tag = Mock()
            mock_tag.attrs = {'value': 'extracted-token'}
            mock_soup.return_value.find.return_value = mock_tag
            
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
class TestBarchartAuthStaticMethods:
    """Test static utility methods."""
    
    def test_build_login_payload(self):
        """Test login payload construction."""
        payload = BarchartAuth._build_login_payload("test-token", "user@example.com", "password123")
        
        expected = {
            '_token': 'test-token',
            'email': 'user@example.com',
            'password': 'password123',
            'remember': 'on',
            'g-recaptcha-response': ''
        }
        
        assert payload == expected
    
    def test_extract_xsrf_token(self):
        """Test XSRF token extraction from response."""
        mock_response = Mock()
        mock_response.text = '<meta name="csrf-token" content="xsrf-token-123">'
        
        with patch('vortex.infrastructure.providers.barchart.auth.BeautifulSoup') as mock_soup:
            mock_meta = Mock()
            mock_meta.__getitem__ = Mock(return_value='xsrf-token-123')
            mock_soup.return_value.find.return_value = mock_meta
            
            token = BarchartAuth.extract_xsrf_token(mock_response)
            
            assert token == 'xsrf-token-123'
            mock_soup.assert_called_once_with(mock_response.text, 'html.parser')
    
    def test_scrape_csrf_token(self):
        """Test CSRF token scraping from historical data response."""
        mock_response = Mock()
        mock_response.text = '<input id="hist-csrf-token" value="hist-token-456">'
        
        with patch('vortex.infrastructure.providers.barchart.auth.BeautifulSoup') as mock_soup:
            mock_input = Mock()
            mock_input.__getitem__ = Mock(return_value='hist-token-456')
            mock_soup.return_value.find.return_value = mock_input
            
            token = BarchartAuth.scrape_csrf_token(mock_response)
            
            assert token == 'hist-token-456'
            mock_soup.return_value.find.assert_called_once_with(id='hist-csrf-token')


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
        assert 'Chrome' in user_agent
        assert 'Safari' in user_agent
    
    def test_url_constants(self):
        """Test URL constants are properly defined."""
        assert BarchartAuth.BARCHART_URL == 'https://www.barchart.com'
        assert BarchartAuth.BARCHART_LOGIN_URL == 'https://www.barchart.com/login'
        assert BarchartAuth.BARCHART_LOGOUT_URL == 'https://www.barchart.com/logout'


@pytest.mark.unit
class TestBarchartAuthIntegration:
    """Test integration scenarios with realistic data."""
    
    def test_full_login_flow_with_realistic_html(self):
        """Test login with realistic HTML response."""
        with patch.object(BarchartAuth, '_create_session'):
            auth = BarchartAuth("testuser", "testpass")
            auth.session = Mock(spec=requests.Session)
            
            # Mock realistic login page HTML
            login_page_html = '''
            <html>
            <body>
                <form>
                    <input type="hidden" name="_token" value="csrf-token-12345">
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
            auth.session.post.return_value = mock_post_response
            
            auth.login()
            
            # Verify the flow
            auth.session.get.assert_called_once()
            auth.session.post.assert_called_once()
            
            # Verify payload structure
            call_args = auth.session.post.call_args
            payload = call_args[1]['data']
            assert '_token' in payload
            assert payload['email'] == 'testuser'
            assert payload['password'] == 'testpass'
            assert payload['remember'] == 'on'