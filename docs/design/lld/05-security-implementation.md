# Security Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Security Design](../hld/06-security-design.md)

## 1. Credential Management Implementation

### 1.1 Credential Manager Core
```python
from cryptography.fernet import Fernet
import keyring
import os
from typing import Dict, Optional
import logging
import json
from pathlib import Path

class CredentialManager:
    """Secure credential management with multiple backends"""
    
    def __init__(self, default_backend: str = "environment"):
        self.default_backend = default_backend
        self.backends = {
            "environment": EnvironmentCredentialBackend(),
            "keyring": KeyringCredentialBackend(), 
            "vault": VaultCredentialBackend(),
            "encrypted_file": EncryptedFileBackend()
        }
        self.credential_cache = {}
        self.encryption_key = self._get_or_create_encryption_key()
        self.logger = logging.getLogger(__name__)
        
    def get_credentials(self, provider: str) -> Dict[str, str]:
        """Get credentials for specified provider"""
        cache_key = f"creds_{provider}"
        
        # Check cache first
        if cache_key in self.credential_cache:
            return self.credential_cache[cache_key]
        
        # Try each backend in order of preference
        for backend_name in [self.default_backend] + list(self.backends.keys()):
            if backend_name == self.default_backend:
                continue
                
            backend = self.backends[backend_name]
            try:
                credentials = backend.get_credentials(provider)
                if credentials:
                    # Cache the credentials (encrypted)
                    self.credential_cache[cache_key] = credentials
                    self.logger.info(f"Retrieved credentials for {provider} from {backend_name}")
                    return credentials
            except Exception as e:
                self.logger.warning(f"Failed to get credentials from {backend_name}: {e}")
                continue
        
        raise CredentialError(f"No credentials found for provider: {provider}")
    
    def store_credentials(self, provider: str, credentials: Dict[str, str], 
                         backend: str = None):
        """Store credentials using specified backend"""
        backend_name = backend or self.default_backend
        backend_impl = self.backends[backend_name]
        
        try:
            backend_impl.store_credentials(provider, credentials)
            # Update cache
            cache_key = f"creds_{provider}"
            self.credential_cache[cache_key] = credentials
            self.logger.info(f"Stored credentials for {provider} in {backend_name}")
        except Exception as e:
            self.logger.error(f"Failed to store credentials: {e}")
            raise
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for credential caching"""
        key_file = Path.home() / ".bcutils" / "encryption.key"
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            # Create new key
            key = Fernet.generate_key()
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(key)
            key_file.chmod(0o600)  # Owner read/write only
            return key
```

### 1.2 Environment Credential Backend
```python
class EnvironmentCredentialBackend:
    """Retrieve credentials from environment variables"""
    
    def get_credentials(self, provider: str) -> Optional[Dict[str, str]]:
        """Get credentials from environment variables"""
        prefix = f"BCU_{provider.upper()}_"
        credentials = {}
        
        # Common credential patterns
        patterns = {
            'username': [f'{prefix}USERNAME', f'{prefix}USER'],
            'password': [f'{prefix}PASSWORD', f'{prefix}PASS'],
            'api_key': [f'{prefix}API_KEY', f'{prefix}KEY'],
            'host': [f'{prefix}HOST'],
            'port': [f'{prefix}PORT']
        }
        
        for cred_type, env_vars in patterns.items():
            for env_var in env_vars:
                value = os.getenv(env_var)
                if value:
                    credentials[cred_type] = value
                    break
        
        return credentials if credentials else None
    
    def store_credentials(self, provider: str, credentials: Dict[str, str]):
        """Environment backend is read-only"""
        raise NotImplementedError("Environment backend is read-only")
```

### 1.3 Encrypted File Backend
```python
class EncryptedFileBackend:
    """Store credentials in encrypted local file"""
    
    def __init__(self, credentials_file: str = None):
        self.credentials_file = Path(credentials_file or 
                                   Path.home() / ".bcutils" / "credentials.enc")
        self.encryption_key = self._get_encryption_key()
        self.fernet = Fernet(self.encryption_key)
    
    def get_credentials(self, provider: str) -> Optional[Dict[str, str]]:
        """Load and decrypt credentials from file"""
        if not self.credentials_file.exists():
            return None
            
        try:
            # Read and decrypt file
            encrypted_data = self.credentials_file.read_bytes()
            decrypted_data = self.fernet.decrypt(encrypted_data)
            credentials_store = json.loads(decrypted_data.decode())
            
            return credentials_store.get(provider)
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to read credentials: {e}")
            return None
    
    def store_credentials(self, provider: str, credentials: Dict[str, str]):
        """Encrypt and store credentials to file"""
        # Load existing credentials
        all_credentials = {}
        if self.credentials_file.exists():
            try:
                encrypted_data = self.credentials_file.read_bytes()
                decrypted_data = self.fernet.decrypt(encrypted_data)
                all_credentials = json.loads(decrypted_data.decode())
            except Exception:
                pass  # Start fresh if file is corrupted
        
        # Update with new credentials
        all_credentials[provider] = credentials
        
        # Encrypt and save
        data_to_encrypt = json.dumps(all_credentials).encode()
        encrypted_data = self.fernet.encrypt(data_to_encrypt)
        
        # Ensure directory exists
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write with secure permissions
        self.credentials_file.write_bytes(encrypted_data)
        self.credentials_file.chmod(0o600)
    
    def _get_encryption_key(self) -> bytes:
        """Get encryption key from secure location"""
        key_file = Path.home() / ".bcutils" / "master.key"
        
        if key_file.exists():
            return key_file.read_bytes()
        else:
            # Generate new key
            key = Fernet.generate_key()
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(key)
            key_file.chmod(0o600)
            return key
```

## 2. Input Validation Implementation

### 2.1 Configuration Validator
```python
import re
from typing import Any, List, Dict
from pathlib import Path

class ConfigurationValidator:
    """Validates configuration inputs for security"""
    
    def __init__(self):
        self.dangerous_patterns = [
            r'\$\(.*\)',  # Command substitution
            r'`.*`',      # Backticks
            r';\s*\w+',   # Command chaining
            r'\|\s*\w+',  # Pipes
            r'>\s*\w+',   # Redirects
            r'<\s*\w+',   # Input redirects
        ]
        
    def validate_configuration(self, config: Dict[str, Any]) -> List[str]:
        """Validate entire configuration object"""
        errors = []
        
        # Validate provider settings
        if 'provider' in config:
            errors.extend(self._validate_provider_config(config['provider']))
        
        # Validate file paths
        if 'download_directory' in config:
            errors.extend(self._validate_path(config['download_directory']))
        
        # Validate date ranges
        if 'start_year' in config and 'end_year' in config:
            errors.extend(self._validate_date_range(config))
        
        # Check for dangerous patterns in string values
        errors.extend(self._scan_for_dangerous_patterns(config))
        
        return errors
    
    def _validate_provider_config(self, provider_config: Dict[str, Any]) -> List[str]:
        """Validate provider-specific configuration"""
        errors = []
        
        # Validate provider type
        allowed_providers = ['barchart', 'yahoo', 'ibkr']
        provider_type = provider_config.get('type')
        if provider_type not in allowed_providers:
            errors.append(f"Invalid provider type: {provider_type}")
        
        # Validate host/port for IBKR
        if provider_type == 'ibkr':
            host = provider_config.get('host')
            if host and not self._is_valid_hostname(host):
                errors.append(f"Invalid hostname: {host}")
            
            port = provider_config.get('port')
            if port and not self._is_valid_port(port):
                errors.append(f"Invalid port: {port}")
        
        return errors
    
    def _validate_path(self, path: str) -> List[str]:
        """Validate file path for security"""
        errors = []
        
        try:
            path_obj = Path(path)
            
            # Check for path traversal
            if '..' in str(path_obj):
                errors.append("Path traversal detected in path")
            
            # Check for absolute paths outside allowed directories
            if path_obj.is_absolute():
                allowed_roots = [Path.home(), Path('/tmp'), Path('/data')]
                if not any(str(path_obj).startswith(str(root)) for root in allowed_roots):
                    errors.append(f"Path outside allowed directories: {path}")
            
        except Exception as e:
            errors.append(f"Invalid path format: {e}")
        
        return errors
    
    def _scan_for_dangerous_patterns(self, config: Dict[str, Any], 
                                   prefix: str = "") -> List[str]:
        """Recursively scan configuration for dangerous patterns"""
        errors = []
        
        for key, value in config.items():
            current_path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, str):
                for pattern in self.dangerous_patterns:
                    if re.search(pattern, value):
                        errors.append(f"Dangerous pattern detected in {current_path}: {value}")
            elif isinstance(value, dict):
                errors.extend(self._scan_for_dangerous_patterns(value, current_path))
        
        return errors
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """Validate hostname format"""
        if len(hostname) > 255:
            return False
        
        # Allow localhost and IP addresses
        if hostname in ['localhost', '127.0.0.1', '::1']:
            return True
        
        # Basic hostname validation
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return bool(re.match(hostname_pattern, hostname))
    
    def _is_valid_port(self, port: Any) -> bool:
        """Validate port number"""
        try:
            port_num = int(port)
            return 1 <= port_num <= 65535
        except (ValueError, TypeError):
            return False
```

## 3. Secure Logging Implementation

### 3.1 Secure Logger Configuration
```python
import logging
import logging.handlers
import re
from typing import Set

class SecureFormatter(logging.Formatter):
    """Logging formatter that redacts sensitive information"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Patterns for sensitive data
        self.sensitive_patterns = [
            (r'password["\']?\s*[:=]\s*["\']?([^"\',\s]+)', 'password=***'),
            (r'api_key["\']?\s*[:=]\s*["\']?([^"\',\s]+)', 'api_key=***'),
            (r'token["\']?\s*[:=]\s*["\']?([^"\',\s]+)', 'token=***'),
            (r'secret["\']?\s*[:=]\s*["\']?([^"\',\s]+)', 'secret=***'),
            (r'Authorization:\s*Bearer\s+([^\s]+)', 'Authorization: Bearer ***'),
        ]
    
    def format(self, record):
        """Format log record and redact sensitive information"""
        # Format the record normally first
        formatted = super().format(record)
        
        # Apply redaction patterns
        for pattern, replacement in self.sensitive_patterns:
            formatted = re.sub(pattern, replacement, formatted, flags=re.IGNORECASE)
        
        return formatted

def setup_secure_logging(log_level: str = "INFO", log_file: str = None):
    """Setup secure logging configuration"""
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create secure formatter
    formatter = SecureFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        
        # Secure file permissions
        import os
        os.chmod(log_file, 0o600)
        
        logger.addHandler(file_handler)
    
    return logger
```

## 4. Data Sanitization Implementation

### 4.1 Data Sanitizer
```python
import pandas as pd
import numpy as np
from typing import Dict, List, Any

class DataSanitizer:
    """Sanitizes data before storage to prevent injection attacks"""
    
    def __init__(self):
        self.max_string_length = 1000
        self.allowed_columns = {
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'symbol', 'provider', 'exchange'
        }
        
    def sanitize_dataframe(self, data: pd.DataFrame) -> pd.DataFrame:
        """Sanitize entire DataFrame"""
        if data.empty:
            return data
        
        sanitized = data.copy()
        
        # Validate column names
        sanitized = self._validate_columns(sanitized)
        
        # Sanitize string columns
        for column in sanitized.select_dtypes(include=['object']).columns:
            sanitized[column] = sanitized[column].apply(self._sanitize_string)
        
        # Validate numeric ranges
        sanitized = self._validate_numeric_ranges(sanitized)
        
        # Remove any potential injection patterns
        sanitized = self._remove_injection_patterns(sanitized)
        
        return sanitized
    
    def _validate_columns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate column names against allowed list"""
        invalid_columns = set(data.columns) - self.allowed_columns
        if invalid_columns:
            logging.getLogger(__name__).warning(
                f"Removing invalid columns: {invalid_columns}"
            )
            return data[list(set(data.columns) & self.allowed_columns)]
        return data
    
    def _sanitize_string(self, value: Any) -> str:
        """Sanitize individual string value"""
        if pd.isna(value):
            return ""
        
        # Convert to string and limit length
        str_value = str(value)[:self.max_string_length]
        
        # Remove control characters
        str_value = ''.join(char for char in str_value if ord(char) >= 32 or char in '\t\n\r')
        
        # Remove potential script tags and SQL patterns
        dangerous_patterns = [
            r'<script.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'SELECT\s+.*\s+FROM',
            r'INSERT\s+INTO',
            r'UPDATE\s+.*\s+SET',
            r'DELETE\s+FROM',
            r'DROP\s+TABLE',
        ]
        
        for pattern in dangerous_patterns:
            str_value = re.sub(pattern, '', str_value, flags=re.IGNORECASE)
        
        return str_value.strip()
    
    def _validate_numeric_ranges(self, data: pd.DataFrame) -> pd.DataFrame:
        """Validate numeric columns are within reasonable ranges"""
        sanitized = data.copy()
        
        # Price validation (must be positive, reasonable range)
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in sanitized.columns:
                # Remove negative prices
                sanitized[col] = sanitized[col].where(sanitized[col] > 0)
                
                # Remove unreasonably large prices (> $1M)
                sanitized[col] = sanitized[col].where(sanitized[col] < 1000000)
        
        # Volume validation (must be non-negative)
        if 'volume' in sanitized.columns:
            sanitized['volume'] = sanitized['volume'].where(sanitized['volume'] >= 0)
        
        return sanitized
    
    def _remove_injection_patterns(self, data: pd.DataFrame) -> pd.DataFrame:
        """Remove potential injection patterns from all columns"""
        sanitized = data.copy()
        
        for column in sanitized.select_dtypes(include=['object']).columns:
            # Remove potential path traversal
            sanitized[column] = sanitized[column].str.replace(r'\.\./', '', regex=True)
            
            # Remove potential command injection
            sanitized[column] = sanitized[column].str.replace(r'[;&|`$()]', '', regex=True)
        
        return sanitized
```

## 5. Access Control Implementation

### 5.1 File Permission Manager
```python
import os
import stat
from pathlib import Path

class FilePermissionManager:
    """Manages secure file permissions"""
    
    def __init__(self):
        self.secure_file_mode = 0o600  # Owner read/write only
        self.secure_dir_mode = 0o700   # Owner full access only
        
    def secure_file(self, file_path: Path):
        """Set secure permissions on file"""
        if file_path.exists():
            file_path.chmod(self.secure_file_mode)
            
    def secure_directory(self, dir_path: Path):
        """Set secure permissions on directory"""
        if dir_path.exists():
            dir_path.chmod(self.secure_dir_mode)
            
    def create_secure_file(self, file_path: Path, content: str = ""):
        """Create file with secure permissions"""
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True, mode=self.secure_dir_mode)
        
        # Create file with secure permissions
        file_path.write_text(content)
        self.secure_file(file_path)
        
    def validate_file_permissions(self, file_path: Path) -> bool:
        """Validate file has secure permissions"""
        if not file_path.exists():
            return False
            
        file_stat = file_path.stat()
        file_mode = stat.filemode(file_stat.st_mode)
        
        # Check if file is readable by group or others
        if file_stat.st_mode & (stat.S_IRGRP | stat.S_IROTH):
            return False
            
        # Check if file is writable by group or others
        if file_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            return False
            
        return True
```

## 6. Security Exception Classes

### 6.1 Security Exceptions
```python
class SecurityError(Exception):
    """Base security exception"""
    pass

class CredentialError(SecurityError):
    """Credential-related security error"""
    pass

class ValidationError(SecurityError):
    """Input validation error"""
    pass

class PermissionError(SecurityError):
    """File permission error"""
    pass

class InjectionError(SecurityError):
    """Potential injection attack detected"""
    pass
```

## Related Documents

- **[Security Design](../hld/06-security-design.md)** - High-level security architecture
- **[Component Implementation](01-component-implementation.md)** - Security integration details
- **[Storage Implementation](04-storage-implementation.md)** - Secure storage implementation

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** Security Engineer, Senior Developer