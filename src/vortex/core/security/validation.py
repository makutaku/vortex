"""
Security-focused input validation utilities.

This module provides comprehensive input validation for security-sensitive
operations, particularly credential handling and user inputs.
"""

import re
import string
from typing import Optional, List, Tuple
from dataclasses import dataclass

from vortex.exceptions.config import ConfigurationValidationError


@dataclass
class ValidationResult:
    """Result of input validation with detailed feedback."""
    is_valid: bool
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class InputValidator:
    """Comprehensive input validator for security-sensitive operations."""
    
    # Security constraints
    MIN_USERNAME_LENGTH = 3
    MAX_USERNAME_LENGTH = 254  # RFC 5321 email limit
    MIN_PASSWORD_LENGTH = 8
    MAX_PASSWORD_LENGTH = 128
    MAX_INPUT_LENGTH = 1024
    
    # Character sets
    SAFE_USERNAME_CHARS = string.ascii_letters + string.digits + '._@+-'
    DANGEROUS_CHARS = ['<', '>', '"', "'", '&', '\x00', '\n', '\r', '\t']
    
    # Patterns
    EMAIL_PATTERN = re.compile(
        r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    )
    
    @classmethod
    def validate_username(cls, username: str) -> ValidationResult:
        """
        Validate username with security checks.
        
        Args:
            username: Username to validate
            
        Returns:
            ValidationResult with validation status and messages
        """
        if not isinstance(username, str):
            return ValidationResult(False, "Username must be a string")
        
        # Length validation
        if len(username) < cls.MIN_USERNAME_LENGTH:
            return ValidationResult(
                False, 
                f"Username must be at least {cls.MIN_USERNAME_LENGTH} characters"
            )
        
        if len(username) > cls.MAX_USERNAME_LENGTH:
            return ValidationResult(
                False, 
                f"Username must not exceed {cls.MAX_USERNAME_LENGTH} characters"
            )
        
        # Character validation
        dangerous_chars = [char for char in cls.DANGEROUS_CHARS if char in username]
        if dangerous_chars:
            return ValidationResult(
                False, 
                f"Username contains dangerous characters: {dangerous_chars}"
            )
        
        # Control character check
        if any(ord(char) < 32 or ord(char) == 127 for char in username):
            return ValidationResult(
                False, 
                "Username contains control characters"
            )
        
        # Basic format validation for email-like usernames
        warnings = []
        if '@' in username and not cls.EMAIL_PATTERN.match(username):
            warnings.append("Username appears to be email but format is invalid")
        
        # Character set validation
        unsafe_chars = [char for char in username if char not in cls.SAFE_USERNAME_CHARS]
        if unsafe_chars:
            warnings.append(f"Username contains potentially unsafe characters: {unsafe_chars}")
        
        return ValidationResult(True, warnings=warnings)
    
    @classmethod
    def validate_password(cls, password: str) -> ValidationResult:
        """
        Validate password with security requirements.
        
        Args:
            password: Password to validate
            
        Returns:
            ValidationResult with validation status and messages
        """
        if not isinstance(password, str):
            return ValidationResult(False, "Password must be a string")
        
        # Length validation
        if len(password) < cls.MIN_PASSWORD_LENGTH:
            return ValidationResult(
                False, 
                f"Password must be at least {cls.MIN_PASSWORD_LENGTH} characters"
            )
        
        if len(password) > cls.MAX_PASSWORD_LENGTH:
            return ValidationResult(
                False, 
                f"Password must not exceed {cls.MAX_PASSWORD_LENGTH} characters"
            )
        
        # Control character check (passwords can have more variety)
        if any(ord(char) < 32 and char not in ['\t'] for char in password):
            return ValidationResult(
                False, 
                "Password contains prohibited control characters"
            )
        
        # Null byte check (critical security issue)
        if '\x00' in password:
            return ValidationResult(
                False, 
                "Password contains null bytes"
            )
        
        warnings = []
        
        # Strength recommendations (warnings, not errors)
        if not any(char.isupper() for char in password):
            warnings.append("Password should contain uppercase letters")
        
        if not any(char.islower() for char in password):
            warnings.append("Password should contain lowercase letters")
        
        if not any(char.isdigit() for char in password):
            warnings.append("Password should contain numbers")
        
        if not any(char in string.punctuation for char in password):
            warnings.append("Password should contain special characters")
        
        return ValidationResult(True, warnings=warnings)
    
    @classmethod
    def validate_credentials(cls, username: str, password: str) -> Tuple[bool, List[str]]:
        """
        Validate both username and password with security checks.
        
        Args:
            username: Username to validate
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Validate username
        username_result = cls.validate_username(username)
        if not username_result.is_valid:
            errors.append(f"Username validation failed: {username_result.error_message}")
        
        # Validate password
        password_result = cls.validate_password(password)
        if not password_result.is_valid:
            errors.append(f"Password validation failed: {password_result.error_message}")
        
        return len(errors) == 0, errors
    
    @classmethod
    def sanitize_for_logging(cls, value: str, mask_char: str = '*') -> str:
        """
        Sanitize sensitive values for safe logging.
        
        Args:
            value: Value to sanitize
            mask_char: Character to use for masking
            
        Returns:
            Sanitized value safe for logging
        """
        if not value:
            return ""
        
        if len(value) <= 3:
            return mask_char * len(value)
        
        # Show first 2 and last 1 characters, mask the rest
        return value[:2] + mask_char * (len(value) - 3) + value[-1:]
    
    @classmethod
    def validate_file_path(cls, file_path: str) -> ValidationResult:
        """
        Validate file paths for security issues.
        
        Args:
            file_path: File path to validate
            
        Returns:
            ValidationResult with validation status
        """
        if not isinstance(file_path, str):
            return ValidationResult(False, "File path must be a string")
        
        if len(file_path) > cls.MAX_INPUT_LENGTH:
            return ValidationResult(
                False, 
                f"File path too long (max {cls.MAX_INPUT_LENGTH} characters)"
            )
        
        # Path traversal check
        dangerous_patterns = ['../', '..\\', '/./', '\\.\\']
        for pattern in dangerous_patterns:
            if pattern in file_path:
                return ValidationResult(
                    False, 
                    f"File path contains dangerous pattern: {pattern}"
                )
        
        # Null byte check
        if '\x00' in file_path:
            return ValidationResult(
                False, 
                "File path contains null bytes"
            )
        
        warnings = []
        
        # Absolute vs relative path warning
        if file_path.startswith('/') or (len(file_path) > 1 and file_path[1] == ':'):
            warnings.append("Using absolute file path")
        
        return ValidationResult(True, warnings=warnings)


class CredentialSanitizer:
    """Utilities for safely handling credentials."""
    
    @staticmethod
    def mask_credential(credential: str, visible_chars: int = 4) -> str:
        """
        Mask credential for display/logging purposes.
        
        Args:
            credential: Credential to mask
            visible_chars: Number of characters to show at the end
            
        Returns:
            Masked credential string
        """
        if not credential:
            return "[empty]"
        
        if len(credential) <= visible_chars:
            return "*" * len(credential)
        
        return "*" * (len(credential) - visible_chars) + credential[-visible_chars:]
    
    @staticmethod
    def validate_and_sanitize_credentials(
        username: str, 
        password: str
    ) -> Tuple[str, str, List[str]]:
        """
        Validate and sanitize credentials for safe use.
        
        Args:
            username: Raw username
            password: Raw password
            
        Returns:
            Tuple of (sanitized_username, sanitized_password, warnings)
            
        Raises:
            ConfigurationValidationError: If validation fails
        """
        # Validate inputs
        is_valid, errors = InputValidator.validate_credentials(username, password)
        if not is_valid:
            raise ConfigurationValidationError(errors)
        
        # Basic sanitization (trim whitespace, normalize)
        sanitized_username = username.strip()
        sanitized_password = password  # Don't modify password
        
        # Collect warnings
        warnings = []
        username_result = InputValidator.validate_username(sanitized_username)
        password_result = InputValidator.validate_password(sanitized_password)
        
        warnings.extend(username_result.warnings)
        warnings.extend(password_result.warnings)
        
        return sanitized_username, sanitized_password, warnings