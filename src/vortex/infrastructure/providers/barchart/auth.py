"""
Barchart authentication and session management.

Handles login, logout, CSRF token extraction, and session creation for Barchart.com.
"""

from typing import Dict, Any, Optional
import logging

import requests
from bs4 import BeautifulSoup

from vortex.utils.logging_utils import LoggingContext, LoggingConfiguration
from vortex.core.constants import NetworkConstants, ProviderConstants
from vortex.core.security.validation import CredentialSanitizer


class BarchartAuth:
    """Handles Barchart authentication and session management."""
    
    BARCHART_URL = ProviderConstants.Barchart.BASE_URL
    BARCHART_LOGIN_URL = BARCHART_URL + '/login'
    BARCHART_LOGOUT_URL = BARCHART_URL + '/logout'
    
    def __init__(self, username: str, password: str):
        # Comprehensive credential validation and sanitization
        sanitized_username, sanitized_password, warnings = (
            CredentialSanitizer.validate_and_sanitize_credentials(username, password)
        )
        
        # Log warnings if any (but not the actual credentials)
        if warnings:
            logger = logging.getLogger(__name__)
            masked_username = CredentialSanitizer.mask_credential(sanitized_username)
            logger.info(
                f"Credential validation warnings for user {masked_username}: {', '.join(warnings)}"
            )
        
        self.username = sanitized_username
        self.password = sanitized_password
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create and configure a requests session for Barchart."""
        session = requests.Session()
        # Use the same User-Agent as the working bc-utils project
        session.headers.update({
            'User-Agent': NetworkConstants.SIMPLE_USER_AGENT
        })
        return session
    
    def login(self):
        """Authenticate with Barchart using credentials (bc-utils methodology)."""
        config = LoggingConfiguration(entry_msg="Logging in ...", success_msg="Logged in.")
        with LoggingContext(config):
            # First, get the login page to establish session (with timeout to prevent hanging)
            resp = self.session.get(self.BARCHART_LOGIN_URL, timeout=NetworkConstants.LOGIN_REQUEST_TIMEOUT)
            
            # Extract CSRF token from the page using bc-utils approach
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Look for CSRF token in meta tag (bc-utils approach)
            csrf_token = None
            meta_token = soup.find('meta', {'name': 'csrf-token'})
            if meta_token:
                csrf_token = meta_token.get('content')
            else:
                # Fallback: look for hidden input with _token
                token_input = soup.find('input', {'name': '_token'})
                if token_input:
                    csrf_token = token_input.get('value')
            
            if not csrf_token:
                raise ValueError("CSRF token not found - authentication may have changed")
            
            # Build login payload (bc-utils style)
            payload = {
                '_token': csrf_token,
                'email': self.username,
                'password': self.password,
                'remember': '1'  # bc-utils uses '1' instead of 'on'
            }
            
            # Post login credentials (with timeout to prevent hanging)
            resp = self.session.post(self.BARCHART_LOGIN_URL, data=payload, allow_redirects=True, timeout=NetworkConstants.LOGIN_REQUEST_TIMEOUT)
            
            # Check if login was successful (bc-utils approach)
            if 'login' in resp.url.lower():
                from vortex.exceptions.providers import AuthenticationError
                raise AuthenticationError('barchart', 'Invalid Barchart credentials or login failed')
            
            # Verify status code is OK
            if resp.status_code != NetworkConstants.HTTP_OK:
                from vortex.exceptions.providers import AuthenticationError
                raise AuthenticationError('barchart', f'Login failed with status code: {resp.status_code}')
                
            # Verify we have necessary cookies for API access (optional check for testing)
            if hasattr(self.session, 'cookies') and 'laravel_session' not in self.session.cookies:
                # Only raise error if we actually have a cookies object but missing the session
                import logging
                logger = logging.getLogger(__name__)
                logger.warning('Login successful but missing expected laravel_session cookie')
    
    def logout(self):
        """Logout from Barchart session."""
        config = LoggingConfiguration(entry_msg="Logging out ...", success_msg="Logged out.")
        with LoggingContext(config):
            self.session.get(self.BARCHART_LOGOUT_URL, timeout=NetworkConstants.SHORT_REQUEST_TIMEOUT)
    
    def get_api_headers(self) -> Dict[str, str]:
        """Get headers required for API requests (bc-utils methodology)."""
        headers = {
            'User-Agent': NetworkConstants.DEFAULT_USER_AGENT,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # Add XSRF token if available
        if 'XSRF-TOKEN' in self.session.cookies:
            from urllib.parse import unquote
            headers['X-XSRF-TOKEN'] = unquote(self.session.cookies['XSRF-TOKEN'])
        
        return headers
    
    def get_xsrf_token(self) -> str:
        """Get XSRF token from cookies (bc-utils methodology)."""
        from urllib.parse import unquote
        
        if 'XSRF-TOKEN' in self.session.cookies:
            return unquote(self.session.cookies['XSRF-TOKEN'])
        
        # If no XSRF token in cookies, try to get one by visiting a page
        import logging
        logger = logging.getLogger(__name__)
        logger.info("No XSRF token in cookies, attempting to obtain one")
        
        # Visit main page to get XSRF token
        resp = self.session.get(self.BARCHART_URL, timeout=NetworkConstants.LOGIN_REQUEST_TIMEOUT)
        
        if 'XSRF-TOKEN' in self.session.cookies:
            return unquote(self.session.cookies['XSRF-TOKEN'])
        
        raise ValueError("Unable to obtain XSRF token from Barchart")
    
    def make_api_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make authenticated API request using bc-utils methodology."""
        import json
        import logging
        logger = logging.getLogger(__name__)
        
        headers = self.get_api_headers()
        
        try:
            if params:
                response = self.session.get(url, headers=headers, params=params, timeout=NetworkConstants.DEFAULT_REQUEST_TIMEOUT)
            else:
                response = self.session.get(url, headers=headers, timeout=NetworkConstants.DEFAULT_REQUEST_TIMEOUT)
            
            response.raise_for_status()
            
            if response.headers.get('content-type', '').startswith('application/json'):
                return response.json()
            else:
                # Handle CSV or other text responses
                return {'data': response.text, 'content_type': response.headers.get('content-type', '')}
                
        except requests.exceptions.Timeout as e:
            logger.error(f"API request timeout: {url} (timeout: {NetworkConstants.DEFAULT_REQUEST_TIMEOUT})")
            raise
        except requests.exceptions.ConnectionError as e:
            logger.error(f"API connection failed: {url}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"API HTTP error: {url}, status: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected API request error: {url}, error: {str(e)}")
            raise