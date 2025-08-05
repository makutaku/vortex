"""
Configuration-specific exceptions.

This module defines exceptions specific to configuration management,
extracted from the main exceptions module for better organization.
"""

from typing import List, Optional, Any


class ConfigurationError(Exception):
    """Base exception for configuration-related errors."""
    
    def __init__(self, message: str, help_text: Optional[str] = None):
        self.message = message
        self.help_text = help_text
        super().__init__(message)
    
    def __str__(self) -> str:
        if self.help_text:
            return f"{self.message}\n\nHelp: {self.help_text}"
        return self.message


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration contains invalid values."""
    
    def __init__(self, field: str, value: Any, expected: str):
        message = f"Invalid configuration for '{field}': got {repr(value)}, expected {expected}"
        help_text = f"Please check the configuration for '{field}' and ensure it matches the expected format: {expected}"
        super().__init__(message, help_text)
        self.field = field
        self.value = value
        self.expected = expected


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    
    def __init__(self, field: str, help_text: Optional[str] = None):
        message = f"Missing required configuration: '{field}'"
        if not help_text:
            help_text = f"Please provide a value for '{field}' in your configuration file or environment variables"
        super().__init__(message, help_text)
        self.field = field


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration validation fails."""
    
    def __init__(self, errors: List[str]):
        self.errors = errors
        message = "Configuration validation failed:"
        for error in errors:
            message += f"\n  - {error}"
        
        help_text = "Please check your configuration file and fix the validation errors listed above"
        super().__init__(message, help_text)