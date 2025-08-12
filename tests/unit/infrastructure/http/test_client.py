"""
Unit tests for the HTTP client abstraction.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from vortex.infrastructure.http.client import HttpClient, AuthenticatedHttpClient


class TestHttpClient:
    """Test the base HttpClient class."""
    
    @pytest.fixture
    def http_client(self):
        """Create an HTTP client instance."""
        return HttpClient('https://api.example.com')
    
    def test_client_initialization(self):
        """Test HTTP client initialization."""
        client = HttpClient('https://api.example.com/', timeout=60, max_retries=5)
        
        assert client.base_url == 'https://api.example.com'  # Trailing slash removed
        assert client.timeout == 60
        assert client.session is not None
    
    def test_client_with_existing_session(self):
        """Test client with provided session."""
        mock_session = Mock(spec=requests.Session)
        client = HttpClient('https://api.example.com', session=mock_session)
        
        assert client.session == mock_session
    
    @patch('vortex.infrastructure.http.client.requests.Session')
    def test_create_session_with_retries(self, mock_session_class):
        """Test session creation with retry configuration."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        client = HttpClient('https://api.example.com', max_retries=3, backoff_factor=0.5)
        
        # Should mount adapters for both http and https
        assert mock_session.mount.call_count == 2
        mount_calls = mock_session.mount.call_args_list
        assert mount_calls[0][0][0] == 'http://'
        assert mount_calls[1][0][0] == 'https://'
    
    def test_build_url_relative(self, http_client):
        """Test building URL from relative endpoint."""
        url = http_client._build_url('/api/data')
        assert url == 'https://api.example.com/api/data'
        
        url = http_client._build_url('api/data')
        assert url == 'https://api.example.com/api/data'
    
    def test_build_url_absolute(self, http_client):
        """Test building URL from absolute endpoint."""
        url = http_client._build_url('https://other.example.com/data')
        assert url == 'https://other.example.com/data'
    
    @patch('requests.Session.get')
    def test_get_request(self, mock_get, http_client):
        """Test GET request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"data": "test"}'
        mock_get.return_value = mock_response
        
        response = http_client.get('/api/data', params={'key': 'value'})
        
        assert response == mock_response
        mock_get.assert_called_once_with(
            'https://api.example.com/api/data',
            params={'key': 'value'},
            headers=None,
            timeout=30
        )
    
    @patch('requests.Session.post')
    def test_post_request_with_data(self, mock_post, http_client):
        """Test POST request with form data."""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.content = b'{"id": 123}'
        mock_post.return_value = mock_response
        
        data = {'field1': 'value1', 'field2': 'value2'}
        response = http_client.post('/api/create', data=data)
        
        assert response == mock_response
        mock_post.assert_called_once_with(
            'https://api.example.com/api/create',
            data=data,
            json=None,
            headers=None,
            timeout=30
        )
    
    @patch('requests.Session.post')
    def test_post_request_with_json(self, mock_post, http_client):
        """Test POST request with JSON data."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'{"success": true}'
        mock_post.return_value = mock_response
        
        json_data = {'key': 'value'}
        response = http_client.post('/api/json', json=json_data)
        
        assert response == mock_response
        mock_post.assert_called_once_with(
            'https://api.example.com/api/json',
            data=None,
            json=json_data,
            headers=None,
            timeout=30
        )
    
    @patch('requests.Session.get')
    def test_custom_timeout(self, mock_get, http_client):
        """Test request with custom timeout."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b'test'
        mock_get.return_value = mock_response
        
        http_client.get('/api/data', timeout=60)
        
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['timeout'] == 60
    
    def test_close_session(self, http_client):
        """Test closing the session."""
        http_client.session = Mock()
        http_client.close()
        
        http_client.session.close.assert_called_once()


class TestAuthenticatedHttpClient:
    """Test the AuthenticatedHttpClient class."""
    
    @pytest.fixture
    def mock_auth_handler(self):
        """Create a mock authentication handler."""
        mock = Mock()
        mock.login = Mock()
        mock.get_auth_headers = Mock(return_value={'Authorization': 'Bearer token123'})
        return mock
    
    @pytest.fixture
    def auth_client(self, mock_auth_handler):
        """Create an authenticated HTTP client."""
        return AuthenticatedHttpClient(
            'https://api.example.com',
            auth_handler=mock_auth_handler
        )
    
    def test_authenticated_client_initialization(self, auth_client, mock_auth_handler):
        """Test authenticated client initialization."""
        assert auth_client.auth_handler == mock_auth_handler
        assert auth_client.base_url == 'https://api.example.com'
    
    def test_authenticate(self, auth_client, mock_auth_handler):
        """Test authentication method."""
        auth_client.authenticate()
        mock_auth_handler.login.assert_called_once()
    
    def test_authenticate_no_handler(self):
        """Test authenticate with no handler."""
        client = AuthenticatedHttpClient('https://api.example.com')
        client.authenticate()  # Should not raise
    
    def test_get_auth_headers(self, auth_client, mock_auth_handler):
        """Test getting authentication headers."""
        headers = auth_client.get_auth_headers()
        
        assert headers == {'Authorization': 'Bearer token123'}
        mock_auth_handler.get_auth_headers.assert_called_once()
    
    def test_get_auth_headers_no_handler(self):
        """Test getting auth headers with no handler."""
        client = AuthenticatedHttpClient('https://api.example.com')
        headers = client.get_auth_headers()
        
        assert headers == {}
    
    @patch('vortex.infrastructure.http.client.HttpClient.get')
    def test_get_with_auth_headers(self, mock_super_get, auth_client):
        """Test GET request includes auth headers."""
        mock_super_get.return_value = Mock()
        
        auth_client.get('/api/protected', headers={'Custom': 'Header'})
        
        mock_super_get.assert_called_once()
        call_kwargs = mock_super_get.call_args[1]
        assert call_kwargs['headers'] == {
            'Custom': 'Header',
            'Authorization': 'Bearer token123'
        }
    
    @patch('vortex.infrastructure.http.client.HttpClient.post')
    def test_post_with_auth_headers(self, mock_super_post, auth_client):
        """Test POST request includes auth headers."""
        mock_super_post.return_value = Mock()
        
        auth_client.post('/api/protected', json={'data': 'value'})
        
        mock_super_post.assert_called_once()
        call_kwargs = mock_super_post.call_args[1]
        assert call_kwargs['headers'] == {'Authorization': 'Bearer token123'}
        assert call_kwargs['json'] == {'data': 'value'}