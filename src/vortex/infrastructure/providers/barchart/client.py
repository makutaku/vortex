"""
Barchart HTTP client and request handling.

Handles all HTTP requests, downloads, and usage checking for Barchart data.
"""

import json
import logging
from datetime import datetime

import requests

from vortex.models.period import FrequencyAttributes
from vortex.utils.logging_utils import LoggingContext, LoggingConfiguration
from vortex.core.constants import ProviderConstants, NetworkConstants
from .auth import BarchartAuth


class BarchartClient:
    """HTTP client for Barchart data downloads and API requests."""
    
    BARCHART_URL = ProviderConstants.Barchart.BASE_URL
    BARCHART_DOWNLOAD_URL = BARCHART_URL + ProviderConstants.Barchart.DOWNLOAD_ENDPOINT
    BARCHART_USAGE_URL = BARCHART_DOWNLOAD_URL
    
    def __init__(self, auth: BarchartAuth):
        self.auth = auth
        self.session = auth.session
    
    def request_download(self, xsrf_token: str, history_csrf_token: str, symbol: str,
                        frequency_attributes: FrequencyAttributes, url: str,
                        start_date: datetime, end_date: datetime) -> requests.Response:
        """Request data download from Barchart."""
        headers = self._build_download_request_headers(xsrf_token, url)
        payload = self._build_download_request_payload(history_csrf_token, symbol, frequency_attributes,
                                                      start_date, end_date)
        resp = self.session.post(self.BARCHART_DOWNLOAD_URL, headers=headers, data=payload, timeout=NetworkConstants.LONG_REQUEST_TIMEOUT)
        logging.debug(f"POST {self.BARCHART_DOWNLOAD_URL}, "
                     f"status: {resp.status_code}, "
                     f"data length: {len(resp.content)}")
        return resp
    
    def fetch_usage(self, url: str, xsrf_token: str) -> tuple[dict, str]:
        """Check download usage count."""
        config = LoggingConfiguration(entry_msg="Checking usage", 
                                     success_msg="Checked usage")
        with LoggingContext(config):
            headers = self._build_usage_request_headers(url, xsrf_token)
            payload = self._build_usage_payload()
            resp = self.session.post(self.BARCHART_USAGE_URL, headers=headers, data=payload, timeout=NetworkConstants.DEFAULT_REQUEST_TIMEOUT)
            xsrf_token = self.auth.get_xsrf_token()
            usage_data = json.loads(resp.text)
            logging.debug(f"usage data: {usage_data}")
            return usage_data, xsrf_token
    
    def _build_download_request_payload(self, history_csrf_token: str, symbol: str, 
                                       frequency_attributes: FrequencyAttributes, 
                                       start_date: datetime, end_date: datetime) -> dict:
        """Build payload for download request with configurable parameters."""
        return {
            '_token': history_csrf_token,
            'fileName': symbol,
            'symbol': symbol,
            'startDate': start_date.strftime("%m/%d/%Y"),
            'endDate': end_date.strftime("%m/%d/%Y"),
            'period': frequency_attributes.name.lower(),
            'maxRecords': frequency_attributes.max_records_per_download,
            'order': getattr(self, 'order', ProviderConstants.Barchart.DEFAULT_ORDER),
            'dividends': getattr(self, 'dividends', ProviderConstants.Barchart.DEFAULT_DIVIDENDS),
            'backadjust': getattr(self, 'backadjust', ProviderConstants.Barchart.DEFAULT_BACKADJUST),
            'dbar': getattr(self, 'dbar', ProviderConstants.Barchart.DEFAULT_DBAR),
            'custombar': getattr(self, 'custombar', ProviderConstants.Barchart.DEFAULT_CUSTOMBAR),
            'volume': getattr(self, 'volume', ProviderConstants.Barchart.DEFAULT_VOLUME),
            'openInterest': getattr(self, 'openInterest', ProviderConstants.Barchart.DEFAULT_OPEN_INTEREST),
            'splits': getattr(self, 'splits', ProviderConstants.Barchart.DEFAULT_SPLITS)
        }
    
    def _build_download_request_headers(self, xsrf_token: str, url: str) -> dict:
        """Build headers for download request with configurable content type."""
        return {
            'Content-Type': getattr(self, 'content_type', 'application/x-www-form-urlencoded; charset=UTF-8'),
            'X-CSRF-TOKEN': xsrf_token,
            'X-Requested-With': getattr(self, 'requested_with', 'XMLHttpRequest'),
            'Referer': url
        }
    
    def _build_usage_request_headers(self, url: str, xsrf_token: str) -> dict:
        """Build headers for usage request with configurable content type."""
        return {
            'Content-Type': getattr(self, 'usage_content_type', 'application/x-www-form-urlencoded; charset=UTF-8'),
            'X-CSRF-TOKEN': xsrf_token,
            'X-Requested-With': getattr(self, 'usage_requested_with', 'XMLHttpRequest'),
            'Referer': url
        }
    
    def _build_usage_payload(self) -> dict:
        """Build payload for usage request with configurable type."""
        return {
            'type': getattr(self, 'usage_type', ProviderConstants.Barchart.DEFAULT_USAGE_TYPE)
        }