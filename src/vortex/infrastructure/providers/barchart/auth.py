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
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
        })
        return session
    
    def login(self):
        """Authenticate with Barchart using credentials."""
        with LoggingContext(entry_msg="Logging in ...", success_msg="Logged in."):
            # GET the login page, scrape to get CSRF token
            resp = self.session.get(self.BARCHART_LOGIN_URL)
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Try multiple ways to find the login token
            csrf_token = None
            token_selectors = [
                # Original method
                {'type': 'hidden'},
                # Common CSRF token locations
                {'name': 'input', 'attrs': {'name': '_token'}},
                {'name': 'input', 'attrs': {'name': 'csrf_token'}},
                {'name': 'meta', 'attrs': {'name': 'csrf-token'}},
            ]
            
            for selector in token_selectors:
                if 'type' in selector:
                    tag = soup.find(type=selector['type'])
                    if tag and 'value' in tag.attrs:
                        csrf_token = tag.attrs['value']
                        break
                else:
                    tag = soup.find(selector['name'], selector.get('attrs', {}))
                    if tag:
                        if selector['name'] == 'meta' and 'content' in tag.attrs:
                            csrf_token = tag.attrs['content']
                            break
                        elif 'value' in tag.attrs:
                            csrf_token = tag.attrs['value']
                            break
            
            if csrf_token is None:
                raise ValueError("Login CSRF token not found - Barchart login page may have changed authentication method")
            
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
        
        # Try multiple possible CSRF token formats
        token_selectors = [
            # Original format
            {'attrs': {'name': 'csrf-token'}, 'attr': 'content'},
            # Meta tag variations
            {'name': 'meta', 'attrs': {'name': 'csrf-token'}, 'attr': 'content'},
            {'name': 'meta', 'attrs': {'name': '_token'}, 'attr': 'content'},
            # Hidden input variations  
            {'name': 'input', 'attrs': {'name': '_token'}, 'attr': 'value'},
            {'name': 'input', 'attrs': {'name': 'csrf_token'}, 'attr': 'value'},
            # JavaScript variable extraction (common in modern sites)
            {'script_var': '_csrf_token'},
            {'script_var': 'window.csrf_token'},
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
        
        raise ValueError("Historical CSRF token not found in page - Barchart may have updated their download system. Please check for updates to Vortex.")