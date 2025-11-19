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
    }, clear=True)
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
    }, clear=True)
    def test_load_from_env_vars_barchart_missing_password(self):
        """Test loading Barchart credentials with missing password."""
        manager = CredentialManager()
        credentials = manager._load_from_env_vars('barchart')
        
        assert credentials is None
    
    @patch.dict(os.environ, {
        'VORTEX_BARCHART_PASSWORD': 'test_pass'
        # Missing username
    }, clear=True)
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
    }, clear=True)
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
    
    def test_get_barchart_credentials_from_user_config(self):
        """Test getting credentials from user config as fallback."""
        # Mock the class methods directly on the class to ensure they're applied
        with patch('vortex.core.security.credentials.CredentialManager._load_from_env_vars', return_value=None):
            with patch('vortex.core.security.credentials.CredentialManager._load_from_env_files', return_value=None):
                with patch('vortex.core.security.credentials.CredentialManager._load_from_user_config', return_value={
                    'username': 'user_config_user',
                    'password': 'user_config_pass'
                }):
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
    }, clear=True)
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


class TestCredentialEncryption:
    """Test credential encryption and decryption functionality."""

    def test_encrypt_credential_success(self):
        """Test successful credential encryption."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            plaintext = "my_secret_password"
            encrypted = encryptor.encrypt_credential(plaintext)

            assert encrypted.startswith("encrypted:")
            assert encrypted != plaintext
            assert len(encrypted) > len(plaintext)

    def test_decrypt_credential_success(self):
        """Test successful credential decryption."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            plaintext = "my_secret_password"
            encrypted = encryptor.encrypt_credential(plaintext)
            decrypted = encryptor.decrypt_credential(encrypted)

            assert decrypted == plaintext

    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            encrypted = encryptor.encrypt_credential("")
            assert encrypted == ""

    def test_encrypt_none(self):
        """Test encryption of None value."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            encrypted = encryptor.encrypt_credential(None)
            assert encrypted is None

    def test_encrypt_already_encrypted(self):
        """Test encrypting already encrypted credential."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            plaintext = "password"
            encrypted_once = encryptor.encrypt_credential(plaintext)
            encrypted_twice = encryptor.encrypt_credential(encrypted_once)

            # Should return same value if already encrypted
            assert encrypted_twice == encrypted_once

    def test_decrypt_plaintext_warning(self):
        """Test decrypting plaintext credential shows warning."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            plaintext = "not_encrypted_password"
            # Should return plaintext unchanged but log warning
            result = encryptor.decrypt_credential(plaintext)
            assert result == plaintext

    def test_is_encrypted_true(self):
        """Test is_encrypted returns True for encrypted credentials."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            encrypted = encryptor.encrypt_credential("password")
            assert encryptor.is_encrypted(encrypted) is True

    def test_is_encrypted_false(self):
        """Test is_encrypted returns False for plaintext."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            plaintext = "password"
            assert encryptor.is_encrypted(plaintext) is False

    def test_is_encrypted_empty_string(self):
        """Test is_encrypted with empty string."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            assert encryptor.is_encrypted("") is False
            assert encryptor.is_encrypted(None) is False

    def test_migrate_plaintext_to_encrypted(self):
        """Test migration from plaintext to encrypted."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            plaintext = "password123"
            encrypted, was_migrated = encryptor.migrate_plaintext_to_encrypted(plaintext)

            assert was_migrated is True
            assert encryptor.is_encrypted(encrypted) is True
            assert encryptor.decrypt_credential(encrypted) == plaintext

    def test_migrate_already_encrypted(self):
        """Test migration of already encrypted credential."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            plaintext = "password123"
            encrypted = encryptor.encrypt_credential(plaintext)

            result, was_migrated = encryptor.migrate_plaintext_to_encrypted(encrypted)

            assert was_migrated is False
            assert result == encrypted

    def test_key_file_created_automatically(self):
        """Test that encryption key file is created automatically."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "auto_key"
            assert not key_file.exists()

            encryptor = CredentialEncryption(key_file=key_file)
            encryptor.encrypt_credential("test")

            assert key_file.exists()

    def test_key_file_permissions_unix(self):
        """Test that key file has secure permissions on Unix systems."""
        from vortex.core.security.credentials import CredentialEncryption

        if os.name != 'posix':
            pytest.skip("Unix-only test")

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "secure_key"
            encryptor = CredentialEncryption(key_file=key_file)
            encryptor.encrypt_credential("test")

            # Check file permissions are 0o600 (owner read/write only)
            stat_info = key_file.stat()
            permissions = stat_info.st_mode & 0o777
            assert permissions == 0o600

    def test_key_reuse_across_instances(self):
        """Test that same key file works across multiple instances."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "shared_key"

            # First instance encrypts
            encryptor1 = CredentialEncryption(key_file=key_file)
            encrypted = encryptor1.encrypt_credential("shared_secret")

            # Second instance decrypts
            encryptor2 = CredentialEncryption(key_file=key_file)
            decrypted = encryptor2.decrypt_credential(encrypted)

            assert decrypted == "shared_secret"

    def test_decrypt_with_wrong_key_fails(self):
        """Test that decryption fails with wrong key."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file1 = Path(tmpdir) / "key1"
            key_file2 = Path(tmpdir) / "key2"

            # Encrypt with first key
            encryptor1 = CredentialEncryption(key_file=key_file1)
            encrypted = encryptor1.encrypt_credential("secret")

            # Try to decrypt with different key
            encryptor2 = CredentialEncryption(key_file=key_file2)
            with pytest.raises(ValueError, match="Failed to decrypt credential"):
                encryptor2.decrypt_credential(encrypted)

    def test_get_credential_encryptor_singleton(self):
        """Test that get_credential_encryptor returns singleton."""
        from vortex.core.security.credentials import get_credential_encryptor

        encryptor1 = get_credential_encryptor()
        encryptor2 = get_credential_encryptor()

        assert encryptor1 is encryptor2


class TestCredentialManagerWithEncryption:
    """Test CredentialManager with encryption support."""

    @patch.dict(os.environ, {
        'VORTEX_BARCHART_USERNAME': 'test_user',
        'VORTEX_BARCHART_PASSWORD': 'encrypted:dGVzdF9lbmNyeXB0ZWRfcGFzc3dvcmQ='
    }, clear=True)
    def test_get_credentials_decrypts_encrypted_password(self):
        """Test that get_barchart_credentials decrypts encrypted passwords."""
        from vortex.core.security.credentials import CredentialEncryption

        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_key"
            encryptor = CredentialEncryption(key_file=key_file)

            # Create encrypted password
            plaintext_password = "my_secret_pass"
            encrypted_password = encryptor.encrypt_credential(plaintext_password)

            # Set up environment with encrypted password
            with patch.dict(os.environ, {
                'VORTEX_BARCHART_USERNAME': 'test_user',
                'VORTEX_BARCHART_PASSWORD': encrypted_password
            }):
                manager = CredentialManager(encryptor=encryptor)
                credentials = manager.get_barchart_credentials()

                assert credentials is not None
                assert credentials['username'] == 'test_user'
                # Password should be decrypted
                assert credentials['password'] == plaintext_password
                assert credentials['password'] != encrypted_password

    @patch.dict(os.environ, {
        'VORTEX_BARCHART_USERNAME': 'test_user',
        'VORTEX_BARCHART_PASSWORD': 'plaintext_password'
    }, clear=True)
    def test_get_credentials_handles_plaintext_password(self):
        """Test that get_barchart_credentials handles plaintext passwords."""
        manager = CredentialManager()
        credentials = manager.get_barchart_credentials()

        assert credentials is not None
        assert credentials['username'] == 'test_user'
        # Plaintext password should be returned as-is
        assert credentials['password'] == 'plaintext_password'