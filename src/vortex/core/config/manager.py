"""
Unified configuration manager for Vortex.

This module consolidates configuration management functionality from:
- src/vortex/config.py (ConfigManager class)
- src/vortex/cli/utils/config_manager.py (ConfigManager class)

Provides a single, comprehensive configuration management system.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
except ImportError:
    tomllib = None

import tomli_w

from .models import VortexConfig, VortexSettings
from .exceptions import (
    ConfigurationError,
    InvalidConfigurationError,
    MissingConfigurationError, 
    ConfigurationValidationError
)


class ConfigManager:
    """
    Unified configuration manager with validation and migration support.
    
    Consolidates functionality from both the original config.py ConfigManager
    and the CLI utils ConfigManager into a single, comprehensive system.
    """
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to custom config file. If None, uses default location.
        """
        if config_file:
            self.config_file = Path(config_file)
        else:
            # Use standard user config directory with fallback
            try:
                config_dir = Path.home() / ".config" / "vortex"
                config_dir.mkdir(parents=True, exist_ok=True)
                self.config_file = config_dir / "config.toml"
            except (OSError, PermissionError):
                # Fallback to current directory if home config not writable
                config_dir = Path.cwd() / ".vortex"
                try:
                    config_dir.mkdir(parents=True, exist_ok=True)
                    self.config_file = config_dir / "config.toml"
                except (OSError, PermissionError):
                    # Final fallback - no persistent config
                    self.config_file = None
        
        self._config: Optional[VortexConfig] = None
        self._settings = VortexSettings()
    
    @property
    def config_directory(self) -> Path:
        """Get the configuration directory."""
        return self.config_file.parent if self.config_file else Path.cwd()
    
    def load_config(self) -> VortexConfig:
        """Load and validate configuration from file and environment."""
        if self._config is not None:
            return self._config
        
        # Start with defaults
        config_data = {}
        
        # Load from TOML file if it exists
        if self.config_file and self.config_file.exists():
            config_data = self._load_toml_file()
        
        # Apply environment variable overrides
        config_data = self._apply_env_overrides(config_data)
        
        # Validate and create config object
        try:
            self._config = VortexConfig(**config_data)
        except Exception as e:
            raise ConfigurationValidationError([str(e)])
        
        return self._config
    
    def _load_toml_file(self) -> Dict[str, Any]:
        """Load configuration from TOML file."""
        if tomllib is None:
            raise ConfigurationError(
                "TOML support not available",
                "Install the 'tomli' package: pip install tomli"
            )
        
        try:
            with open(self.config_file, 'rb') as f:
                return tomllib.load(f)
        except FileNotFoundError:
            return {}
        except PermissionError as e:
            raise ConfigurationError(
                f"Cannot read configuration file: {e}",
                f"Check file permissions for {self.config_file}"
            )
        except Exception as e:
            raise InvalidConfigurationError(
                str(self.config_file), 
                str(e), 
                "valid TOML format"
            )
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        # Initialize nested dictionaries if they don't exist
        if "general" not in config_data:
            config_data["general"] = {}
        if "providers" not in config_data:
            config_data["providers"] = {}
        if "barchart" not in config_data["providers"]:
            config_data["providers"]["barchart"] = {}
        if "ibkr" not in config_data["providers"]:
            config_data["providers"]["ibkr"] = {}
        
        # Apply modern environment variables
        if self._settings.vortex_output_directory:
            config_data["general"]["output_directory"] = self._settings.vortex_output_directory
        if self._settings.vortex_log_level:
            config_data["general"]["log_level"] = self._settings.vortex_log_level
        if self._settings.vortex_backup_enabled is not None:
            config_data["general"]["backup_enabled"] = self._settings.vortex_backup_enabled
        if self._settings.vortex_dry_run is not None:
            config_data["general"]["dry_run"] = self._settings.vortex_dry_run
        if self._settings.vortex_default_provider:
            config_data["general"]["default_provider"] = self._settings.vortex_default_provider
        
        # Apply logging environment variables
        if "logging" not in config_data["general"]:
            config_data["general"]["logging"] = {}
        
        if self._settings.vortex_logging_level:
            config_data["general"]["logging"]["level"] = self._settings.vortex_logging_level
        if self._settings.vortex_logging_format:
            config_data["general"]["logging"]["format"] = self._settings.vortex_logging_format
        if self._settings.vortex_logging_output:
            # Parse comma-separated outputs
            outputs = [o.strip() for o in self._settings.vortex_logging_output.split(",")]
            config_data["general"]["logging"]["output"] = outputs
        if self._settings.vortex_logging_file_path:
            config_data["general"]["logging"]["file_path"] = self._settings.vortex_logging_file_path
        
        if self._settings.vortex_barchart_username:
            config_data["providers"]["barchart"]["username"] = self._settings.vortex_barchart_username
        if self._settings.vortex_barchart_password:
            config_data["providers"]["barchart"]["password"] = self._settings.vortex_barchart_password
        if self._settings.vortex_barchart_daily_limit:
            config_data["providers"]["barchart"]["daily_limit"] = self._settings.vortex_barchart_daily_limit
        
        if self._settings.vortex_ibkr_host:
            config_data["providers"]["ibkr"]["host"] = self._settings.vortex_ibkr_host
        if self._settings.vortex_ibkr_port:
            config_data["providers"]["ibkr"]["port"] = self._settings.vortex_ibkr_port
        if self._settings.vortex_ibkr_client_id:
            config_data["providers"]["ibkr"]["client_id"] = self._settings.vortex_ibkr_client_id
        
        return config_data
    
    def save_config(self, config: Optional[VortexConfig] = None) -> None:
        """Save configuration to TOML file."""
        if config is None:
            config = self.load_config()
        
        # Handle case where no config file is available
        if self.config_file is None:
            return
        
        # Ensure directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary for serialization
        config_dict = config.model_dump(exclude_unset=False, mode='json')
        
        # Convert Path objects to strings for TOML serialization
        if 'general' in config_dict and 'output_directory' in config_dict['general']:
            config_dict['general']['output_directory'] = str(config_dict['general']['output_directory'])
        
        try:
            with open(self.config_file, 'wb') as f:
                tomli_w.dump(config_dict, f)
        except PermissionError as e:
            raise ConfigurationError(
                f"Cannot write configuration file: {e}",
                f"Check write permissions for {self.config_file.parent}"
            )
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        config = self.load_config()
        
        if provider == "barchart":
            return config.providers.barchart.model_dump()
        elif provider == "yahoo":
            return config.providers.yahoo.model_dump()
        elif provider == "ibkr":
            return config.providers.ibkr.model_dump()
        else:
            raise InvalidConfigurationError("provider", provider, "barchart, yahoo, or ibkr")
    
    def set_provider_config(self, provider: str, provider_config: Dict[str, Any]) -> None:
        """Set configuration for a specific provider."""
        from .models import BarchartConfig, YahooConfig, IBKRConfig
        
        config = self.load_config()
        
        try:
            if provider == "barchart":
                config.providers.barchart = BarchartConfig(**provider_config)
            elif provider == "yahoo":
                config.providers.yahoo = YahooConfig(**provider_config)
            elif provider == "ibkr":
                config.providers.ibkr = IBKRConfig(**provider_config)
            else:
                raise InvalidConfigurationError("provider", provider, "barchart, yahoo, or ibkr")
        except Exception as e:
            raise ConfigurationValidationError([f"Invalid {provider} configuration: {e}"])
        
        # Save the updated configuration
        self.save_config(config)
        
        # Update cached config
        self._config = config
    
    def validate_provider_credentials(self, provider: str) -> bool:
        """Validate that provider has required credentials."""
        config = self.load_config()
        
        if provider == "barchart":
            return (config.providers.barchart.username is not None and 
                   config.providers.barchart.password is not None)
        elif provider == "yahoo":
            return True  # No credentials required
        elif provider == "ibkr":
            return True  # Connection details are sufficient
        else:
            return False
    
    def get_missing_credentials(self, provider: str) -> List[str]:
        """Get list of missing credential fields for a provider."""
        missing = []
        
        if provider == "barchart":
            config = self.load_config()
            if not config.providers.barchart.username:
                missing.append("username")
            if not config.providers.barchart.password:
                missing.append("password")
        # Yahoo and IBKR don't require credentials
        
        return missing
    
    def get_default_provider(self) -> str:
        """Get the default provider from configuration."""
        config = self.load_config()
        return config.general.default_provider.value
    
    def import_config(self, file_path: Path) -> None:
        """Import configuration from another TOML file."""
        if not file_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {file_path}",
                "Check that the file path is correct"
            )
        
        try:
            with open(file_path, 'rb') as f:
                imported_data = tomllib.load(f)
            
            # Validate imported configuration
            imported_config = VortexConfig(**imported_data)
            
            # Save to our config file
            self.save_config(imported_config)
            
            # Update cached config
            self._config = imported_config
            
        except Exception as e:
            raise ConfigurationValidationError([f"Invalid configuration file: {e}"])
    
    def export_config(self, file_path: Path) -> None:
        """Export current configuration to a TOML file."""
        config = self.load_config()
        
        # Ensure target directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary for serialization
        config_dict = config.model_dump(exclude_unset=False, mode='json')
        
        # Convert Path objects to strings
        if 'general' in config_dict and 'output_directory' in config_dict['general']:
            config_dict['general']['output_directory'] = str(config_dict['general']['output_directory'])
        
        try:
            with open(file_path, 'wb') as f:
                tomli_w.dump(config_dict, f)
        except PermissionError as e:
            raise ConfigurationError(
                f"Cannot write to export file: {e}",
                f"Check write permissions for {file_path.parent}"
            )
    
    def reset_config(self) -> None:
        """Reset configuration to defaults."""
        self._config = VortexConfig()
        self.save_config()
    
    # Additional methods from CLI ConfigManager for compatibility
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration (legacy CLI compatibility)."""
        return VortexConfig().model_dump(mode='json')
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries (legacy CLI compatibility)."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result