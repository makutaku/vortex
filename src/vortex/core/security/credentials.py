"""
Secure credential management for Vortex.

This module provides secure loading of credentials from environment variables
and credential files, with encryption support for credentials at rest.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class CredentialEncryption:
    """Encrypt and decrypt credentials using Fernet symmetric encryption."""

    def __init__(self, key_file: Optional[Path] = None):
        """Initialize credential encryption.

        Args:
            key_file: Path to encryption key file (default: ~/.vortex/encryption.key)
        """
        self.key_file = key_file or Path.home() / ".vortex" / "encryption.key"
        self._fernet = None

    def _ensure_key_exists(self) -> bytes:
        """Ensure encryption key exists, creating it if necessary.

        Returns:
            Encryption key bytes

        Raises:
            RuntimeError: If key file has insecure permissions
        """
        # Create key directory if it doesn't exist
        self.key_file.parent.mkdir(parents=True, exist_ok=True)

        if self.key_file.exists():
            # Validate key file permissions (should be readable only by owner)
            self._validate_key_permissions()

            # Read existing key
            with open(self.key_file, "rb") as f:
                return f.read()
        else:
            # Generate new key
            from cryptography.fernet import Fernet

            key = Fernet.generate_key()

            # Write key with secure permissions (0o600 = owner read/write only)
            self.key_file.touch(mode=0o600)
            with open(self.key_file, "wb") as f:
                f.write(key)

            logger.info(
                f"Generated new encryption key at {self.key_file}",
                extra={"key_file": str(self.key_file)},
            )

            return key

    def _validate_key_permissions(self) -> None:
        """Validate that key file has secure permissions.

        Raises:
            RuntimeError: If key file has insecure permissions
        """
        # Only validate on Unix-like systems
        if os.name == "posix":
            stat_info = self.key_file.stat()
            # Check if file is readable by group or others (insecure)
            if stat_info.st_mode & 0o077:
                raise RuntimeError(
                    f"Encryption key file {self.key_file} has insecure permissions. "
                    f"Fix with: chmod 600 {self.key_file}"
                )

    def _get_fernet(self):
        """Get or create Fernet cipher instance."""
        if self._fernet is None:
            from cryptography.fernet import Fernet

            key = self._ensure_key_exists()
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt_credential(self, plaintext: str) -> str:
        """Encrypt a credential (password, API key, etc.).

        Args:
            plaintext: The plaintext credential to encrypt

        Returns:
            Base64-encoded encrypted credential with "encrypted:" prefix
        """
        if not plaintext:
            return plaintext

        # Check if already encrypted
        if plaintext.startswith("encrypted:"):
            logger.debug("Credential already encrypted, skipping")
            return plaintext

        # Encrypt the credential
        fernet = self._get_fernet()
        encrypted_bytes = fernet.encrypt(plaintext.encode("utf-8"))

        # Return as base64 string with prefix for identification
        encrypted_str = base64.b64encode(encrypted_bytes).decode("utf-8")
        return f"encrypted:{encrypted_str}"

    def decrypt_credential(self, encrypted: str) -> str:
        """Decrypt an encrypted credential.

        Args:
            encrypted: The encrypted credential (with or without "encrypted:" prefix)

        Returns:
            Decrypted plaintext credential

        Raises:
            ValueError: If decryption fails (invalid key or corrupted data)
        """
        if not encrypted:
            return encrypted

        # Handle plaintext credentials (backward compatibility during migration)
        if not encrypted.startswith("encrypted:"):
            logger.warning(
                "Credential is not encrypted - storing plaintext is insecure. "
                "Use encrypt_credential() to secure it."
            )
            return encrypted

        # Remove prefix and decrypt
        encrypted_b64 = encrypted.replace("encrypted:", "", 1)

        try:
            encrypted_bytes = base64.b64decode(encrypted_b64)
            fernet = self._get_fernet()
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")

        except Exception as e:
            raise ValueError(
                f"Failed to decrypt credential. The encryption key may have changed "
                f"or the credential data is corrupted: {e}"
            ) from e

    def is_encrypted(self, credential: str) -> bool:
        """Check if a credential is encrypted.

        Args:
            credential: The credential to check

        Returns:
            True if encrypted, False if plaintext
        """
        return bool(credential and credential.startswith("encrypted:"))

    def migrate_plaintext_to_encrypted(self, plaintext: str) -> Tuple[str, bool]:
        """Migrate a plaintext credential to encrypted format.

        Args:
            plaintext: The credential (may be plaintext or already encrypted)

        Returns:
            Tuple of (credential_value, was_migrated)
            - credential_value: Encrypted credential
            - was_migrated: True if migration occurred, False if already encrypted
        """
        if self.is_encrypted(plaintext):
            return plaintext, False

        encrypted = self.encrypt_credential(plaintext)
        logger.info("Migrated plaintext credential to encrypted format")
        return encrypted, True


# Global credential encryptor instance
_credential_encryptor: Optional[CredentialEncryption] = None


def get_credential_encryptor(key_file: Optional[Path] = None) -> CredentialEncryption:
    """Get or create global credential encryptor instance.

    Args:
        key_file: Optional custom key file path

    Returns:
        CredentialEncryption instance
    """
    global _credential_encryptor

    if _credential_encryptor is None:
        _credential_encryptor = CredentialEncryption(key_file)

    return _credential_encryptor


class CredentialManager:
    """
    Secure credential manager that loads credentials from multiple sources
    in order of precedence:
    1. Environment variables
    2. Credential files (.env.local, .env)
    3. User credential directory (~/.vortex/credentials.json)

    All credential files are excluded from version control.
    Supports encrypted credentials with automatic decryption.
    """

    def __init__(self, encryptor: Optional[CredentialEncryption] = None):
        """Initialize credential manager.

        Args:
            encryptor: Optional CredentialEncryption instance (default: global instance)
        """
        self.credential_sources = [
            self._load_from_env_vars,
            self._load_from_env_files,
            self._load_from_user_config,
        ]
        self.encryptor = encryptor or get_credential_encryptor()

    def get_barchart_credentials(self) -> Optional[Dict[str, str]]:
        """
        Get Barchart credentials securely from available sources.
        Automatically decrypts encrypted passwords.

        Returns:
            Dict with 'username' and 'password' keys (decrypted), or None if not found
        """
        for source_loader in self.credential_sources:
            try:
                credentials = source_loader("barchart")
                if (
                    credentials
                    and "username" in credentials
                    and "password" in credentials
                ):
                    source_name = getattr(source_loader, "__name__", str(source_loader))
                    logger.debug(f"Barchart credentials loaded from {source_name}")

                    # Decrypt password if encrypted
                    password = credentials["password"]
                    if self.encryptor.is_encrypted(password):
                        try:
                            password = self.encryptor.decrypt_credential(password)
                            logger.debug("Decrypted encrypted password")
                        except ValueError as e:
                            logger.error(f"Failed to decrypt password: {e}")
                            continue  # Try next source

                    return {
                        "username": credentials["username"],
                        "password": password,  # ✅ DECRYPTED
                    }
            except (
                KeyError,
                TypeError,
                ValueError,
                FileNotFoundError,
                PermissionError,
                OSError,
            ) as e:
                source_name = getattr(source_loader, "__name__", str(source_loader))
                logger.debug(f"Failed to load credentials from {source_name}: {e}")
                continue

        logger.warning("No Barchart credentials found in any secure source")
        return None

    def _load_from_env_vars(self, provider: str) -> Optional[Dict[str, Any]]:
        """Load credentials from environment variables."""
        if provider and provider.lower() == "barchart":
            username = os.getenv("VORTEX_BARCHART_USERNAME")
            password = os.getenv("VORTEX_BARCHART_PASSWORD")

            if username and password:
                return {"username": username, "password": password}

        return None

    def _load_from_env_files(self, provider: str) -> Optional[Dict[str, Any]]:
        """Load credentials from .env files (excluded from git)."""
        if not provider:
            return None

        try:
            env_files = [".env.local", ".env"]

            for env_file in env_files:
                env_path = Path.cwd() / env_file
                if env_path.exists():
                    try:
                        credentials = self._parse_env_file(env_path, provider)
                        if credentials:
                            return credentials
                    except (
                        FileNotFoundError,
                        PermissionError,
                        OSError,
                        UnicodeDecodeError,
                    ) as e:
                        logger.debug(f"Failed to parse {env_file}: {e}")
                        continue
        except (OSError, PermissionError) as e:
            logger.debug(f"Failed to access .env files: {e}")

        return None

    def _load_from_user_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """Load credentials from user configuration directory."""
        if not provider:
            return None

        try:
            user_config_dir = Path.home() / ".vortex"
            credentials_file = user_config_dir / "credentials.json"

            if not credentials_file.exists():
                return None

            with open(credentials_file, "r") as f:
                config = json.load(f)

            provider_config = config.get("providers", {}).get(provider.lower(), {})
            if "username" in provider_config and "password" in provider_config:
                return {
                    "username": provider_config["username"],
                    "password": provider_config["password"],
                }
        except (
            FileNotFoundError,
            PermissionError,
            OSError,
            KeyError,
            TypeError,
            ValueError,
        ) as e:
            logger.debug(f"Failed to load user credentials: {e}")

        return None

    def _parse_env_file(
        self, env_path: Path, provider: str
    ) -> Optional[Dict[str, Any]]:
        """Parse environment file for provider credentials."""
        if not provider:
            return None

        credentials = {}

        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip("\"'")  # Remove quotes

                    if provider.lower() == "barchart":
                        if key == "VORTEX_BARCHART_USERNAME":
                            credentials["username"] = value
                        elif key == "VORTEX_BARCHART_PASSWORD":
                            credentials["password"] = value

        if "username" in credentials and "password" in credentials:
            return credentials

        return None

    def create_example_files(self):
        """Create example credential files (for documentation purposes)."""
        # Create .env.example (safe to commit)
        env_example_content = """# Vortex Environment Variables Example
# Copy this file to .env.local and fill in your actual credentials
# .env.local is excluded from git for security

# Barchart.com credentials
VORTEX_BARCHART_USERNAME=<YOUR_BARCHART_USERNAME_HERE>
VORTEX_BARCHART_PASSWORD=<YOUR_BARCHART_PASSWORD_HERE>

# Other provider credentials can be added here
# VORTEX_IBKR_HOST=<YOUR_IBKR_HOST_HERE>
# VORTEX_IBKR_PORT=<YOUR_IBKR_PORT_HERE>
"""

        env_example_path = Path.cwd() / ".env.example"
        with open(env_example_path, "w") as f:
            f.write(env_example_content)

        # Create user config directory example
        user_config_dir = Path.home() / ".vortex"
        user_config_dir.mkdir(exist_ok=True)

        credentials_example = {
            "providers": {
                "barchart": {
                    "username": "<YOUR_BARCHART_USERNAME_HERE>",
                    "password": "<YOUR_BARCHART_PASSWORD_HERE>",
                },
                "ibkr": {
                    "host": "<YOUR_IBKR_HOST_HERE>",
                    "port": "<YOUR_IBKR_PORT_HERE>",
                    "client_id": "<YOUR_CLIENT_ID_HERE>",
                },
            }
        }

        credentials_example_path = user_config_dir / "credentials.json.example"
        with open(credentials_example_path, "w") as f:
            json.dump(credentials_example, f, indent=2)

        logger.info(
            f"Created credential examples at {env_example_path} and {credentials_example_path}"
        )


def get_secure_barchart_credentials() -> Optional[Dict[str, str]]:
    """
    Convenience function to get Barchart credentials securely.

    Returns:
        Dict with 'username' and 'password' keys, or None if not found
    """
    manager = CredentialManager()
    return manager.get_barchart_credentials()
