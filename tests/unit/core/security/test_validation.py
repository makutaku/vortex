"""
Unit tests for security validation utilities.

Tests comprehensive input validation for security-sensitive operations.
"""

import pytest
from vortex.core.security.validation import (
    InputValidator, 
    CredentialSanitizer, 
    ValidationResult
)
from vortex.exceptions.config import ConfigurationValidationError


@pytest.mark.unit
class TestInputValidator:
    """Test InputValidator class."""
    
    def test_validate_username_valid(self):
        """Test valid username validation."""
        result = InputValidator.validate_username("user@example.com")
        assert result.is_valid
        assert result.error_message is None
    
    def test_validate_username_too_short(self):
        """Test username validation with too short input."""
        result = InputValidator.validate_username("ab")
        assert not result.is_valid
        assert "at least 3 characters" in result.error_message
    
    def test_validate_username_too_long(self):
        """Test username validation with too long input."""
        long_username = "a" * 300
        result = InputValidator.validate_username(long_username)
        assert not result.is_valid
        assert "not exceed 254 characters" in result.error_message
    
    def test_validate_username_dangerous_chars(self):
        """Test username validation with dangerous characters."""
        result = InputValidator.validate_username("user<script>")
        assert not result.is_valid
        assert "dangerous characters" in result.error_message
    
    def test_validate_password_valid(self):
        """Test valid password validation."""
        result = InputValidator.validate_password("SecurePass123!")
        assert result.is_valid
        assert result.error_message is None
    
    def test_validate_password_too_short(self):
        """Test password validation with too short input."""
        result = InputValidator.validate_password("abc123")
        assert not result.is_valid
        assert "at least 8 characters" in result.error_message
    
    def test_validate_password_null_byte(self):
        """Test password validation with null byte."""
        result = InputValidator.validate_password("password\x00test")
        assert not result.is_valid
        assert "control characters" in result.error_message
    
    def test_validate_credentials_valid(self):
        """Test valid credential validation."""
        is_valid, errors = InputValidator.validate_credentials(
            "user@example.com", "SecurePass123!"
        )
        assert is_valid
        assert len(errors) == 0
    
    def test_validate_credentials_invalid(self):
        """Test invalid credential validation."""
        is_valid, errors = InputValidator.validate_credentials("ab", "123")
        assert not is_valid
        assert len(errors) == 2
        assert any("Username" in error for error in errors)
        assert any("Password" in error for error in errors)


@pytest.mark.unit
class TestCredentialSanitizer:
    """Test CredentialSanitizer class."""
    
    def test_mask_credential_short(self):
        """Test masking short credentials."""
        result = CredentialSanitizer.mask_credential("abc")
        assert result == "***"
    
    def test_mask_credential_long(self):
        """Test masking long credentials."""
        result = CredentialSanitizer.mask_credential("password123")
        assert result == "*******d123"
        assert result.endswith("d123")
    
    def test_mask_credential_empty(self):
        """Test masking empty credentials."""
        result = CredentialSanitizer.mask_credential("")
        assert result == "[empty]"
    
    def test_validate_and_sanitize_valid(self):
        """Test validation and sanitization of valid credentials."""
        username, password, warnings = CredentialSanitizer.validate_and_sanitize_credentials(
            "  user@example.com  ", "SecurePass123!"
        )
        assert username == "user@example.com"  # Trimmed
        assert password == "SecurePass123!"    # Not modified
        assert isinstance(warnings, list)
    
    def test_validate_and_sanitize_invalid(self):
        """Test validation and sanitization of invalid credentials."""
        with pytest.raises(ConfigurationValidationError):
            CredentialSanitizer.validate_and_sanitize_credentials("ab", "123")


@pytest.mark.unit
class TestValidationResult:
    """Test ValidationResult dataclass."""
    
    def test_validation_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(True)
        assert result.is_valid
        assert result.error_message is None
        assert result.warnings == []
    
    def test_validation_result_with_warnings(self):
        """Test ValidationResult with warnings."""
        warnings = ["Warning 1", "Warning 2"]
        result = ValidationResult(True, warnings=warnings)
        assert result.is_valid
        assert result.warnings == warnings


@pytest.mark.unit
class TestInputValidatorAdvanced:
    """Test advanced InputValidator functionality."""
    
    def test_validate_username_non_string(self):
        """Test username validation with non-string input."""
        result = InputValidator.validate_username(123)
        assert not result.is_valid
        assert "must be a string" in result.error_message
    
    def test_validate_username_control_characters(self):
        """Test username validation with control characters."""
        result = InputValidator.validate_username("user\x1f@example.com")
        assert not result.is_valid
        assert "control characters" in result.error_message
    
    def test_validate_username_email_like_invalid(self):
        """Test username validation with invalid email format."""
        result = InputValidator.validate_username("user@invalid")
        assert result.is_valid  # Still valid as username
        assert any("email but format is invalid" in warning for warning in result.warnings)
    
    def test_validate_username_unsafe_characters(self):
        """Test username validation with unsafe characters."""
        result = InputValidator.validate_username("user[bracket]")
        assert result.is_valid  # Still valid but with warnings
        assert any("unsafe characters" in warning for warning in result.warnings)
    
    def test_validate_password_non_string(self):
        """Test password validation with non-string input."""
        result = InputValidator.validate_password(None)
        assert not result.is_valid
        assert "must be a string" in result.error_message
    
    def test_validate_password_too_long(self):
        """Test password validation with too long input."""
        long_password = "a" * 200
        result = InputValidator.validate_password(long_password)
        assert not result.is_valid
        assert "not exceed 128 characters" in result.error_message
    
    def test_validate_password_control_characters(self):
        """Test password validation with prohibited control characters."""
        result = InputValidator.validate_password("password\x01test")
        assert not result.is_valid
        assert "control characters" in result.error_message
    
    def test_validate_password_strength_warnings(self):
        """Test password validation strength warnings."""
        result = InputValidator.validate_password("alllowercase")
        assert result.is_valid
        assert any("uppercase" in warning for warning in result.warnings)
        
        result = InputValidator.validate_password("ALLUPPERCASE")
        assert result.is_valid
        assert any("lowercase" in warning for warning in result.warnings)
        
        result = InputValidator.validate_password("NoNumbers!")
        assert result.is_valid
        assert any("numbers" in warning for warning in result.warnings)
        
        result = InputValidator.validate_password("NoSpecial123")
        assert result.is_valid
        assert any("special characters" in warning for warning in result.warnings)
    
    def test_sanitize_for_logging_edge_cases(self):
        """Test logging sanitization edge cases."""
        result = InputValidator.sanitize_for_logging("")
        assert result == ""
        
        result = InputValidator.sanitize_for_logging("a")
        assert result == "*"
        
        result = InputValidator.sanitize_for_logging("ab")
        assert result == "**"
        
        result = InputValidator.sanitize_for_logging("abc")
        assert result == "***"
        
        result = InputValidator.sanitize_for_logging("abcdef", mask_char='#')
        assert result == "ab###f"
    
    def test_validate_file_path_non_string(self):
        """Test file path validation with non-string input."""
        result = InputValidator.validate_file_path(123)
        assert not result.is_valid
        assert "must be a string" in result.error_message
    
    def test_validate_file_path_too_long(self):
        """Test file path validation with too long input."""
        long_path = "a" * 1100
        result = InputValidator.validate_file_path(long_path)
        assert not result.is_valid
        assert "too long" in result.error_message
    
    def test_validate_file_path_traversal_attacks(self):
        """Test file path validation against path traversal."""
        dangerous_paths = [
            "../etc/passwd",
            "..\\windows\\system32",
            "/./secret",
            "\\.\\secret"
        ]
        for path in dangerous_paths:
            result = InputValidator.validate_file_path(path)
            assert not result.is_valid
            assert "dangerous pattern" in result.error_message
    
    def test_validate_file_path_absolute_warning(self):
        """Test file path validation with absolute path warning."""
        result = InputValidator.validate_file_path("/absolute/path")
        assert result.is_valid
        assert any("absolute file path" in warning for warning in result.warnings)
        
        result = InputValidator.validate_file_path("C:\\windows\\path")
        assert result.is_valid
        assert any("absolute file path" in warning for warning in result.warnings)


@pytest.mark.unit
class TestCredentialSanitizerAdvanced:
    """Test advanced CredentialSanitizer functionality."""
    
    def test_mask_credential_edge_cases(self):
        """Test credential masking edge cases."""
        # Test with different visible_chars values
        result = CredentialSanitizer.mask_credential("password123", visible_chars=2)
        assert result == "*********23"
        
        result = CredentialSanitizer.mask_credential("password123", visible_chars=20)
        assert result == "***********"  # Should mask completely when visible_chars > length
    
    def test_validate_and_sanitize_with_whitespace(self):
        """Test credential validation and sanitization with whitespace."""
        username, password, warnings = CredentialSanitizer.validate_and_sanitize_credentials(
            "  user@example.com  ", "ValidPass123!"
        )
        assert username == "user@example.com"  # Trimmed
        assert password == "ValidPass123!"     # Not modified
        assert isinstance(warnings, list)
    
    def test_validate_and_sanitize_with_warnings(self):
        """Test credential validation and sanitization collects warnings."""
        username, password, warnings = CredentialSanitizer.validate_and_sanitize_credentials(
            "user[unsafe]", "weakpass"
        )
        assert len(warnings) > 0  # Should have warnings from both username and password