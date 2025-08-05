"""
Configuration models for Vortex.

This module defines Pydantic-based configuration models that provide
validation, type safety, and documentation for all Vortex configuration.
Consolidated from the original config.py file.
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
    default_provider: Provider = Field(
        Provider.YAHOO, 
        description="Default data provider (yahoo is free and requires no setup)"
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
    vortex_default_provider: Optional[str] = Field(None, alias="VORTEX_DEFAULT_PROVIDER")
    
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )