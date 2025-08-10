"""
Barchart authentication and session management.

Handles login, logout, CSRF token extraction, and session creation for Barchart.com.
"""

import requests
from bs4 import BeautifulSoup

from vortex.utils.logging_utils import LoggingContext


class BarchartAuth:
    """Handles Barchart authentication and session management."""
    
    BARCHART_URL = 'https://www.barchart.com'
    BARCHART_LOGIN_URL = BARCHART_URL + '/login'
    BARCHART_LOGOUT_URL = BARCHART_URL + '/logout'
    
    def __init__(self, username: str, password: str):
        if not username or not password:
            raise Exception('Barchart credentials are required')
        
        self.username = username
        self.password = password
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create and configure a requests session for Barchart."""
        session = requests.Session()
        # Use the same User-Agent as the working bc-utils project
        session.headers.update({
            'User-Agent': 'Mozilla/5.0'
        })
        return session
    
    def login(self):
        """Authenticate with Barchart using credentials."""
        with LoggingContext(entry_msg="Logging in ...", success_msg="Logged in."):
            # GET the login page, scrape to get CSRF token (using bc-utils approach)
            resp = self.session.get(self.BARCHART_LOGIN_URL)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Use the same approach as working bc-utils project
            tag = soup.find(type='hidden')
            if tag is None:
                raise ValueError("Login CSRF token not found - Barchart login page may have changed authentication method")
            csrf_token = tag.attrs['value']
            
            # Login to site
            payload = self._build_login_payload(csrf_token, self.username, self.password)
            resp = self.session.post(self.BARCHART_LOGIN_URL, data=payload)
            
            if resp.url == self.BARCHART_LOGIN_URL:
                raise Exception('Invalid Barchart credentials')
    
    def logout(self):
        """Logout from Barchart session."""
        with LoggingContext(entry_msg="Logging out ...", success_msg="Logged out."):
            self.session.get(self.BARCHART_LOGOUT_URL, timeout=10)
    
    @staticmethod
    def _build_login_payload(csrf_token: str, username: str, password: str) -> dict:
        """Build login request payload."""
        return {
            '_token': csrf_token,
            'email': username,
            'password': password,
            'remember': 'on',
            'g-recaptcha-response': ''
        }
    
    @staticmethod
    def extract_xsrf_token(hist_resp) -> str:
        """Extract XSRF token from response with adaptive fallbacks."""
        soup = BeautifulSoup(hist_resp.text, 'html.parser')
        
        # Check if this might be a login redirect or different page structure
        if "login" in hist_resp.url.lower() or "sign" in hist_resp.url.lower():
            raise ValueError("Redirected to login page - authentication may have expired")
        
        # Try multiple possible CSRF token formats
        token_selectors = [
            # Original format
            {'attrs': {'name': 'csrf-token'}, 'attr': 'content'},
            # Meta tag variations
            {'name': 'meta', 'attrs': {'name': 'csrf-token'}, 'attr': 'content'},
            {'name': 'meta', 'attrs': {'name': '_token'}, 'attr': 'content'},
            {'name': 'meta', 'attrs': {'name': 'X-CSRF-TOKEN'}, 'attr': 'content'},
            # Hidden input variations  
            {'name': 'input', 'attrs': {'name': '_token'}, 'attr': 'value'},
            {'name': 'input', 'attrs': {'name': 'csrf_token'}, 'attr': 'value'},
            {'name': 'input', 'attrs': {'name': 'authenticity_token'}, 'attr': 'value'},
            # JavaScript variable extraction (common in modern sites)
            {'script_var': '_csrf_token'},
            {'script_var': 'window.csrf_token'},
            {'script_var': 'csrfToken'},
            {'script_var': 'window._token'},
        ]
        
        for selector in token_selectors:
            if 'script_var' in selector:
                # Extract from JavaScript variables
                scripts = soup.find_all('script')
                for script in scripts:
                    if script.string and selector['script_var'] in script.string:
                        # Simple regex to extract token value
                        import re
                        pattern = rf'{selector["script_var"]}\s*[=:]\s*["\']([^"\']+)["\']'
                        match = re.search(pattern, script.string)
                        if match:
                            return match.group(1)
            else:
                # Extract from HTML elements
                element = soup.find(selector.get('name'), selector.get('attrs', {}))
                if element and element.get(selector['attr']):
                    return element[selector['attr']]
        
        # Debug: Log what we actually found in the page
        import logging
        logger = logging.getLogger(__name__)
        
        # Extract first 500 chars of page content for diagnostics
        page_preview = hist_resp.text[:500] if hist_resp.text else "No content"
        logger.error(f"CSRF token extraction failed. Page preview: {page_preview}")
        
        # Look for any script tags or forms that might indicate new auth method
        forms = soup.find_all('form')
        scripts = soup.find_all('script')
        logger.error(f"Found {len(forms)} forms and {len(scripts)} script tags")
        
        if forms:
            for i, form in enumerate(forms[:3]):  # Log first 3 forms
                logger.error(f"Form {i}: {form}")
        
        raise ValueError("CSRF token not found in page - Barchart may have updated their authentication system. Please check for updates to Vortex.")
    
    @staticmethod  
    def scrape_csrf_token(hist_resp) -> str:
        """Extract CSRF token from historical data response with adaptive fallbacks."""
        soup = BeautifulSoup(hist_resp.text, 'html.parser')
        
        # Try multiple possible historical CSRF token formats
        token_selectors = [
            # Original format
            {'id': 'hist-csrf-token', 'attr': 'value'},
            # Common variations
            {'name': 'input', 'attrs': {'name': 'hist_csrf_token'}, 'attr': 'value'},
            {'name': 'input', 'attrs': {'name': 'download_token'}, 'attr': 'value'},
            {'name': 'input', 'attrs': {'class': 'csrf-token'}, 'attr': 'value'},
            # Data attributes
            {'attrs': {'data-csrf-token': True}, 'data_attr': 'data-csrf-token'},
            {'attrs': {'data-download-token': True}, 'data_attr': 'data-download-token'},
        ]
        
        for selector in token_selectors:
            if 'id' in selector:
                element = soup.find(id=selector['id'])
                if element and element.get(selector['attr']):
                    return element[selector['attr']]
            elif 'data_attr' in selector:
                element = soup.find(attrs=selector['attrs'])
                if element and element.get(selector['data_attr']):
                    return element[selector['data_attr']]
            else:
                element = soup.find(selector.get('name'), selector.get('attrs', {}))
                if element and element.get(selector['attr']):
                    return element[selector['attr']]
        
        # Debug: Log what we actually found in the page
        import logging
        logger = logging.getLogger(__name__)
        
        # Extract first 500 chars of page content for diagnostics
        page_preview = hist_resp.text[:500] if hist_resp.text else "No content"
        logger.error(f"Historical CSRF token extraction failed. Page preview: {page_preview}")
        
        # Look for download-related elements
        download_links = soup.find_all('a', href=True)
        download_forms = soup.find_all('form')
        logger.error(f"Found {len(download_links)} links and {len(download_forms)} forms")
        
        # Check for any download buttons or elements
        download_buttons = soup.find_all(['button', 'input'], {'type': ['submit', 'button']})
        logger.error(f"Found {len(download_buttons)} potential download buttons")
        
        if download_forms:
            for i, form in enumerate(download_forms[:2]):  # Log first 2 forms
                logger.error(f"Download form {i}: {form}")
        
        raise ValueError("Historical CSRF token not found in page - Barchart may have updated their download system. Please check for updates to Vortex.")