"""
Barchart-specific HTTP client with clean separation of concerns.

This module extends the base HTTP client to handle Barchart-specific
authentication and request patterns.
"""

import json
import logging
from datetime import datetime
from typing import Dict, Tuple

import requests

from vortex.infrastructure.http import AuthenticatedHttpClient
from vortex.models.period import FrequencyAttributes
from vortex.utils.logging_utils import LoggingContext


class BarchartHttpClient(AuthenticatedHttpClient):
    """HTTP client specifically configured for Barchart API interactions."""

    # API endpoints
    DOWNLOAD_ENDPOINT = "/my/download"
    USAGE_ENDPOINT = "/my/download"  # Same endpoint with different payload

    def __init__(self, auth_handler):
        """Initialize Barchart HTTP client.

        Args:
            auth_handler: BarchartAuth instance for authentication
        """
        super().__init__(
            base_url="https://www.barchart.com",
            auth_handler=auth_handler,
            session=auth_handler.session,  # Reuse auth session
        )
        self.logger = logging.getLogger(__name__)

    def download_data(
        self,
        symbol: str,
        frequency_attributes: FrequencyAttributes,
        start_date: datetime,
        end_date: datetime,
        xsrf_token: str,
        history_csrf_token: str,
    ) -> requests.Response:
        """Download historical data for a symbol.

        Args:
            symbol: Trading symbol
            frequency_attributes: Frequency configuration
            start_date: Start date for data
            end_date: End date for data
            xsrf_token: XSRF token for request
            history_csrf_token: History CSRF token

        Returns:
            Response containing CSV data
        """
        headers = self._build_download_headers(xsrf_token)
        payload = self._build_download_payload(
            history_csrf_token, symbol, frequency_attributes, start_date, end_date
        )

        response = self.post(self.DOWNLOAD_ENDPOINT, data=payload, headers=headers)

        self.logger.debug(
            f"Download request for {symbol}: "
            f"status={response.status_code}, "
            f"size={len(response.content)} bytes"
        )

        return response

    def check_usage(self, xsrf_token: str) -> Tuple[Dict, str]:
        """Check current download usage/allowance.

        Args:
            xsrf_token: Current XSRF token

        Returns:
            Tuple of (usage_data dict, new_xsrf_token)
        """
        from vortex.utils.logging_utils import LoggingConfiguration

        config = LoggingConfiguration(
            entry_msg="Checking usage", success_msg="Checked usage"
        )
        with LoggingContext(config):
            headers = self._build_usage_headers(xsrf_token)
            payload = {"check": True}

            response = self.post(self.USAGE_ENDPOINT, data=payload, headers=headers)

            # Get fresh token after request
            new_xsrf_token = self.auth_handler.get_xsrf_token()

            usage_data = json.loads(response.text)
            self.logger.debug(f"Usage data: {usage_data}")

            return usage_data, new_xsrf_token

    def _build_download_headers(self, xsrf_token: str) -> Dict[str, str]:
        """Build headers for download request."""
        return {
            "X-XSRF-TOKEN": xsrf_token,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": f"{self.base_url}/my/download",
            "X-Requested-With": "XMLHttpRequest",
        }

    def _build_usage_headers(self, xsrf_token: str) -> Dict[str, str]:
        """Build headers for usage check request."""
        return self._build_download_headers(xsrf_token)

    def _build_download_payload(
        self,
        history_csrf_token: str,
        symbol: str,
        frequency_attributes: FrequencyAttributes,
        start_date: datetime,
        end_date: datetime,
    ) -> Dict[str, str]:
        """Build payload for download request."""
        return {
            "_token": history_csrf_token,
            "fileName": symbol,
            "symbol": symbol,
            "startDate": start_date.strftime("%m/%d/%Y"),
            "endDate": end_date.strftime("%m/%d/%Y"),
            "period": str(frequency_attributes.frequency).lower(),
            "maxRecords": "5000",  # Default max records
            "order": "asc",
            "dividends": "false",
            "backadjust": "false",
            "dbar": "1",
            "custombar": "",
            "volume": "true",
            "openInterest": "true",
            "splits": "true",
        }
