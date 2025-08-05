"""
Barchart HTTP client and request handling.

Handles all HTTP requests, downloads, and allowance checking for Barchart data.
"""

import json
import logging
from datetime import datetime

import requests

from vortex.models.period import FrequencyAttributes
from vortex.shared.utils.logging_utils import LoggingContext
from .auth import BarchartAuth


class BarchartClient:
    """HTTP client for Barchart data downloads and API requests."""
    
    BARCHART_URL = 'https://www.barchart.com'
    BARCHART_DOWNLOAD_URL = BARCHART_URL + '/my/download'
    BARCHART_ALLOWANCE_URL = BARCHART_DOWNLOAD_URL
    
    def __init__(self, auth: BarchartAuth):
        self.auth = auth
        self.session = auth.session
    
    def request_download(self, xsrf_token: str, hist_csrf_token: str, symbol: str,
                        freq_attrs: FrequencyAttributes, url: str,
                        start_date: datetime, end_date: datetime) -> requests.Response:
        """Request data download from Barchart."""
        headers = self._build_download_request_headers(xsrf_token, url)
        payload = self._build_download_request_payload(hist_csrf_token, symbol, freq_attrs,
                                                      start_date, end_date)
        resp = self.session.post(self.BARCHART_DOWNLOAD_URL, headers=headers, data=payload)
        logging.debug(f"POST {self.BARCHART_DOWNLOAD_URL}, "
                     f"status: {resp.status_code}, "
                     f"data length: {len(resp.content)}")
        return resp
    
    def fetch_allowance(self, url: str, xsf_token: str) -> tuple[dict, str]:
        """Check download allowance remaining."""
        with LoggingContext(entry_msg="Checking allowance", 
                           success_msg="Checked allowance"):
            headers = self._build_allowance_request_headers(url, xsf_token)
            payload = self._build_allowance_payload()
            resp = self.session.post(self.BARCHART_ALLOWANCE_URL, headers=headers, data=payload)
            xsf_token = self.auth.extract_xsrf_token(resp)
            allowance = json.loads(resp.text)
            logging.debug(f"allowance: {allowance}")
            return allowance, xsf_token
    
    @staticmethod
    def _build_download_request_payload(hist_csrf_token: str, symbol: str, 
                                       freq_attrs: FrequencyAttributes, 
                                       start_date: datetime, end_date: datetime) -> dict:
        """Build payload for download request."""
        return {
            '_token': hist_csrf_token,
            'fileName': symbol,
            'symbol': symbol,
            'startDate': start_date.strftime("%m/%d/%Y"),
            'endDate': end_date.strftime("%m/%d/%Y"),
            'period': freq_attrs.name.lower(),
            'maxRecords': freq_attrs.max_records_per_download,
            'order': 'asc',
            'dividends': 'false',
            'backadjust': 'false',
            'dbar': 1,
            'custombar': '',
            'volume': 'true',
            'openInterest': 'true',
            'splits': 'true'
        }
    
    @staticmethod
    def _build_download_request_headers(xsrf_token: str, url: str) -> dict:
        """Build headers for download request."""
        return {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-CSRF-TOKEN': xsrf_token,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': url
        }
    
    @staticmethod  
    def _build_allowance_request_headers(url: str, xsf_token: str) -> dict:
        """Build headers for allowance request."""
        return {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-CSRF-TOKEN': xsf_token,
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': url
        }
    
    @staticmethod
    def _build_allowance_payload() -> dict:
        """Build payload for allowance request."""
        return {
            'type': 'quotes'
        }