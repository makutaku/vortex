"""Tests for sensitive data sanitizer."""

import pytest

from vortex.core.security.sanitizer import SensitiveDataSanitizer


class TestSensitiveDataSanitizer:
    """Test sensitive data sanitization functionality."""

    def test_sanitize_payload_with_password(self):
        """Test sanitization of password in payload."""
        payload = {"username": "testuser", "password": "secret123", "data": "public"}

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        assert sanitized["username"] == "testuser"
        assert sanitized["password"] == "[REDACTED_9_CHARS]"
        assert sanitized["data"] == "public"

    def test_sanitize_payload_nested_dict(self):
        """Test sanitization of nested dictionary."""
        payload = {
            "user": {"name": "test", "password": "secret"},
            "api_key": "key123",
            "public": "data",
        }

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        assert sanitized["user"]["name"] == "test"
        assert sanitized["user"]["password"] == "[REDACTED_6_CHARS]"
        assert sanitized["api_key"] == "[REDACTED_6_CHARS]"
        assert sanitized["public"] == "data"

    def test_sanitize_payload_with_list(self):
        """Test sanitization of list in payload."""
        payload = {
            "credentials": [
                {"username": "user1", "password": "pass1"},
                {"username": "user2", "token": "token2"},
            ]
        }

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        assert sanitized["credentials"][0]["username"] == "user1"
        assert sanitized["credentials"][0]["password"] == "[REDACTED_5_CHARS]"
        assert sanitized["credentials"][1]["username"] == "user2"
        assert sanitized["credentials"][1]["token"] == "[REDACTED_6_CHARS]"

    def test_sanitize_payload_case_insensitive(self):
        """Test that sanitization is case insensitive."""
        payload = {
            "PASSWORD": "secret",
            "Api_Key": "key123",
            "X-CSRF-TOKEN": "token",
        }

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        assert sanitized["PASSWORD"] == "[REDACTED_6_CHARS]"
        assert sanitized["Api_Key"] == "[REDACTED_6_CHARS]"
        assert sanitized["X-CSRF-TOKEN"] == "[REDACTED_5_CHARS]"

    def test_sanitize_headers(self):
        """Test sanitization of HTTP headers."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
            "Cookie": "session=abc123",
            "X-API-Key": "secret",
        }

        sanitized = SensitiveDataSanitizer.sanitize_headers(headers)

        assert sanitized["Content-Type"] == "application/json"
        assert sanitized["Authorization"] == "[REDACTED]"
        assert sanitized["Cookie"] == "[REDACTED]"
        assert sanitized["X-API-Key"] == "[REDACTED]"

    def test_sanitize_url_with_credentials(self):
        """Test sanitization of URL with embedded credentials."""
        url = "https://user:pass@example.com/api/data"

        sanitized = SensitiveDataSanitizer.sanitize_url(url)

        assert sanitized == "https://[REDACTED]@example.com/api/data"

    def test_sanitize_url_without_credentials(self):
        """Test sanitization of URL without credentials."""
        url = "https://example.com/api/data"

        sanitized = SensitiveDataSanitizer.sanitize_url(url)

        assert sanitized == url

    def test_sanitize_url_with_port(self):
        """Test sanitization of URL with port and credentials."""
        url = "https://admin:secret@example.com:8080/api"

        sanitized = SensitiveDataSanitizer.sanitize_url(url)

        assert sanitized == "https://[REDACTED]@example.com:8080/api"

    def test_sanitize_request_metadata_complete(self):
        """Test complete request metadata sanitization."""
        metadata = {
            "url": "https://user:pass@api.example.com/data",
            "method": "POST",
            "headers": {
                "Authorization": "Bearer token",
                "Content-Type": "application/json",
            },
            "payload": {"username": "test", "password": "secret", "data": "public"},
        }

        sanitized = SensitiveDataSanitizer.sanitize_request_metadata(metadata)

        assert sanitized["url"] == "https://[REDACTED]@api.example.com/data"
        assert sanitized["method"] == "POST"
        assert sanitized["headers"]["Authorization"] == "[REDACTED]"
        assert sanitized["headers"]["Content-Type"] == "application/json"
        assert sanitized["payload"]["username"] == "test"
        assert sanitized["payload"]["password"] == "[REDACTED_6_CHARS]"
        assert sanitized["payload"]["data"] == "public"

    def test_sanitize_request_metadata_with_payload_data(self):
        """Test sanitization of payload data in request metadata."""
        metadata = {
            "url": "https://example.com/login",
            "payload": {"username": "user", "password": "pass123"},
        }

        sanitized = SensitiveDataSanitizer.sanitize_request_metadata(metadata)

        assert sanitized["payload"]["username"] == "user"
        assert sanitized["payload"]["password"] == "[REDACTED_7_CHARS]"

    def test_sanitize_empty_payload(self):
        """Test sanitization of empty payload."""
        payload = {}

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        assert sanitized == {}

    def test_sanitize_none_values(self):
        """Test sanitization handles None values."""
        payload = {"username": "test", "password": None, "token": None}

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        assert sanitized["username"] == "test"
        # None values are redacted as "[REDACTED]" since they're not str/int/float
        assert sanitized["password"] == "[REDACTED]"
        assert sanitized["token"] == "[REDACTED]"

    def test_sanitize_empty_string(self):
        """Test sanitization of empty string values."""
        payload = {"username": "test", "password": "", "api_key": ""}

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        assert sanitized["username"] == "test"
        assert sanitized["password"] == "[REDACTED_0_CHARS]"
        assert sanitized["api_key"] == "[REDACTED_0_CHARS]"

    def test_sanitize_various_sensitive_keywords(self):
        """Test sanitization of various sensitive keyword patterns."""
        payload = {
            "passwd": "secret",
            "api_token": "token123",
            "access_token": "access",
            "refresh_token": "refresh",
            "client_secret": "client",
            "my_api_key": "secretkey",
            "csrf_token": "csrf",
        }

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        # All should be redacted with character count
        assert sanitized["passwd"] == "[REDACTED_6_CHARS]"
        assert sanitized["api_token"] == "[REDACTED_8_CHARS]"
        assert sanitized["access_token"] == "[REDACTED_6_CHARS]"
        assert sanitized["refresh_token"] == "[REDACTED_7_CHARS]"
        assert sanitized["client_secret"] == "[REDACTED_6_CHARS]"
        assert sanitized["my_api_key"] == "[REDACTED_9_CHARS]"
        assert sanitized["csrf_token"] == "[REDACTED_4_CHARS]"

    def test_sanitize_deeply_nested_structure(self):
        """Test sanitization of deeply nested data structures."""
        payload = {
            "level1": {
                "level2": {
                    "level3": {"password": "deep_secret", "data": "public"},
                    "token": "level2_token",
                },
                "api_key": "level1_key",
            }
        }

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        assert sanitized["level1"]["level2"]["level3"]["data"] == "public"
        assert (
            sanitized["level1"]["level2"]["level3"]["password"]
            == "[REDACTED_11_CHARS]"
        )
        assert sanitized["level1"]["level2"]["token"] == "[REDACTED_12_CHARS]"
        assert sanitized["level1"]["api_key"] == "[REDACTED_10_CHARS]"

    def test_sanitize_mixed_types_in_list(self):
        """Test sanitization of mixed types in list."""
        payload = {
            "data": [
                {"password": "secret1"},
                "plain_string",
                123,
                {"token": "secret2"},
            ]
        }

        sanitized = SensitiveDataSanitizer.sanitize_payload(payload)

        assert sanitized["data"][0]["password"] == "[REDACTED_7_CHARS]"
        assert sanitized["data"][1] == "plain_string"
        assert sanitized["data"][2] == 123
        assert sanitized["data"][3]["token"] == "[REDACTED_7_CHARS]"

    def test_sanitize_headers_case_insensitive(self):
        """Test header sanitization is case insensitive."""
        headers = {
            "authorization": "Bearer token",
            "COOKIE": "session=123",
            "X-Api-Key": "secret",
        }

        sanitized = SensitiveDataSanitizer.sanitize_headers(headers)

        assert sanitized["authorization"] == "[REDACTED]"
        assert sanitized["COOKIE"] == "[REDACTED]"
        assert sanitized["X-Api-Key"] == "[REDACTED]"

    def test_sanitize_url_with_query_params(self):
        """Test URL sanitization preserves query parameters."""
        url = "https://user:pass@api.example.com/data?key=value&foo=bar"

        sanitized = SensitiveDataSanitizer.sanitize_url(url)

        assert sanitized == "https://[REDACTED]@api.example.com/data?key=value&foo=bar"

    def test_sanitize_url_with_fragment(self):
        """Test URL sanitization preserves fragments."""
        url = "https://user:pass@example.com/page#section"

        sanitized = SensitiveDataSanitizer.sanitize_url(url)

        assert sanitized == "https://[REDACTED]@example.com/page#section"

    def test_sanitize_request_metadata_missing_fields(self):
        """Test sanitization handles missing fields gracefully."""
        metadata = {"url": "https://example.com", "method": "GET"}

        sanitized = SensitiveDataSanitizer.sanitize_request_metadata(metadata)

        assert sanitized["url"] == "https://example.com"
        assert sanitized["method"] == "GET"
        assert "headers" not in sanitized
        assert "payload" not in sanitized
