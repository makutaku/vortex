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
        message = f"Invalid configuration for '{field}': got '{value}', expected {expected}"
        help_text = f"Please check your configuration file or use 'vortex config --help' for guidance"
        super().__init__(message, help_text, "CONFIG_INVALID")


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    
    def __init__(self, field: str, config_location: Optional[str] = None):
        message = f"Missing required configuration: '{field}'"
        help_text = f"Set this value using 'vortex config --provider <provider> --set-credentials'"
        if config_location:
            help_text += f" or add it to {config_location}"
        super().__init__(message, help_text, "CONFIG_MISSING")


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration fails validation."""
    
    def __init__(self, errors: List[str]):
        message = f"Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
        help_text = "Fix the configuration errors above and try again"
        super().__init__(message, help_text, "CONFIG_VALIDATION")