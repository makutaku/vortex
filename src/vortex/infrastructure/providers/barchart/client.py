"""
Barchart HTTP client and request handling.

Handles all HTTP requests, downloads, and usage checking for Barchart data.
"""

import json
import logging
import time
from datetime import datetime

import requests

from vortex.models.period import FrequencyAttributes
from vortex.utils.logging_utils import LoggingContext, LoggingConfiguration
from vortex.core.constants import ProviderConstants, NetworkConstants
from .auth import BarchartAuth

# Optional metrics - graceful fallback if not available
try:
    from vortex.infrastructure.metrics import get_metrics
    _metrics_available = True
except ImportError:
    _metrics_available = False


class BarchartClient:
    """HTTP client for Barchart data downloads and API requests."""
    
    BARCHART_URL = ProviderConstants.Barchart.BASE_URL
    BARCHART_DOWNLOAD_URL = BARCHART_URL + ProviderConstants.Barchart.DOWNLOAD_ENDPOINT
    BARCHART_USAGE_URL = BARCHART_DOWNLOAD_URL
    
    def __init__(self, auth: BarchartAuth):
        self.auth = auth
        self.session = auth.session
        self._metrics = get_metrics() if _metrics_available else None
    
    def request_download(self, xsrf_token: str, history_csrf_token: str, symbol: str,
                        frequency_attributes: FrequencyAttributes, url: str,
                        start_date: datetime, end_date: datetime) -> requests.Response:
        """Request data download from Barchart."""
        start_time = time.time()
        
        try:
            headers = self._build_download_request_headers(xsrf_token, url)
            payload = self._build_download_request_payload(history_csrf_token, symbol, frequency_attributes,
                                                          start_date, end_date)
            resp = self.session.post(self.BARCHART_DOWNLOAD_URL, headers=headers, data=payload, timeout=NetworkConstants.LONG_REQUEST_TIMEOUT)
            
            # Record success metrics
            duration = time.time() - start_time
            if self._metrics:
                self._metrics.record_provider_request('barchart', 'download', duration, True)
                if hasattr(resp, 'content') and resp.content:
                    # Estimate row count from response size (rough approximation)
                    estimated_rows = len(resp.content) // 50  # ~50 bytes per row estimate
                    self._metrics.record_download('barchart', symbol, estimated_rows, True)
            
            logging.debug(f"POST {self.BARCHART_DOWNLOAD_URL}, "
                         f"status: {resp.status_code}, "
                         f"data length: {len(resp.content)}")
            return resp
            
        except Exception as e:
            # Record failure metrics
            duration = time.time() - start_time
            if self._metrics:
                self._metrics.record_provider_request('barchart', 'download', duration, False)
                self._metrics.record_download('barchart', symbol, 0, False)
                self._metrics.record_error(type(e).__name__, 'barchart', 'download')
            raise
    
    def fetch_usage(self, url: str, xsrf_token: str) -> tuple[dict, str]:
        """Check download usage count."""
        start_time = time.time()
        config = LoggingConfiguration(entry_msg="Checking usage", 
                                     success_msg="Checked usage")
        
        try:
            with LoggingContext(config):
                headers = self._build_usage_request_headers(url, xsrf_token)
                payload = self._build_usage_payload()
                resp = self.session.post(self.BARCHART_USAGE_URL, headers=headers, data=payload, timeout=NetworkConstants.DEFAULT_REQUEST_TIMEOUT)
                xsrf_token = self.auth.get_xsrf_token()
                usage_data = json.loads(resp.text)
                logging.debug(f"usage data: {usage_data}")
                
                # Record success metrics
                duration = time.time() - start_time
                if self._metrics:
                    self._metrics.record_provider_request('barchart', 'usage_check', duration, True)
                
                return usage_data, xsrf_token
                
        except Exception as e:
            # Record failure metrics
            duration = time.time() - start_time
            if self._metrics:
                self._metrics.record_provider_request('barchart', 'usage_check', duration, False)
                self._metrics.record_error(type(e).__name__, 'barchart', 'usage_check')
            raise
    
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