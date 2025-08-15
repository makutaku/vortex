"""
Secure credential management for Vortex.

This module provides secure loading of credentials from environment variables
and credential files, following security best practices.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Secure credential manager that loads credentials from multiple sources
    in order of precedence:
    1. Environment variables
    2. Credential files (.env.local, .env) 
    3. User credential directory (~/.vortex/credentials.json)
    
    All credential files are excluded from version control.
    """
    
    def __init__(self):
        self.credential_sources = [
            self._load_from_env_vars,
            self._load_from_env_files,
            self._load_from_user_config
        ]
    
    def get_barchart_credentials(self) -> Optional[Dict[str, str]]:
        """
        Get Barchart credentials securely from available sources.
        
        Returns:
            Dict with 'username' and 'password' keys, or None if not found
        """
        for source_loader in self.credential_sources:
            try:
                credentials = source_loader('barchart')
                if credentials and 'username' in credentials and 'password' in credentials:
                    source_name = getattr(source_loader, '__name__', str(source_loader))
                    logger.debug(f"Barchart credentials loaded from {source_name}")
                    return {
                        'username': credentials['username'],
                        'password': credentials['password']
                    }
            except Exception as e:
                source_name = getattr(source_loader, '__name__', str(source_loader))
                logger.debug(f"Failed to load credentials from {source_name}: {e}")
                continue
        
        logger.warning("No Barchart credentials found in any secure source")
        return None
    
    def _load_from_env_vars(self, provider: str) -> Optional[Dict[str, Any]]:
        """Load credentials from environment variables."""
        if provider and provider.lower() == 'barchart':
            username = os.getenv('VORTEX_BARCHART_USERNAME')
            password = os.getenv('VORTEX_BARCHART_PASSWORD')
            
            if username and password:
                return {
                    'username': username,
                    'password': password
                }
        
        return None
    
    def _load_from_env_files(self, provider: str) -> Optional[Dict[str, Any]]:
        """Load credentials from .env files (excluded from git)."""
        if not provider:
            return None
            
        try:
            env_files = ['.env.local', '.env']
            
            for env_file in env_files:
                env_path = Path.cwd() / env_file
                if env_path.exists():
                    try:
                        credentials = self._parse_env_file(env_path, provider)
                        if credentials:
                            return credentials
                    except Exception as e:
                        logger.debug(f"Failed to parse {env_file}: {e}")
                        continue
        except Exception as e:
            logger.debug(f"Failed to access .env files: {e}")
        
        return None
    
    def _load_from_user_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Load credentials from user configuration directory."""
        if not provider:
            return None
            
        try:
            user_config_dir = Path.home() / '.vortex'
            credentials_file = user_config_dir / 'credentials.json'
            
            if not credentials_file.exists():
                return None
            
            with open(credentials_file, 'r') as f:
                config = json.load(f)
            
            provider_config = config.get('providers', {}).get(provider.lower(), {})
            if 'username' in provider_config and 'password' in provider_config:
                return {
                    'username': provider_config['username'],
                    'password': provider_config['password']
                }
        except Exception as e:
            logger.debug(f"Failed to load user credentials: {e}")
        
        return None
    
    def _parse_env_file(self, env_path: Path, provider: str) -> Optional[Dict[str, Any]]:
        """Parse environment file for provider credentials."""
        if not provider:
            return None
            
        credentials = {}
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')  # Remove quotes
                    
                    if provider.lower() == 'barchart':
                        if key == 'VORTEX_BARCHART_USERNAME':
                            credentials['username'] = value
                        elif key == 'VORTEX_BARCHART_PASSWORD':
                            credentials['password'] = value
        
        if 'username' in credentials and 'password' in credentials:
            return credentials
        
        return None
    
    def create_example_files(self):
        """Create example credential files (for documentation purposes)."""
        # Create .env.example (safe to commit)
        env_example_content = """# Vortex Environment Variables Example
# Copy this file to .env.local and fill in your actual credentials
# .env.local is excluded from git for security

# Barchart.com credentials
VORTEX_BARCHART_USERNAME=your_barchart_username
VORTEX_BARCHART_PASSWORD=your_barchart_password

# Other provider credentials can be added here
# VORTEX_IBKR_HOST=localhost
# VORTEX_IBKR_PORT=7497
"""
        
        env_example_path = Path.cwd() / '.env.example'
        with open(env_example_path, 'w') as f:
            f.write(env_example_content)
        
        # Create user config directory example
        user_config_dir = Path.home() / '.vortex'
        user_config_dir.mkdir(exist_ok=True)
        
        credentials_example = {
            "providers": {
                "barchart": {
                    "username": "your_barchart_username",
                    "password": "your_barchart_password"
                },
                "ibkr": {
                    "host": "localhost",
                    "port": 7497,
                    "client_id": 1
                }
            }
        }
        
        credentials_example_path = user_config_dir / 'credentials.json.example'
        with open(credentials_example_path, 'w') as f:
            json.dump(credentials_example, f, indent=2)
        
        logger.info(f"Created credential examples at {env_example_path} and {credentials_example_path}")


def get_secure_barchart_credentials() -> Optional[Dict[str, str]]:
    """
    Convenience function to get Barchart credentials securely.
    
    Returns:
        Dict with 'username' and 'password' keys, or None if not found
    """
    manager = CredentialManager()
    return manager.get_barchart_credentials()