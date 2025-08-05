"""
Base configuration schemas using Pydantic for validation.
"""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from pathlib import Path


class LoggingConfig(BaseModel):
    """Logging configuration schema."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    format: Literal["console", "json"] = "console"
    output: Literal["console", "file"] = "console"
    file_path: Optional[Path] = None
    rotation: Optional[Literal["daily", "weekly", "size"]] = None
    retention_days: Optional[int] = None

    @validator("file_path", pre=True)
    def validate_file_path(cls, v):
        if v is not None:
            return Path(v)
        return v


class GeneralConfig(BaseModel):
    """General application configuration schema."""
    output_directory: Path = Field(default=Path("./data"))
    backup_enabled: bool = True
    default_provider: Literal["barchart", "yahoo", "ibkr", "mock"] = "yahoo"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @validator("output_directory", pre=True)
    def validate_output_directory(cls, v):
        return Path(v)


class ProviderConfig(BaseModel):
    """Base provider configuration schema."""
    timeout: int = Field(default=30, ge=1, le=300)
    retry_attempts: int = Field(default=3, ge=1, le=10)
    rate_limit_delay: float = Field(default=1.0, ge=0.1, le=10.0)
    mock_responses: bool = False


class BarchartConfig(ProviderConfig):
    """Barchart provider configuration schema."""
    daily_limit: int = Field(default=150, ge=1, le=1000)
    username: Optional[str] = None
    password: Optional[str] = None


class YahooConfig(ProviderConfig):
    """Yahoo Finance provider configuration schema."""
    pass  # Uses base provider config


class IBKRConfig(ProviderConfig):
    """Interactive Brokers provider configuration schema."""
    host: str = "localhost"
    port: int = Field(default=7497, ge=1, le=65535)
    client_id: int = Field(default=1, ge=1, le=999)


class ProvidersConfig(BaseModel):
    """All providers configuration schema."""
    barchart: BarchartConfig = Field(default_factory=BarchartConfig)
    yahoo: YahooConfig = Field(default_factory=YahooConfig)
    ibkr: IBKRConfig = Field(default_factory=IBKRConfig)


class MonitoringConfig(BaseModel):
    """Monitoring and observability configuration schema."""
    enable_tracing: bool = False
    enable_metrics: bool = False
    metrics_port: int = Field(default=8080, ge=1024, le=65535)
    health_check_port: int = Field(default=8081, ge=1024, le=65535)


class EnvironmentConfig(BaseModel):
    """Base environment configuration schema."""
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    # Environment-specific sections
    development: Optional[Dict[str, Any]] = None
    production: Optional[Dict[str, Any]] = None  
    testing: Optional[Dict[str, Any]] = None
    fixtures: Optional[Dict[str, Any]] = None

    class Config:
        # Allow extra fields for environment-specific configurations
        extra = "allow"