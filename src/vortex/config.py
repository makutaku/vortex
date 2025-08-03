"""
Unified Configuration Management for Vortex

This module provides a comprehensive configuration system using Pydantic for validation,
supporting both TOML files and environment variables with proper schema validation
and migration utilities.

Example configuration file (~/.config/vortex/config.toml):
    [general]
    output_directory = "./data"
    log_level = "INFO"
    backup_enabled = true
    
    [providers.barchart]
    username = "your_email@example.com"
    password = "your_password"
    daily_limit = 150
    
    [providers.yahoo]
    # No configuration required
    
    [providers.ibkr]
    host = "localhost"
    port = 7497
    client_id = 1
"""

import os
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
except ImportError:
    tomllib = None

import tomli_w

from .exceptions import (
    ConfigurationError, 
    InvalidConfigurationError, 
    MissingConfigurationError,
    ConfigurationValidationError
)


class LogLevel(str, Enum):
    """Valid logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Provider(str, Enum):
    """Supported data providers."""
    BARCHART = "barchart"
    YAHOO = "yahoo"
    IBKR = "ibkr"


class BarchartConfig(BaseModel):
    """Barchart provider configuration."""
    username: Optional[str] = Field(None, description="Barchart username")
    password: Optional[str] = Field(None, description="Barchart password")
    daily_limit: int = Field(150, ge=1, le=1000, description="Daily download limit")
    
    @field_validator('username', 'password')
    @classmethod
    def validate_credentials(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            return None
        return v
    
    @model_validator(mode='after')
    def validate_credentials_together(self) -> 'BarchartConfig':
        if (self.username is None) != (self.password is None):
            raise ValueError("Both username and password must be provided together")
        return self


class YahooConfig(BaseModel):
    """Yahoo Finance provider configuration."""
    # No configuration required for Yahoo Finance
    enabled: bool = Field(True, description="Enable Yahoo Finance provider")


class IBKRConfig(BaseModel):
    """Interactive Brokers provider configuration."""
    host: str = Field("localhost", description="TWS/Gateway host")
    port: int = Field(7497, ge=1, le=65535, description="TWS/Gateway port")
    client_id: int = Field(1, ge=0, le=999, description="Client ID")
    timeout: int = Field(30, ge=1, le=300, description="Connection timeout in seconds")


class ProvidersConfig(BaseModel):
    """Configuration for all data providers."""
    barchart: BarchartConfig = Field(default_factory=BarchartConfig)
    yahoo: YahooConfig = Field(default_factory=YahooConfig)  
    ibkr: IBKRConfig = Field(default_factory=IBKRConfig)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    format: str = Field("console", description="Log format: console, json, rich")
    output: List[str] = Field(["console"], description="Log outputs: console, file")
    file_path: Optional[Path] = Field(None, description="Log file path")
    max_file_size: int = Field(
        10 * 1024 * 1024, 
        ge=1024, 
        description="Maximum log file size in bytes"
    )
    backup_count: int = Field(
        5, 
        ge=1, 
        le=20, 
        description="Number of backup log files to keep"
    )
    
    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in ["console", "json", "rich"]:
            raise ValueError("format must be one of: console, json, rich")
        return v
    
    @field_validator('output')
    @classmethod
    def validate_output(cls, v: List[str]) -> List[str]:
        valid_outputs = {"console", "file"}
        for output in v:
            if output not in valid_outputs:
                raise ValueError(f"output must contain only: {', '.join(valid_outputs)}")
        return v


class GeneralConfig(BaseModel):
    """General application configuration."""
    output_directory: Path = Field(
        Path("./data"), 
        description="Directory for downloaded data files"
    )
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level (deprecated, use logging.level)")
    logging: LoggingConfig = Field(default_factory=LoggingConfig, description="Logging configuration")
    backup_enabled: bool = Field(False, description="Enable Parquet backup files")
    force_backup: bool = Field(False, description="Force backup even if files exist")
    dry_run: bool = Field(False, description="Perform dry run without downloading")
    random_sleep_max: int = Field(
        10, 
        ge=0, 
        le=300, 
        description="Maximum random sleep between requests (seconds)"
    )
    
    @model_validator(mode='after')
    def sync_log_levels(self) -> 'GeneralConfig':
        """Sync deprecated log_level with new logging.level."""
        # If logging.level is default but log_level is set, use log_level
        if (self.logging.level == LogLevel.INFO and 
            self.log_level != LogLevel.INFO):
            self.logging.level = self.log_level
        # If both are set and different, prefer logging.level
        elif (self.logging.level != LogLevel.INFO and 
              self.log_level != LogLevel.INFO and 
              self.logging.level != self.log_level):
            self.log_level = self.logging.level
        return self
    
    @field_validator('output_directory')
    @classmethod
    def validate_output_directory(cls, v: Path) -> Path:
        """Validate and create output directory if needed."""
        if isinstance(v, str):
            v = Path(v)
        
        # Expand user home directory
        v = v.expanduser()
        
        # Make path absolute
        if not v.is_absolute():
            v = Path.cwd() / v
            
        return v


class DateRangeConfig(BaseModel):
    """Date range configuration for downloads."""
    start_year: int = Field(
        2000, 
        ge=1980, 
        le=datetime.now().year + 1,
        description="Default start year for downloads"
    )
    end_year: int = Field(
        datetime.now().year,
        ge=1980,
        le=datetime.now().year + 10,
        description="Default end year for downloads"
    )
    
    @model_validator(mode='after')
    def validate_date_range(self) -> 'DateRangeConfig':
        if self.start_year >= self.end_year:
            raise ValueError(f"start_year ({self.start_year}) must be less than end_year ({self.end_year})")
        return self


class VortexConfig(BaseModel):
    """Main Vortex configuration model."""
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    date_range: DateRangeConfig = Field(default_factory=DateRangeConfig)
    
    model_config = {
        "extra": "forbid",  # Don't allow extra fields
        "validate_assignment": True,  # Validate on assignment
        "str_strip_whitespace": True,  # Strip whitespace from strings
    }


class VortexSettings(BaseSettings):
    """Settings that can be overridden by environment variables."""
    
    # General settings
    vortex_output_directory: Optional[str] = Field(None, alias="VORTEX_OUTPUT_DIR")
    vortex_log_level: Optional[str] = Field(None, alias="VORTEX_LOG_LEVEL")
    vortex_backup_enabled: Optional[bool] = Field(None, alias="VORTEX_BACKUP_ENABLED")
    vortex_dry_run: Optional[bool] = Field(None, alias="VORTEX_DRY_RUN")
    
    # Logging settings
    vortex_logging_level: Optional[str] = Field(None, alias="VORTEX_LOGGING_LEVEL")
    vortex_logging_format: Optional[str] = Field(None, alias="VORTEX_LOGGING_FORMAT")
    vortex_logging_output: Optional[str] = Field(None, alias="VORTEX_LOGGING_OUTPUT")
    vortex_logging_file_path: Optional[str] = Field(None, alias="VORTEX_LOGGING_FILE_PATH")
    
    # Barchart settings
    vortex_barchart_username: Optional[str] = Field(None, alias="VORTEX_BARCHART_USERNAME")
    vortex_barchart_password: Optional[str] = Field(None, alias="VORTEX_BARCHART_PASSWORD")
    vortex_barchart_daily_limit: Optional[int] = Field(None, alias="VORTEX_BARCHART_DAILY_LIMIT")
    
    # IBKR settings
    vortex_ibkr_host: Optional[str] = Field(None, alias="VORTEX_IBKR_HOST")
    vortex_ibkr_port: Optional[int] = Field(None, alias="VORTEX_IBKR_PORT")
    vortex_ibkr_client_id: Optional[int] = Field(None, alias="VORTEX_IBKR_CLIENT_ID")
    
    # Legacy environment variables for backward compatibility
    bcu_output_dir: Optional[str] = Field(None, alias="BCU_OUTPUT_DIR")
    bcu_username: Optional[str] = Field(None, alias="BCU_USERNAME") 
    bcu_password: Optional[str] = Field(None, alias="BCU_PASSWORD")
    bcu_logging_level: Optional[str] = Field(None, alias="BCU_LOGGING_LEVEL")
    bcu_dry_run: Optional[bool] = Field(None, alias="BCU_DRY_RUN")
    bcu_backup_data: Optional[bool] = Field(None, alias="BCU_BACKUP_DATA")
    bcu_provider_host: Optional[str] = Field(None, alias="BCU_PROVIDER_HOST")
    bcu_provider_port: Optional[int] = Field(None, alias="BCU_PROVIDER_PORT")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


class ConfigManager:
    """Unified configuration manager with validation and migration support."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to custom config file. If None, uses default location.
        """
        if config_file:
            self.config_file = Path(config_file)
        else:
            # Use standard user config directory
            config_dir = Path.home() / ".config" / "vortex"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "config.toml"
        
        self._config: Optional[VortexConfig] = None
        self._settings = VortexSettings()
    
    @property
    def config_directory(self) -> Path:
        """Get the configuration directory."""
        return self.config_file.parent
    
    def load_config(self) -> VortexConfig:
        """Load and validate configuration from file and environment."""
        if self._config is not None:
            return self._config
        
        # Start with defaults
        config_data = {}
        
        # Load from TOML file if it exists
        if self.config_file.exists():
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
        
        # Apply legacy environment variables for backward compatibility
        if self._settings.bcu_output_dir:
            config_data["general"]["output_directory"] = self._settings.bcu_output_dir
        if self._settings.bcu_logging_level:
            config_data["general"]["log_level"] = self._settings.bcu_logging_level
        if self._settings.bcu_dry_run is not None:
            config_data["general"]["dry_run"] = self._settings.bcu_dry_run
        if self._settings.bcu_backup_data is not None:
            config_data["general"]["backup_enabled"] = self._settings.bcu_backup_data
        
        if self._settings.bcu_username:
            config_data["providers"]["barchart"]["username"] = self._settings.bcu_username
        if self._settings.bcu_password:
            config_data["providers"]["barchart"]["password"] = self._settings.bcu_password
        
        if self._settings.bcu_provider_host:
            config_data["providers"]["ibkr"]["host"] = self._settings.bcu_provider_host
        if self._settings.bcu_provider_port:
            config_data["providers"]["ibkr"]["port"] = self._settings.bcu_provider_port
        
        return config_data
    
    def save_config(self, config: Optional[VortexConfig] = None) -> None:
        """Save configuration to TOML file."""
        if config is None:
            config = self.load_config()
        
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
    
    def migrate_legacy_config(self) -> bool:
        """Migrate from legacy BCU environment variables.
        
        Returns:
            True if migration was performed, False if no legacy config found.
        """
        migrated = False
        
        # Check if any legacy environment variables exist
        legacy_vars = [
            "BCU_USERNAME", "BCU_PASSWORD", "BCU_OUTPUT_DIR", 
            "BCU_LOGGING_LEVEL", "BCU_DRY_RUN", "BCU_BACKUP_DATA",
            "BCU_PROVIDER_HOST", "BCU_PROVIDER_PORT"
        ]
        
        has_legacy = any(os.getenv(var) for var in legacy_vars)
        
        if has_legacy and not self.config_file.exists():
            # Create new config from legacy environment variables
            config = self.load_config()  # This will apply legacy env vars
            self.save_config(config)
            migrated = True
        
        return migrated