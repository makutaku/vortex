"""
Test fixtures for secure credential handling.

This module provides test utilities for working with secure credentials
without hardcoding them in test files.
"""

import os
import tempfile
import json
from pathlib import Path
from typing import Optional, Dict
from unittest.mock import patch

from vortex.core.security.credentials import CredentialManager


class TestCredentialManager:
    """Test utility for managing credentials in tests."""
    
    def __init__(self):
        self.temp_files = []
    
    def create_test_env_file(self, credentials: Dict[str, str]) -> Path:
        """Create a temporary .env file for testing."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False)
        self.temp_files.append(temp_file.name)
        
        for key, value in credentials.items():
            temp_file.write(f"{key}={value}\n")
        temp_file.close()
        
        return Path(temp_file.name)
    
    def create_test_credentials_json(self, credentials_data: Dict) -> Path:
        """Create a temporary credentials.json file for testing."""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        self.temp_files.append(temp_file.name)
        
        json.dump(credentials_data, temp_file, indent=2)
        temp_file.close()
        
        return Path(temp_file.name)
    
    def get_barchart_credentials_from_env(self) -> Optional[Dict[str, str]]:
        """
        Get Barchart credentials from environment variables if available.
        Returns None if not found - tests should skip gracefully.
        """
        username = os.getenv('VORTEX_BARCHART_USERNAME')
        password = os.getenv('VORTEX_BARCHART_PASSWORD')
        
        if username and password:
            return {
                'username': username,
                'password': password
            }
        return None
    
    def mock_credential_manager_with_test_creds(self) -> CredentialManager:
        """
        Create a mock CredentialManager that returns test credentials.
        Use this for unit tests that don't need real credentials.
        """
        manager = CredentialManager()
        
        def mock_get_barchart_credentials():
            return {
                'username': 'test@example.com',
                'password': 'test_password_123'
            }
        
        manager.get_barchart_credentials = mock_get_barchart_credentials
        return manager
    
    def cleanup(self):
        """Clean up temporary files."""
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except FileNotFoundError:
                pass
        self.temp_files.clear()


def require_barchart_credentials():
    """
    Decorator to skip tests that require real Barchart credentials.
    Tests will only run if credentials are available via environment variables.
    """
    def decorator(test_func):
        def wrapper(*args, **kwargs):
            manager = TestCredentialManager()
            creds = manager.get_barchart_credentials_from_env()
            
            if not creds:
                import pytest
                pytest.skip("Barchart credentials not available (set VORTEX_BARCHART_USERNAME and VORTEX_BARCHART_PASSWORD)")
            
            return test_func(*args, **kwargs)
        return wrapper
    return decorator