"""
Sensitive Data Sanitization Module.

This module provides utilities for sanitizing sensitive data before storage,
logging, or transmission to prevent credential leakage and security vulnerabilities.
"""

from typing import Any, Dict, Set


class SensitiveDataSanitizer:
    """Sanitize sensitive data from payloads, headers, and metadata."""

    # Sensitive keys that should be redacted in payloads
    SENSITIVE_PAYLOAD_KEYS: Set[str] = {
        "password",
        "passwd",
        "pwd",
        "token",
        "_token",
        "csrf",
        "xsrf",
        "csrf_token",
        "xsrf_token",
        "api_key",
        "apikey",
        "secret",
        "authorization",
        "auth",
        "bearer",
        "session",
        "sessionid",
        "session_id",
        "cookie",
        "set_cookie",
    }

    # Sensitive headers that should be redacted
    SENSITIVE_HEADER_KEYS: Set[str] = {
        "authorization",
        "x-api-key",
        "x-apikey",
        "cookie",
        "set-cookie",
        "x-csrf-token",
        "x-xsrf-token",
        "proxy-authorization",
        "www-authenticate",
        "proxy-authenticate",
        "x-auth-token",
        "x-session-token",
    }

    @classmethod
    def sanitize_payload(cls, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Remove or mask sensitive payload fields.

        Args:
            payload: Dictionary containing request payload data

        Returns:
            Sanitized copy of payload with sensitive fields redacted
        """
        if not isinstance(payload, dict):
            return payload

        sanitized = {}

        for key, value in payload.items():
            key_lower = key.lower()

            # Check if key contains any sensitive keyword
            if any(sensitive in key_lower for sensitive in cls.SENSITIVE_PAYLOAD_KEYS):
                # Replace with redacted placeholder showing length
                if isinstance(value, str):
                    sanitized[key] = f"[REDACTED_{len(value)}_CHARS]"
                elif isinstance(value, (int, float)):
                    sanitized[key] = "[REDACTED_NUMBER]"
                else:
                    sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                sanitized[key] = cls.sanitize_payload(value)
            elif isinstance(value, list):
                # Sanitize lists (may contain dicts)
                sanitized[key] = [
                    cls.sanitize_payload(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                # Keep non-sensitive values as-is
                sanitized[key] = value

        return sanitized

    @classmethod
    def sanitize_headers(cls, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove or mask sensitive headers.

        Args:
            headers: Dictionary containing HTTP headers

        Returns:
            Sanitized copy of headers with sensitive fields redacted
        """
        if not isinstance(headers, dict):
            return headers

        sanitized = {}

        for key, value in headers.items():
            key_lower = key.lower()

            # Check if header is sensitive
            if any(sensitive in key_lower for sensitive in cls.SENSITIVE_HEADER_KEYS):
                sanitized[key] = "[REDACTED]"
            else:
                # Keep non-sensitive headers
                sanitized[key] = value

        return sanitized

    @classmethod
    def sanitize_url(cls, url: str) -> str:
        """Remove credentials from URL if present.

        Args:
            url: URL that may contain credentials

        Returns:
            Sanitized URL with credentials removed
        """
        if not isinstance(url, str):
            return url

        # Check for credentials in URL (http://user:pass@host)
        if "@" in url and "://" in url:
            protocol, rest = url.split("://", 1)
            if "@" in rest:
                # Has credentials
                credentials, host_and_path = rest.split("@", 1)
                return f"{protocol}://[REDACTED]@{host_and_path}"

        return url

    @classmethod
    def sanitize_request_metadata(
        cls, request_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Sanitize complete request metadata before storage.

        Args:
            request_metadata: Full request metadata dictionary

        Returns:
            Sanitized copy of request metadata
        """
        if not isinstance(request_metadata, dict):
            return request_metadata

        sanitized = {}

        for key, value in request_metadata.items():
            if key == "payload" and isinstance(value, dict):
                # Sanitize request payload
                sanitized[key] = cls.sanitize_payload(value)
            elif key in ("headers", "response_headers") and isinstance(value, dict):
                # Sanitize headers
                sanitized[key] = cls.sanitize_headers(value)
            elif key == "url" and isinstance(value, str):
                # Sanitize URL
                sanitized[key] = cls.sanitize_url(value)
            elif isinstance(value, dict):
                # Recursively sanitize nested dicts
                sanitized[key] = cls.sanitize_request_metadata(value)
            else:
                # Keep other fields as-is (method, status, etc.)
                sanitized[key] = value

        return sanitized
