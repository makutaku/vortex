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
            tag = soup.find(type='hidden')
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
        """Extract XSRF token from response."""
        soup = BeautifulSoup(hist_resp.text, 'html.parser')
        return soup.find(attrs={'name': 'csrf-token'})['content']
    
    @staticmethod  
    def scrape_csrf_token(hist_resp) -> str:
        """Extract CSRF token from historical data response."""
        soup = BeautifulSoup(hist_resp.text, 'html.parser')
        hist_csrf_token = soup.find(id='hist-csrf-token')['value']
        return hist_csrf_token