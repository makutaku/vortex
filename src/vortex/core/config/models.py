"""
Configuration models for Vortex.

This module defines Pydantic-based configuration models that provide
validation, type safety, and documentation for all Vortex configuration.
Consolidated from the original config.py file.
"""

import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from vortex.constants import (
    DEFAULT_DAILY_LIMIT,
    DEFAULT_IBKR_PORT,
    DEFAULT_LOG_BACKUP_COUNT,
    DEFAULT_LOG_FILE_SIZE_BYTES,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_PORT_NUMBER,
    MIN_LOG_FILE_SIZE_BYTES,
)

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
    daily_limit: int = Field(
        DEFAULT_DAILY_LIMIT, ge=1, le=1000, description="Daily download limit"
    )

    @field_validator("username", "password")
    @classmethod
    def validate_credentials(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            return None
        return v

    @model_validator(mode="after")
    def validate_credentials_together(self) -> "BarchartConfig":
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
    port: int = Field(
        DEFAULT_IBKR_PORT, ge=1, le=MAX_PORT_NUMBER, description="TWS/Gateway port"
    )
    client_id: int = Field(1, ge=0, le=999, description="Client ID")
    timeout: int = Field(
        DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=300,
        description="Connection timeout in seconds",
    )


class ProvidersConfig(BaseModel):
    """Configuration for all data providers."""

    barchart: BarchartConfig = Field(default_factory=BarchartConfig)
    yahoo: YahooConfig = Field(default_factory=YahooConfig)
    ibkr: IBKRConfig = Field(default_factory=IBKRConfig)


class MetricsConfig(BaseModel):
    """Metrics configuration."""

    enabled: bool = Field(True, description="Enable Prometheus metrics collection")
    port: int = Field(8000, ge=1024, le=65535, description="Metrics server port")
    path: str = Field("/metrics", description="Metrics endpoint path")


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    format: str = Field("console", description="Log format: console, json, rich")
    output: List[str] = Field(["console"], description="Log outputs: console, file")
    file_path: Optional[Path] = Field(None, description="Log file path")
    max_file_size: int = Field(
        DEFAULT_LOG_FILE_SIZE_BYTES,
        ge=MIN_LOG_FILE_SIZE_BYTES,
        description="Maximum log file size in bytes",
    )
    backup_count: int = Field(
        DEFAULT_LOG_BACKUP_COUNT,
        ge=1,
        le=20,
        description="Number of backup log files to keep",
    )

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in ["console", "json", "rich"]:
            raise ValueError("format must be one of: console, json, rich")
        return v

    @field_validator("output")
    @classmethod
    def validate_output(cls, v: List[str]) -> List[str]:
        valid_outputs = {"console", "file"}
        for output in v:
            if output not in valid_outputs:
                raise ValueError(
                    f"output must contain only: {', '.join(valid_outputs)}"
                )
        return v


class RawConfig(BaseModel):
    """Raw data storage configuration for compliance and debugging."""

    enabled: bool = Field(
        True, description="Enable raw data storage for provider responses"
    )
    retention_days: Optional[int] = Field(
        30,
        ge=1,
        le=365,
        description="Number of days to retain raw data files (None for unlimited)",
    )
    compress: bool = Field(True, description="Compress raw data files with gzip")
    include_metadata: bool = Field(
        True, description="Include request metadata with raw data files"
    )


class GeneralConfig(BaseModel):
    """General application configuration."""

    output_directory: Path = Field(
        Path("./data"), description="Directory for downloaded data files"
    )
    raw_directory: Path = Field(
        Path("./raw"), description="Directory for raw data audit trail files"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging configuration"
    )
    metrics: MetricsConfig = Field(
        default_factory=MetricsConfig, description="Metrics configuration"
    )
    raw: RawConfig = Field(
        default_factory=RawConfig, description="Raw data storage configuration"
    )
    backup_enabled: bool = Field(False, description="Enable Parquet backup files")
    force_backup: bool = Field(False, description="Force backup even if files exist")
    dry_run: bool = Field(False, description="Perform dry run without downloading")
    random_sleep_max: int = Field(
        10, ge=0, le=300, description="Maximum random sleep between requests (seconds)"
    )
    default_provider: Provider = Field(
        Provider.YAHOO,
        description="Default data provider (yahoo is free and requires no setup)",
    )

    @field_validator("output_directory", "raw_directory")
    @classmethod
    def validate_directories(cls, v: Path) -> Path:
        """Validate and prepare directories."""
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
        description="Default start year for downloads",
    )
    end_year: int = Field(
        datetime.now().year,
        ge=1980,
        le=datetime.now().year + 10,
        description="Default end year for downloads",
    )

    @model_validator(mode="after")
    def validate_date_range(self) -> "DateRangeConfig":
        if self.start_year >= self.end_year:
            raise ValueError(
                f"start_year ({self.start_year}) must be less than end_year ({self.end_year})"
            )
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
    vortex_raw_directory: Optional[str] = Field(None, alias="VORTEX_RAW_DIR")
    vortex_log_level: Optional[str] = Field(None, alias="VORTEX_LOG_LEVEL")
    vortex_backup_enabled: Optional[bool] = Field(None, alias="VORTEX_BACKUP_ENABLED")
    vortex_dry_run: Optional[bool] = Field(None, alias="VORTEX_DRY_RUN")
    vortex_default_provider: Optional[str] = Field(
        None, alias="VORTEX_DEFAULT_PROVIDER"
    )

    # Logging settings
    vortex_logging_level: Optional[str] = Field(None, alias="VORTEX_LOGGING_LEVEL")
    vortex_logging_format: Optional[str] = Field(None, alias="VORTEX_LOGGING_FORMAT")
    vortex_logging_output: Optional[str] = Field(None, alias="VORTEX_LOGGING_OUTPUT")
    vortex_logging_file_path: Optional[str] = Field(
        None, alias="VORTEX_LOGGING_FILE_PATH"
    )

    # Barchart settings
    vortex_barchart_username: Optional[str] = Field(
        None, alias="VORTEX_BARCHART_USERNAME"
    )
    vortex_barchart_password: Optional[str] = Field(
        None, alias="VORTEX_BARCHART_PASSWORD"
    )
    vortex_barchart_daily_limit: Optional[int] = Field(
        None, alias="VORTEX_BARCHART_DAILY_LIMIT"
    )
    vortex_barchart_timeout: Optional[int] = Field(
        None, alias="VORTEX_BARCHART_TIMEOUT"
    )

    # Yahoo settings
    vortex_yahoo_timeout: Optional[int] = Field(None, alias="VORTEX_YAHOO_TIMEOUT")

    # IBKR settings
    vortex_ibkr_host: Optional[str] = Field(None, alias="VORTEX_IBKR_HOST")
    vortex_ibkr_port: Optional[int] = Field(None, alias="VORTEX_IBKR_PORT")
    vortex_ibkr_client_id: Optional[int] = Field(None, alias="VORTEX_IBKR_CLIENT_ID")
    vortex_ibkr_timeout: Optional[int] = Field(None, alias="VORTEX_IBKR_TIMEOUT")

    # Metrics settings
    vortex_metrics_enabled: Optional[bool] = Field(None, alias="VORTEX_METRICS_ENABLED")
    vortex_metrics_port: Optional[int] = Field(None, alias="VORTEX_METRICS_PORT")
    vortex_metrics_path: Optional[str] = Field(None, alias="VORTEX_METRICS_PATH")

    # Raw data storage settings
    vortex_raw_enabled: Optional[bool] = Field(None, alias="VORTEX_RAW_ENABLED")
    vortex_raw_base_directory: Optional[str] = Field(
        None, alias="VORTEX_RAW_BASE_DIRECTORY"
    )
    vortex_raw_retention_days: Optional[int] = Field(
        None, alias="VORTEX_RAW_RETENTION_DAYS"
    )
    vortex_raw_compress: Optional[bool] = Field(None, alias="VORTEX_RAW_COMPRESS")
    vortex_raw_include_metadata: Optional[bool] = Field(
        None, alias="VORTEX_RAW_INCLUDE_METADATA"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )
