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
from dataclasses import dataclass

try:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
except ImportError:
    tomllib = None

import tomli_w

from .models import VortexConfig, VortexSettings
from ...exceptions.config import (
    ConfigurationError,
    InvalidConfigurationError,
    MissingConfigurationError, 
    ConfigurationValidationError
)
from ...utils.error_handling import FileOperationHandler


@dataclass
class EnvironmentOverride:
    """Helper for applying environment variable overrides."""
    config_section: Dict[str, Any]
    settings: VortexSettings
    
    def apply_if_set(self, setting_name: str, config_key: str) -> None:
        """Apply setting if it's set in environment."""
        value = getattr(self.settings, setting_name, None)
        if value is not None:
            self.config_section[config_key] = value
    
    def apply_string_if_set(self, setting_name: str, config_key: str) -> None:
        """Apply string setting if it's set in environment."""
        value = getattr(self.settings, setting_name, None)
        if value:
            self.config_section[config_key] = value


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
        except (ValueError, TypeError) as e:
            raise ConfigurationValidationError([f"Configuration validation failed: {e}"])
        except Exception as e:
            raise ConfigurationValidationError([f"Unexpected configuration error: {e}"])
        
        return self._config
    
    def _load_toml_file(self) -> Dict[str, Any]:
        """Load configuration from TOML file."""
        if tomllib is None:
            raise ConfigurationError(
                "TOML support not available",
                help_text="Install the 'tomli' package: pip install tomli"
            )
        
        def load_toml_content(f):
            try:
                return tomllib.load(f)
            except tomllib.TOMLDecodeError as e:
                # Specific TOML parsing error
                raise InvalidConfigurationError(
                    str(self.config_file), 
                    f"Invalid TOML syntax: {e}", 
                    "valid TOML format"
                )
            except (ValueError, TypeError) as e:
                # Data type or value errors
                raise InvalidConfigurationError(
                    str(self.config_file), 
                    f"Invalid configuration values: {e}", 
                    "valid TOML format"
                )
            except Exception as e:
                # Unexpected errors
                raise InvalidConfigurationError(
                    str(self.config_file), 
                    f"Failed to parse TOML file: {e}", 
                    "valid TOML format"
                )
        
        return FileOperationHandler.safe_file_operation(
            file_path=self.config_file,
            operation=load_toml_content,
            mode='rb',
            file_type="configuration file",
            operation_name="read",
            default_on_missing={}
        )
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration."""
        settings = VortexSettings()
        
        self._initialize_config_sections(config_data)
        self._apply_general_env_overrides(config_data, settings)
        self._apply_logging_env_overrides(config_data, settings)
        self._apply_provider_env_overrides(config_data, settings)
        
        return config_data
    
    def _initialize_config_sections(self, config_data: Dict[str, Any]) -> None:
        """Initialize nested configuration dictionaries if they don't exist."""
        if "general" not in config_data:
            config_data["general"] = {}
        if "providers" not in config_data:
            config_data["providers"] = {}
        if "barchart" not in config_data["providers"]:
            config_data["providers"]["barchart"] = {}
        if "ibkr" not in config_data["providers"]:
            config_data["providers"]["ibkr"] = {}
    
    def _apply_general_env_overrides(
        self, 
        config_data: Dict[str, Any], 
        settings: VortexSettings
    ) -> None:
        """Apply general environment variable overrides."""
        override = EnvironmentOverride(config_data["general"], settings)
        
        override.apply_string_if_set("vortex_output_directory", "output_directory")
        override.apply_string_if_set("vortex_log_level", "log_level")
        override.apply_if_set("vortex_backup_enabled", "backup_enabled")
        override.apply_if_set("vortex_dry_run", "dry_run")
        override.apply_string_if_set("vortex_default_provider", "default_provider")
    
    def _apply_logging_env_overrides(self, config_data: Dict[str, Any], settings: VortexSettings) -> None:
        """Apply logging environment variable overrides."""
        if "logging" not in config_data["general"]:
            config_data["general"]["logging"] = {}
        
        logging_config = config_data["general"]["logging"]
        
        if settings.vortex_logging_level:
            logging_config["level"] = settings.vortex_logging_level
        if settings.vortex_logging_format:
            logging_config["format"] = settings.vortex_logging_format
        if settings.vortex_logging_output:
            # Parse comma-separated outputs
            outputs = [o.strip() for o in settings.vortex_logging_output.split(",")]
            logging_config["output"] = outputs
        if settings.vortex_logging_file_path:
            logging_config["file_path"] = settings.vortex_logging_file_path
    
    def _apply_provider_env_overrides(self, config_data: Dict[str, Any], settings: VortexSettings) -> None:
        """Apply provider-specific environment variable overrides."""
        self._apply_barchart_env_overrides(config_data, settings)
        self._apply_ibkr_env_overrides(config_data, settings)
    
    def _apply_barchart_env_overrides(self, config_data: Dict[str, Any], settings: VortexSettings) -> None:
        """Apply Barchart provider environment variable overrides."""
        barchart_config = config_data["providers"]["barchart"]
        
        if settings.vortex_barchart_username:
            barchart_config["username"] = settings.vortex_barchart_username
        if settings.vortex_barchart_password:
            barchart_config["password"] = settings.vortex_barchart_password
        if settings.vortex_barchart_daily_limit:
            barchart_config["daily_limit"] = settings.vortex_barchart_daily_limit
    
    def _apply_ibkr_env_overrides(self, config_data: Dict[str, Any], settings: VortexSettings) -> None:
        """Apply IBKR provider environment variable overrides."""
        ibkr_config = config_data["providers"]["ibkr"]
        
        if settings.vortex_ibkr_host:
            ibkr_config["host"] = settings.vortex_ibkr_host
        if settings.vortex_ibkr_port:
            ibkr_config["port"] = settings.vortex_ibkr_port
        if settings.vortex_ibkr_client_id:
            ibkr_config["client_id"] = settings.vortex_ibkr_client_id
    
    def _remove_none_values(self, data):
        """Recursively remove None values from dictionary to avoid TOML serialization issues."""
        if isinstance(data, dict):
            return {k: self._remove_none_values(v) for k, v in data.items() if v is not None}
        elif isinstance(data, list):
            return [self._remove_none_values(item) for item in data if item is not None]
        else:
            return data
    
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
        
        # Remove None values to avoid TOML serialization issues
        config_dict = self._remove_none_values(config_dict)
        
        def write_toml_content(f):
            tomli_w.dump(config_dict, f)
        
        FileOperationHandler.safe_file_operation(
            file_path=self.config_file,
            operation=write_toml_content,
            mode='wb',
            file_type="configuration file",
            operation_name="write"
        )
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        config = self.load_config()
        provider_configs = {
            "barchart": config.providers.barchart,
            "yahoo": config.providers.yahoo,
            "ibkr": config.providers.ibkr
        }
        
        provider_config = provider_configs.get(provider)
        if provider_config:
            return provider_config.model_dump()
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
        except (ValueError, TypeError) as e:
            raise ConfigurationValidationError([f"Invalid {provider} configuration values: {e}"])
        except Exception as e:
            raise ConfigurationValidationError([f"Unexpected error configuring {provider}: {e}"])
        
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
    
    def import_config(self, file_path: Path) -> VortexConfig:
        """Import configuration from another TOML file."""
        if not file_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {file_path}",
                help_text="Check that the file path is correct"
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
            
            return imported_config
            
        except (FileNotFoundError, PermissionError) as e:
            raise ConfigurationError(
                f"Cannot access configuration file: {file_path}",
                help_text="Check file permissions and path"
            )
        except (ValueError, TypeError) as e:
            raise ConfigurationValidationError([f"Invalid configuration format: {e}"])
        except Exception as e:
            raise ConfigurationValidationError([f"Failed to import configuration: {e}"])
    
    def export_config(self, file_path: Path) -> None:
        """Export current configuration to a TOML file."""
        config = self.load_config()
        
        # Ensure target directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary for serialization
        config_dict = config.model_dump(exclude_unset=False, mode='json')
        
        # Filter out None values (not TOML serializable)
        config_dict = self._filter_none_values(config_dict)
        
        # Convert Path objects to strings
        if 'general' in config_dict and 'output_directory' in config_dict['general']:
            config_dict['general']['output_directory'] = str(config_dict['general']['output_directory'])
        
        def write_export_toml(f):
            tomli_w.dump(config_dict, f)
        
        FileOperationHandler.safe_file_operation(
            file_path=file_path,
            operation=write_export_toml,
            mode='wb',
            file_type="export file",
            operation_name="write"
        )
    
    def _filter_none_values(self, data: Any) -> Any:
        """Recursively filter out None values from nested dictionaries."""
        if isinstance(data, dict):
            return {k: self._filter_none_values(v) for k, v in data.items() if v is not None}
        elif isinstance(data, list):
            return [self._filter_none_values(item) for item in data if item is not None]
        else:
            return data
    
    def reset_config(self) -> None:
        """Reset configuration to defaults."""
        self._config = VortexConfig()
        self.save_config()
    
