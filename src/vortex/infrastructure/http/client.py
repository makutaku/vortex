"""
HTTP client abstraction for separating HTTP concerns from business logic.

This module provides a clean abstraction for HTTP operations, allowing
providers to focus on business logic rather than HTTP details.
"""

import logging
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    """Base HTTP client with common functionality for all providers."""
    
    def __init__(
        self,
        base_url: str,
        session: Optional[requests.Session] = None,
        timeout: int = 30,
        max_retries: int = 3,
        backoff_factor: float = 0.3
    ):
        """Initialize HTTP client with configuration.
        
        Args:
            base_url: Base URL for all requests
            session: Optional existing session to use
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            backoff_factor: Backoff factor for retries
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Use provided session or create new one
        self.session = session or self._create_session(max_retries, backoff_factor)
    
    def _create_session(self, max_retries: int, backoff_factor: float) -> requests.Session:
        """Create a session with retry configuration."""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        """Perform GET request.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            headers: Additional headers
            **kwargs: Additional arguments passed to requests
            
        Returns:
            Response object
        """
        url = self._build_url(endpoint)
        
        self.logger.debug(f"GET {url}")
        
        response = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=kwargs.get('timeout', self.timeout),
            **{k: v for k, v in kwargs.items() if k != 'timeout'}
        )
        
        self._log_response(response)
        return response
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> requests.Response:
        """Perform POST request.
        
        Args:
            endpoint: API endpoint (relative to base_url)
            data: Form data
            json: JSON data
            headers: Additional headers
            **kwargs: Additional arguments passed to requests
            
        Returns:
            Response object
        """
        url = self._build_url(endpoint)
        
        self.logger.debug(f"POST {url}")
        
        response = self.session.post(
            url,
            data=data,
            json=json,
            headers=headers,
            timeout=kwargs.get('timeout', self.timeout),
            **{k: v for k, v in kwargs.items() if k != 'timeout'}
        )
        
        self._log_response(response)
        return response
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        if endpoint.startswith('http'):
            return endpoint
        return urljoin(self.base_url + '/', endpoint.lstrip('/'))
    
    def _log_response(self, response: requests.Response) -> None:
        """Log response details."""
        self.logger.debug(
            f"Response: {response.status_code} - "
            f"{len(response.content)} bytes"
        )
    
    def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            self.session.close()


class AuthenticatedHttpClient(HttpClient):
    """HTTP client with authentication support."""
    
    def __init__(
        self,
        base_url: str,
        auth_handler: Optional[Any] = None,
        **kwargs
    ):
        """Initialize authenticated HTTP client.
        
        Args:
            base_url: Base URL for all requests
            auth_handler: Optional authentication handler
            **kwargs: Additional arguments for HttpClient
        """
        super().__init__(base_url, **kwargs)
        self.auth_handler = auth_handler
    
    def authenticate(self) -> None:
        """Perform authentication if handler is available."""
        if self.auth_handler and hasattr(self.auth_handler, 'login'):
            self.auth_handler.login()
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers if available."""
        if self.auth_handler and hasattr(self.auth_handler, 'get_auth_headers'):
            return self.auth_handler.get_auth_headers()
        return {}
    
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """GET request with authentication headers."""
        headers = kwargs.get('headers', {})
        headers.update(self.get_auth_headers())
        kwargs['headers'] = headers
        return super().get(endpoint, **kwargs)
    
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """POST request with authentication headers."""
        headers = kwargs.get('headers', {})
        headers.update(self.get_auth_headers())
        kwargs['headers'] = headers
        return super().post(endpoint, **kwargs)