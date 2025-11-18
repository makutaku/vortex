"""
Barchart usage checking and validation.

Extracted from BarchartProvider to implement single responsibility principle.
Handles usage limit checking and allowance validation.
"""

import logging
from typing import Optional, Tuple

from vortex.exceptions.providers import AllowanceLimitExceededError
from vortex.constants import ProviderConstants, NetworkConstants

from .auth import BarchartAuth
from .client import BarchartClient


class BarchartUsageChecker:
    """Handles usage checking and allowance validation for Barchart provider."""
    
    def __init__(self, auth: BarchartAuth, client: BarchartClient, daily_limit: int):
        self.auth = auth
        self.client = client
        self.daily_limit = daily_limit
        self.logger = logging.getLogger(__name__)
    
    def check_server_usage(self) -> Optional[int]:
        """Check current usage count from Barchart server using bc-utils methodology.
        
        Returns:
            Current usage count if successful, None if failed
        """
        try:
            # Use exact bc-utils approach: GET home page for CSRF token, then POST with onlyCheckPermissions
            url = ProviderConstants.Barchart.BASE_URL
            home_response = self.auth.session.get(url, timeout=NetworkConstants.DEFAULT_REQUEST_TIMEOUT)
            
            if home_response.status_code != NetworkConstants.HTTP_OK:
                self.logger.debug(f"Cannot access home page for usage check: {home_response.status_code}")
                return None
            
            # Extract CSRF token using shared method
            csrf_token = self._extract_csrf_token(home_response)
            if not csrf_token:
                self.logger.debug("No CSRF token found for usage check")
                return None
            
            # Build payload exactly like bc-utils (this is the secret!)
            payload = {
                'onlyCheckPermissions': 'true'  # This is the bc-utils secret!
            }
            
            headers = {
                'User-Agent': NetworkConstants.DEFAULT_USER_AGENT,
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Accept-Language': 'en-US,en;q=0.9',
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-TOKEN': csrf_token
            }
            
            # POST to download endpoint with onlyCheckPermissions
            download_url = url + ProviderConstants.Barchart.DOWNLOAD_ENDPOINT
            resp = self.auth.session.post(download_url, headers=headers, data=payload, 
                                        timeout=NetworkConstants.DEFAULT_REQUEST_TIMEOUT)
            
            if resp.status_code == NetworkConstants.HTTP_OK:
                try:
                    # Parse JSON response that contains usage information
                    json_data = resp.json()
                    self.logger.debug(f"Usage check raw response: {json_data}")
                    
                    # Check for error (bc-utils approach)
                    if json_data.get("error") is not None:
                        self.logger.debug(f"Usage check error: {json_data.get('error')}")
                        return None
                    
                    # Check for success and count (bc-utils approach) - this is the correct format!
                    if json_data.get("success"):
                        used_count = int(json_data.get('count', '0'))
                        self.logger.debug(f"bc-utils usage success: {json_data['success']}, count: {used_count}")
                        return used_count
                    else:
                        self.logger.debug(f"Usage check unsuccessful: {json_data}")
                        return None
                    
                except Exception as parse_error:
                    self.logger.debug(f"Could not parse usage response: {parse_error}")
                    return None
            else:
                self.logger.debug(f"Usage check failed with status: {resp.status_code}")
                return None
                
        except Exception as e:
            self.logger.debug(f"Exception during usage check: {e}")
            return None
    
    def validate_daily_limit(self) -> None:
        """Validate that we haven't exceeded the daily download limit.
        
        Raises:
            AllowanceLimitExceededError: If daily limit is exceeded
        """
        current_usage = self.check_server_usage()
        if current_usage is not None:
            if current_usage >= self.daily_limit:
                raise AllowanceLimitExceededError(
                    provider='barchart',
                    limit=self.daily_limit,
                    current_usage=current_usage
                )
            
            remaining = self.daily_limit - current_usage
            self.logger.info(f"Usage check: {current_usage}/{self.daily_limit} downloads used, {remaining} remaining")
        else:
            self.logger.warning("Could not verify usage count - proceeding with download")
    
    def fetch_usage_data(self, url: str, xsrf_token: str) -> Tuple[dict, str]:
        """Fetch usage data using the client."""
        return self.client.fetch_usage(url, xsrf_token)
    
    def _extract_csrf_token(self, home_response) -> Optional[str]:
        """Extract CSRF token from Barchart home page response."""
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(home_response.text, 'html.parser')
            
            # Look for meta CSRF token (the correct token type)
            meta_token = soup.find('meta', {'name': 'csrf-token'})
            if meta_token:
                csrf_token = meta_token.get('content')
                self.logger.debug(f"Found meta CSRF token: {csrf_token[:20]}...")
                return csrf_token
            else:
                self.logger.debug("No meta CSRF token found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error extracting CSRF token: {e}")
            return None