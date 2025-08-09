"""
Configuration-related exceptions.

All exceptions related to configuration parsing, validation, and management.
"""

from typing import Any, List, Optional

from .base import VortexError


class ConfigurationError(VortexError):
    """Base class for configuration-related errors."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration contains invalid values."""
    
    def __init__(self, field: str, value: Any, expected: str):
        self.field = field
        self.value = value
        self.expected = expected
        message = f"Invalid configuration for '{field}': got {repr(value)}, expected {expected}"
        help_text = f"Please check the configuration for '{field}' and ensure it matches the expected format: {expected}"
        user_action = f"Run 'vortex config --provider <provider> --help' for valid values"
        super().__init__(message, help_text=help_text, error_code="CONFIG_INVALID", user_action=user_action)


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    
    def __init__(self, field: str, config_location: Optional[str] = None):
        message = f"Missing required configuration: '{field}'"
        help_text = f"Set this value using 'vortex config --provider <provider> --set-credentials'"
        if config_location:
            help_text += f" or add it to {config_location}"
        super().__init__(message, help_text=help_text, error_code="CONFIG_MISSING")


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration fails validation."""
    
    def __init__(self, errors: List[str]):
        self.errors = errors
        message = "Configuration validation failed:"
        for error in errors:
            message += f"\n  - {error}"
        
        help_text = "Please check your configuration file and fix the validation errors listed above"
        user_action = "Run 'vortex config --validate' to check your configuration"
        super().__init__(message, help_text=help_text, error_code="CONFIG_VALIDATION", user_action=user_action)