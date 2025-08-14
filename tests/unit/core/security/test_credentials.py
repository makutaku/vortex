"""
Tests for secure credential management functionality.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
import pytest

from vortex.core.security.credentials import (
    CredentialManager, 
    get_secure_barchart_credentials
)


class TestCredentialManager:
    """Test credential manager functionality."""
    
    def test_init(self):
        """Test credential manager initialization."""
        manager = CredentialManager()
        assert len(manager.credential_sources) == 3
        assert manager._load_from_env_vars in manager.credential_sources
        assert manager._load_from_env_files in manager.credential_sources
        assert manager._load_from_user_config in manager.credential_sources


class TestEnvironmentVariableCredentials:
    """Test loading credentials from environment variables."""
    
    @patch.dict(os.environ, {
        'VORTEX_BARCHART_USERNAME': 'test_user',
        'VORTEX_BARCHART_PASSWORD': 'test_pass'
    })
    def test_load_from_env_vars_barchart_success(self):
        """Test successful loading of Barchart credentials from env vars."""
        manager = CredentialManager()
        credentials = manager._load_from_env_vars('barchart')
        
        assert credentials is not None
        assert credentials['username'] == 'test_user'
        assert credentials['password'] == 'test_pass'
    
    @patch.dict(os.environ, {
        'VORTEX_BARCHART_USERNAME': 'test_user'
        # Missing password
    })
    def test_load_from_env_vars_barchart_missing_password(self):
        """Test loading Barchart credentials with missing password."""
        manager = CredentialManager()
        credentials = manager._load_from_env_vars('barchart')
        
        assert credentials is None
    
    @patch.dict(os.environ, {
        'VORTEX_BARCHART_PASSWORD': 'test_pass'
        # Missing username
    })
    def test_load_from_env_vars_barchart_missing_username(self):
        """Test loading Barchart credentials with missing username."""
        manager = CredentialManager()
        credentials = manager._load_from_env_vars('barchart')
        
        assert credentials is None
    
    @patch.dict(os.environ, {}, clear=True)
    def test_load_from_env_vars_barchart_no_credentials(self):
        """Test loading Barchart credentials when no env vars present."""
        manager = CredentialManager()
        credentials = manager._load_from_env_vars('barchart')
        
        assert credentials is None
    
    def test_load_from_env_vars_unsupported_provider(self):
        """Test loading credentials for unsupported provider."""
        manager = CredentialManager()
        credentials = manager._load_from_env_vars('unsupported_provider')
        
        assert credentials is None


class TestEnvironmentFileCredentials:
    """Test loading credentials from environment files."""
    
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="""
VORTEX_BARCHART_USERNAME=file_user
VORTEX_BARCHART_PASSWORD=file_pass
# This is a comment
OTHER_VAR=other_value
""")
    def test_load_from_env_files_success(self, mock_file, mock_exists, mock_cwd):
        """Test successful loading from .env file."""
        mock_cwd.return_value = Path('/test/dir')
        mock_exists.return_value = True
        
        manager = CredentialManager()
        credentials = manager._load_from_env_files('barchart')
        
        assert credentials is not None
        assert credentials['username'] == 'file_user'
        assert credentials['password'] == 'file_pass'
    
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="""
VORTEX_BARCHART_USERNAME="quoted_user"
VORTEX_BARCHART_PASSWORD='single_quoted_pass'
""")
    def test_load_from_env_files_quoted_values(self, mock_file, mock_exists, mock_cwd):
        """Test loading from .env file with quoted values."""
        mock_cwd.return_value = Path('/test/dir')
        mock_exists.return_value = True
        
        manager = CredentialManager()
        credentials = manager._load_from_env_files('barchart')
        
        assert credentials is not None
        assert credentials['username'] == 'quoted_user'
        assert credentials['password'] == 'single_quoted_pass'
    
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="""
VORTEX_BARCHART_USERNAME=incomplete_user
# Missing password
""")
    def test_load_from_env_files_incomplete_credentials(self, mock_file, mock_exists, mock_cwd):
        """Test loading incomplete credentials from .env file."""
        mock_cwd.return_value = Path('/test/dir')
        mock_exists.return_value = True
        
        manager = CredentialManager()
        credentials = manager._load_from_env_files('barchart')
        
        assert credentials is None
    
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.exists')
    def test_load_from_env_files_no_files(self, mock_exists, mock_cwd):
        """Test loading when no .env files exist."""
        mock_cwd.return_value = Path('/test/dir')
        mock_exists.return_value = False
        
        manager = CredentialManager()
        credentials = manager._load_from_env_files('barchart')
        
        assert credentials is None
    
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', side_effect=IOError("File read error"))
    def test_load_from_env_files_file_error(self, mock_file, mock_exists, mock_cwd):
        """Test handling of file read errors."""
        mock_cwd.return_value = Path('/test/dir')
        mock_exists.return_value = True
        
        manager = CredentialManager()
        credentials = manager._load_from_env_files('barchart')
        
        assert credentials is None


class TestUserConfigCredentials:
    """Test loading credentials from user config directory."""
    
    @patch('pathlib.Path.home')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=json.dumps({
        "providers": {
            "barchart": {
                "username": "config_user",
                "password": "config_pass"
            }
        }
    }))
    def test_load_from_user_config_success(self, mock_file, mock_exists, mock_home):
        """Test successful loading from user config."""
        mock_home.return_value = Path('/home/test')
        mock_exists.return_value = True
        
        manager = CredentialManager()
        credentials = manager._load_from_user_config('barchart')
        
        assert credentials is not None
        assert credentials['username'] == 'config_user'
        assert credentials['password'] == 'config_pass'
    
    @patch('pathlib.Path.home')
    @patch('pathlib.Path.exists')
    def test_load_from_user_config_no_file(self, mock_exists, mock_home):
        """Test loading when config file doesn't exist."""
        mock_home.return_value = Path('/home/test')
        mock_exists.return_value = False
        
        manager = CredentialManager()
        credentials = manager._load_from_user_config('barchart')
        
        assert credentials is None
    
    @patch('pathlib.Path.home')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data=json.dumps({
        "providers": {
            "barchart": {
                "username": "incomplete_user"
                # Missing password
            }
        }
    }))
    def test_load_from_user_config_incomplete_credentials(self, mock_file, mock_exists, mock_home):
        """Test loading incomplete credentials from user config."""
        mock_home.return_value = Path('/home/test')
        mock_exists.return_value = True
        
        manager = CredentialManager()
        credentials = manager._load_from_user_config('barchart')
        
        assert credentials is None
    
    @patch('pathlib.Path.home')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    def test_load_from_user_config_invalid_json(self, mock_file, mock_exists, mock_home):
        """Test handling of invalid JSON in config file."""
        mock_home.return_value = Path('/home/test')
        mock_exists.return_value = True
        
        manager = CredentialManager()
        credentials = manager._load_from_user_config('barchart')
        
        assert credentials is None
    
    @patch('pathlib.Path.home')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', side_effect=IOError("File read error"))
    def test_load_from_user_config_file_error(self, mock_file, mock_exists, mock_home):
        """Test handling of file read errors."""
        mock_home.return_value = Path('/home/test')
        mock_exists.return_value = True
        
        manager = CredentialManager()
        credentials = manager._load_from_user_config('barchart')
        
        assert credentials is None


class TestGetBarchartCredentials:
    """Test the main get_barchart_credentials method."""
    
    @patch.dict(os.environ, {
        'VORTEX_BARCHART_USERNAME': 'env_user',
        'VORTEX_BARCHART_PASSWORD': 'env_pass'
    })
    def test_get_barchart_credentials_from_env(self):
        """Test getting Barchart credentials from environment variables."""
        manager = CredentialManager()
        credentials = manager.get_barchart_credentials()
        
        assert credentials is not None
        assert credentials['username'] == 'env_user'
        assert credentials['password'] == 'env_pass'
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="""
VORTEX_BARCHART_USERNAME=file_user
VORTEX_BARCHART_PASSWORD=file_pass
""")
    def test_get_barchart_credentials_from_file(self, mock_file, mock_exists, mock_cwd):
        """Test getting Barchart credentials from file when env vars not available."""
        mock_cwd.return_value = Path('/test/dir')
        mock_exists.return_value = True
        
        manager = CredentialManager()
        credentials = manager.get_barchart_credentials()
        
        assert credentials is not None
        assert credentials['username'] == 'file_user'
        assert credentials['password'] == 'file_pass'
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.exists', side_effect=lambda: False)  # No .env files
    @patch('pathlib.Path.home')
    def test_get_barchart_credentials_from_user_config(self, mock_home, mock_env_exists, mock_cwd):
        """Test getting credentials from user config as fallback."""
        mock_cwd.return_value = Path('/test/dir')
        mock_home.return_value = Path('/home/test')
        
        # Mock user config file exists and content
        with patch('pathlib.Path.exists') as mock_user_exists:
            mock_user_exists.side_effect = lambda self: str(self).endswith('credentials.json')
            
            with patch('builtins.open', new_callable=mock_open, read_data=json.dumps({
                "providers": {
                    "barchart": {
                        "username": "user_config_user",
                        "password": "user_config_pass"
                    }
                }
            })):
                manager = CredentialManager()
                credentials = manager.get_barchart_credentials()
                
                assert credentials is not None
                assert credentials['username'] == 'user_config_user'
                assert credentials['password'] == 'user_config_pass'
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('pathlib.Path.exists', return_value=False)
    def test_get_barchart_credentials_none_found(self, mock_exists):
        """Test when no credentials are found from any source."""
        manager = CredentialManager()
        credentials = manager.get_barchart_credentials()
        
        assert credentials is None


class TestParseEnvFile:
    """Test environment file parsing functionality."""
    
    def test_parse_env_file_success(self):
        """Test successful parsing of environment file."""
        manager = CredentialManager()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            f.write("""
# Barchart credentials
VORTEX_BARCHART_USERNAME=parse_user
VORTEX_BARCHART_PASSWORD=parse_pass

# Other variables
OTHER_VAR=other_value
""")
            f.flush()
            
            try:
                credentials = manager._parse_env_file(Path(f.name), 'barchart')
                assert credentials is not None
                assert credentials['username'] == 'parse_user'
                assert credentials['password'] == 'parse_pass'
            finally:
                os.unlink(f.name)
    
    def test_parse_env_file_empty_lines_and_comments(self):
        """Test parsing file with empty lines and comments."""
        manager = CredentialManager()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            f.write("""
# This is a comment
VORTEX_BARCHART_USERNAME=comment_user

# Another comment
VORTEX_BARCHART_PASSWORD=comment_pass

# End comment
""")
            f.flush()
            
            try:
                credentials = manager._parse_env_file(Path(f.name), 'barchart')
                assert credentials is not None
                assert credentials['username'] == 'comment_user'
                assert credentials['password'] == 'comment_pass'
            finally:
                os.unlink(f.name)
    
    def test_parse_env_file_no_equals(self):
        """Test parsing file with malformed lines (no equals)."""
        manager = CredentialManager()
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as f:
            f.write("""
MALFORMED_LINE_WITHOUT_EQUALS
VORTEX_BARCHART_USERNAME=valid_user
VORTEX_BARCHART_PASSWORD=valid_pass
""")
            f.flush()
            
            try:
                credentials = manager._parse_env_file(Path(f.name), 'barchart')
                assert credentials is not None
                assert credentials['username'] == 'valid_user'
                assert credentials['password'] == 'valid_pass'
            finally:
                os.unlink(f.name)


class TestCreateExampleFiles:
    """Test creation of example credential files."""
    
    @patch('pathlib.Path.cwd')
    @patch('pathlib.Path.home')
    @patch('pathlib.Path.mkdir')
    @patch('builtins.open', new_callable=mock_open)
    def test_create_example_files(self, mock_file, mock_mkdir, mock_home, mock_cwd):
        """Test creation of example credential files."""
        mock_cwd.return_value = Path('/project/dir')
        mock_home.return_value = Path('/home/user')
        
        manager = CredentialManager()
        manager.create_example_files()
        
        # Verify mkdir was called for user config directory
        mock_mkdir.assert_called_once_with(exist_ok=True)
        
        # Verify files were written
        assert mock_file.call_count == 2
        
        # Check that .env.example was created
        env_example_calls = [call for call in mock_file.call_args_list 
                           if '.env.example' in str(call[0][0])]
        assert len(env_example_calls) == 1
        
        # Check that credentials.json.example was created
        cred_example_calls = [call for call in mock_file.call_args_list 
                            if 'credentials.json.example' in str(call[0][0])]
        assert len(cred_example_calls) == 1


class TestConvenienceFunction:
    """Test convenience function for getting credentials."""
    
    @patch.dict(os.environ, {
        'VORTEX_BARCHART_USERNAME': 'convenience_user',
        'VORTEX_BARCHART_PASSWORD': 'convenience_pass'
    })
    def test_get_secure_barchart_credentials(self):
        """Test convenience function for getting Barchart credentials."""
        credentials = get_secure_barchart_credentials()
        
        assert credentials is not None
        assert credentials['username'] == 'convenience_user'
        assert credentials['password'] == 'convenience_pass'
    
    @patch.dict(os.environ, {}, clear=True)
    @patch('pathlib.Path.exists', return_value=False)
    def test_get_secure_barchart_credentials_none(self, mock_exists):
        """Test convenience function when no credentials found."""
        credentials = get_secure_barchart_credentials()
        
        assert credentials is None


class TestErrorHandling:
    """Test error handling in credential loading."""
    
    def test_load_from_env_vars_exception_handling(self):
        """Test exception handling in env var loading."""
        manager = CredentialManager()
        
        # This should not raise an exception even if provider is None
        credentials = manager._load_from_env_vars(None)
        assert credentials is None
    
    @patch('pathlib.Path.cwd', side_effect=OSError("Directory access error"))
    def test_load_from_env_files_exception_handling(self, mock_cwd):
        """Test exception handling in env file loading."""
        manager = CredentialManager()
        
        # Should handle OS errors gracefully
        credentials = manager._load_from_env_files('barchart')
        assert credentials is None
    
    @patch('pathlib.Path.home', side_effect=OSError("Home directory error"))
    def test_load_from_user_config_exception_handling(self, mock_home):
        """Test exception handling in user config loading."""
        manager = CredentialManager()
        
        # Should handle OS errors gracefully
        credentials = manager._load_from_user_config('barchart')
        assert credentials is None
    
    def test_get_barchart_credentials_source_exception_handling(self):
        """Test handling of exceptions from individual credential sources."""
        manager = CredentialManager()
        
        # Mock a source that raises an exception
        def failing_source(provider):
            raise ValueError("Credential source error")
        
        # Replace one source with failing one
        manager.credential_sources = [
            failing_source,
            manager._load_from_env_vars,
            manager._load_from_user_config
        ]
        
        # Should continue to next source despite exception
        with patch.dict(os.environ, {
            'VORTEX_BARCHART_USERNAME': 'fallback_user',
            'VORTEX_BARCHART_PASSWORD': 'fallback_pass'
        }):
            credentials = manager.get_barchart_credentials()
            assert credentials is not None
            assert credentials['username'] == 'fallback_user'