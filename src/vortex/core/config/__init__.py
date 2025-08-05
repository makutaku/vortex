"""
Unified configuration management for Vortex.

This module consolidates all configuration functionality from the previous
scattered locations (config.py, cli/utils/config_manager.py) into a single,
comprehensive configuration system.

Key Features:
- Pydantic-based configuration models with validation
- TOML file support with environment variable overrides
- Interactive configuration management
- Provider-specific configuration handling
- Configuration migration and import/export
- Schema validation and error handling

Usage:
    from vortex.core.config import VortexConfig, ConfigManager
    
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # Access provider settings
    barchart_config = config.providers.barchart
    
    # Interactive configuration
    config_manager.set_provider_config("barchart", {"username": "user"})
"""

from .models import (
    VortexConfig,
    GeneralConfig,
    ProvidersConfig,
    BarchartConfig,
    YahooConfig,
    IBKRConfig,
    LoggingConfig,
    DateRangeConfig,
    LogLevel,
    Provider
)
from .manager import ConfigManager, VortexSettings
from .exceptions import (
    ConfigurationError,
    InvalidConfigurationError,
    MissingConfigurationError,
    ConfigurationValidationError
)

__all__ = [
    # Configuration models
    'VortexConfig',
    'GeneralConfig',
    'ProvidersConfig',
    'BarchartConfig',
    'YahooConfig',
    'IBKRConfig',
    'LoggingConfig',
    'DateRangeConfig',
    'LogLevel',
    'Provider',
    
    # Configuration management
    'ConfigManager',
    'VortexSettings',
    
    # Exceptions
    'ConfigurationError',
    'InvalidConfigurationError',
    'MissingConfigurationError',
    'ConfigurationValidationError',
]