"""
Unit tests for the Vortex exception system.
"""

import pytest

from vortex.exceptions import (
    VortexError, ConfigurationError, InvalidConfigurationError,
    ConfigurationValidationError, MissingConfigurationError,
    DataProviderError, DataStorageError, CLIError,
    MissingArgumentError, InvalidCommandError
)


@pytest.mark.unit
class TestVortexError:
    """Test the base VortexError class."""
    
    def test_basic_error_creation(self):
        """Test basic error creation with message and help."""
        error = VortexError("Test error message", help_text="Test help text")
        
        # The new enhanced error format includes help text and error ID
        error_str = str(error)
        assert "Test error message" in error_str
        assert "💡 Help: Test help text" in error_str
        assert "🔍 Error ID:" in error_str
        assert error.help_text == "Test help text"
        assert error.error_code is None
    
    def test_error_with_code(self):
        """Test error creation with error code."""
        error = VortexError("Test error", help_text="Test help", error_code="TEST_001")
        
        assert error.error_code == "TEST_001"
    
    def test_error_without_help(self):
        """Test error creation without help text."""
        error = VortexError("Test error")
        
        # Even without help text, it should include the error ID
        error_str = str(error)
        assert "Test error" in error_str
        assert "🔍 Error ID:" in error_str
        assert "💡 Help:" not in error_str  # No help text should be shown
        assert error.help_text is None
    
    def test_error_chaining(self):
        """Test error chaining with cause."""
        original_error = ValueError("Original error")
        vortex_error = VortexError("Vortex error", help_text="Help text")
        
        # Test that we can chain errors
        try:
            raise vortex_error from original_error
        except VortexError as e:
            assert e.__cause__ is original_error
    
    def test_error_representation(self):
        """Test error representation."""
        error = VortexError("Test message", help_text="Help text", error_code="CODE_001")
        
        repr_str = repr(error)
        assert "VortexError" in repr_str
        assert "Test message" in repr_str


@pytest.mark.unit
class TestConfigurationErrors:
    """Test configuration-related errors."""
    
    def test_configuration_error(self):
        """Test ConfigurationError creation."""
        error = ConfigurationError("Config failed", help_text="Check config file")
        
        assert isinstance(error, VortexError)
        assert "Config failed" in str(error)
        assert error.help_text == "Check config file"
    
    def test_invalid_configuration_error(self):
        """Test InvalidConfigurationError creation."""
        error = InvalidConfigurationError("field_name", "invalid_value", "expected_format")
        
        assert isinstance(error, ConfigurationError)
        assert "field_name" in str(error)
        assert "invalid_value" in str(error)
        assert "expected_format" in str(error)
        # Help text should provide guidance
        assert error.help_text is not None
        assert len(error.help_text) > 0
    
    def test_configuration_validation_error(self):
        """Test ConfigurationValidationError creation."""
        validation_errors = [
            "Field 'username' is required",
            "Field 'port' must be between 1 and 65535"
        ]
        error = ConfigurationValidationError(validation_errors)
        
        assert isinstance(error, ConfigurationError)
        assert "Configuration validation failed" in str(error)
        assert "username" in str(error)
        assert "port" in str(error)
        assert error.help_text is not None
    
    def test_missing_configuration_error(self):
        """Test MissingConfigurationError creation."""
        error = MissingConfigurationError("database_url")
        
        assert isinstance(error, ConfigurationError)
        assert "database_url" in str(error)
        assert "required configuration" in str(error)
        assert error.help_text is not None


@pytest.mark.unit
class TestDataErrors:
    """Test data-related errors."""
    
    def test_data_provider_error(self):
        """Test DataProviderError creation."""
        error = DataProviderError("barchart", "Authentication failed", "Check credentials")
        
        assert isinstance(error, VortexError)
        assert "barchart" in str(error)
        assert "Authentication failed" in str(error)
        assert "Check credentials" in error.help_text
    
    def test_data_storage_error(self):
        """Test DataStorageError creation."""
        error = DataStorageError("/path/to/file - Permission denied", help_text="Check file permissions")
        
        assert isinstance(error, VortexError)
        assert "/path/to/file" in str(error)
        assert "Permission denied" in str(error)
        assert error.help_text is not None


@pytest.mark.unit
class TestCLIErrors:
    """Test CLI-related errors."""
    
    def test_cli_error(self):
        """Test CLIError creation."""
        error = CLIError("Invalid command syntax", help_text="Use --help for usage")
        
        assert isinstance(error, VortexError)
        assert "Invalid command syntax" in str(error)
        assert error.help_text == "Use --help for usage"
    
    def test_missing_argument_error(self):
        """Test MissingArgumentError creation."""
        error = MissingArgumentError("--provider", "download")
        
        assert isinstance(error, CLIError)
        assert "--provider" in str(error)
        assert "download" in str(error)
        # Should mention it's required
        assert "required" in str(error).lower()
        assert error.help_text is not None
    
    def test_invalid_command_error(self):
        """Test InvalidCommandError creation."""
        error = InvalidCommandError("download", "Start date must be before end date")
        
        assert isinstance(error, CLIError)
        assert "download" in str(error)
        assert "Start date must be before end date" in str(error)
        assert "vortex download --help" in error.help_text


@pytest.mark.unit
class TestErrorInheritance:
    """Test error inheritance hierarchy."""
    
    def test_inheritance_chain(self):
        """Test that all errors inherit from VortexError."""
        errors = [
            ConfigurationError("test", help_text="help"),
            InvalidConfigurationError("field", "value", "expected"),
            ConfigurationValidationError(["error"]),
            MissingConfigurationError("field"),
            DataProviderError("provider", "message", "help"),
            DataStorageError("path - message", help_text="help"),
            CLIError("message", help_text="help"),
            MissingArgumentError("arg", "command"),
            InvalidCommandError("command", "reason")
        ]
        
        for error in errors:
            assert isinstance(error, VortexError)
            assert isinstance(error, Exception)
    
    def test_configuration_error_hierarchy(self):
        """Test configuration error inheritance."""
        errors = [
            InvalidConfigurationError("field", "value", "expected"),
            ConfigurationValidationError(["error"]),
            MissingConfigurationError("field")
        ]
        
        for error in errors:
            assert isinstance(error, ConfigurationError)
            assert isinstance(error, VortexError)
    
    def test_cli_error_hierarchy(self):
        """Test CLI error inheritance."""
        errors = [
            MissingArgumentError("arg", "command"),
            InvalidCommandError("command", "reason")
        ]
        
        for error in errors:
            assert isinstance(error, CLIError)
            assert isinstance(error, VortexError)


@pytest.mark.unit
class TestErrorMessages:
    """Test error message formatting."""
    
    def test_error_message_formatting(self):
        """Test that error messages contain key information."""
        # Test various error types have expected key information
        errors = [
            (ConfigurationError("Config error", help_text="Help"), "config error"),
            (InvalidConfigurationError("port", "99999", "1-65535"), "port"),
            (DataProviderError("yahoo", "Network error", "Check connection"), "yahoo"),
            (MissingArgumentError("--symbol", "download"), "--symbol"),
        ]
        
        for error, key_content in errors:
            error_str = str(error)
            assert key_content.lower() in error_str.lower()
    
    def test_help_text_formatting(self):
        """Test that help text is properly formatted."""
        error = InvalidConfigurationError("daily_limit", "2000", "between 1 and 1000")
        
        assert error.help_text is not None
        assert len(error.help_text) > 0  # Just verify help text exists
    
    def test_validation_error_multiple_messages(self):
        """Test validation error with multiple messages."""
        validation_errors = [
            "Username is required",
            "Password must be at least 8 characters",
            "Port must be between 1 and 65535"
        ]
        error = ConfigurationValidationError(validation_errors)
        
        error_str = str(error)
        for validation_error in validation_errors:
            assert validation_error in error_str


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling patterns."""
    
    def test_error_catching(self):
        """Test that errors can be caught at different levels."""
        
        # Test catching specific error type
        with pytest.raises(InvalidConfigurationError):
            raise InvalidConfigurationError("field", "value", "expected")
        
        # Test catching parent class
        with pytest.raises(ConfigurationError):
            raise InvalidConfigurationError("field", "value", "expected")
        
        # Test catching base class
        with pytest.raises(VortexError):
            raise InvalidConfigurationError("field", "value", "expected")
    
    def test_error_context_managers(self):
        """Test errors work properly with context managers."""
        
        class TestContext:
            def __enter__(self):
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if isinstance(exc_val, VortexError):
                    # Handle VortexError specially
                    return True  # Suppress the exception
                return False
        
        # Test that VortexError is handled by context manager
        with TestContext():
            raise ConfigurationError("Test error", help_text="Test help")
        
        # Test that other errors are not handled
        with pytest.raises(ValueError):
            with TestContext():
                raise ValueError("Regular error")
    
    def test_error_chaining_preservation(self):
        """Test that error chaining is preserved."""
        original = FileNotFoundError("File not found")
        
        try:
            raise ConfigurationError("Config file missing", help_text="Check file path") from original
        except ConfigurationError as e:
            assert e.__cause__ is original
            assert isinstance(e.__cause__, FileNotFoundError)