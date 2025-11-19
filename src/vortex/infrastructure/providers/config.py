"""
Provider-specific configuration classes.

This module defines configuration dataclasses for all data providers,
eliminating hardcoded values and providing type-safe configuration.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class BarchartProviderConfig:
    """Configuration for Barchart data provider."""

    # Authentication
    username: str
    password: str

    # Rate limiting
    daily_limit: int = 150

    # Network timeouts
    request_timeout: int = 30
    download_timeout: int = 60
    login_timeout: int = 30

    # Retry configuration
    max_retries: int = 3
    retry_backoff_factor: float = 2.0

    # URLs
    base_url: str = "https://www.barchart.com"
    login_url: str = "https://www.barchart.com/login"
    logout_url: str = "https://www.barchart.com/logout"
    download_endpoint: str = "/my/download"

    # Data validation
    min_required_data_points: int = 1
    max_bars_per_download: int = 10000

    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_recovery_timeout: int = 60
    circuit_breaker_success_threshold: int = 2

    def validate(self) -> bool:
        """Validate configuration parameters."""
        return all(
            [
                self.username and self.username.strip(),
                self.password and self.password.strip(),
                self.request_timeout > 0,
                self.download_timeout > 0,
                self.max_retries >= 0,
                self.daily_limit > 0,
                # Fixed: Add validation for data validation parameters
                self.min_required_data_points > 0,
                self.max_bars_per_download > 0,
            ]
        )

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None
    ) -> "BarchartProviderConfig":
        """Create configuration from dictionary with optional overrides."""
        config_data = data.copy()
        if overrides:
            config_data.update(overrides)

        # Map config keys to expected parameter names
        mapped_data = {
            "username": config_data.get("username"),
            "password": config_data.get("password"),
            "daily_limit": config_data.get("daily_limit", 150),
            "request_timeout": config_data.get("request_timeout", 30),
            "download_timeout": config_data.get("download_timeout", 60),
            "max_retries": config_data.get("max_retries", 3),
        }

        return cls(**{k: v for k, v in mapped_data.items() if v is not None})


@dataclass
class YahooProviderConfig:
    """Configuration for Yahoo Finance provider."""

    # Cache settings
    cache_enabled: bool = True
    cache_directory: Optional[str] = None
    cache_ttl_hours: int = 24

    # Network timeouts
    request_timeout: int = 30

    # Retry configuration
    max_retries: int = 3
    retry_backoff_factor: float = 1.5

    # Data validation
    validate_data_types: bool = True
    repair_data: bool = True

    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 30
    circuit_breaker_success_threshold: int = 2

    # Rate limiting (Yahoo has implicit limits)
    rate_limit_delay: float = 0.1

    def validate(self) -> bool:
        """Validate configuration parameters."""
        return all(
            [
                self.request_timeout > 0,
                self.max_retries >= 0,
                self.cache_ttl_hours > 0,
                self.rate_limit_delay >= 0,
            ]
        )

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None
    ) -> "YahooProviderConfig":
        """Create configuration from dictionary with optional overrides."""
        config_data = data.copy()
        if overrides:
            config_data.update(overrides)

        return cls(
            cache_enabled=config_data.get("cache_enabled", True),
            cache_directory=config_data.get("cache_directory"),
            request_timeout=config_data.get("request_timeout", 30),
            max_retries=config_data.get("max_retries", 3),
            validate_data_types=config_data.get("validate_data_types", True),
        )


@dataclass
class IBKRProviderConfig:
    """Configuration for Interactive Brokers provider."""

    # Connection settings
    host: str = "localhost"
    port: int = 7497
    client_id: Optional[int] = None

    # Connection timeouts
    connection_timeout: int = 30
    historical_data_timeout: int = 120

    # Retry configuration
    max_retries: int = 3
    retry_backoff_factor: float = 2.0

    # Data settings
    use_rth_only: bool = True  # Regular Trading Hours only
    market_data_type: int = 3  # Delayed data

    # Circuit breaker settings
    circuit_breaker_failure_threshold: int = 3
    circuit_breaker_recovery_timeout: int = 90
    circuit_breaker_success_threshold: int = 2

    # Connection stability
    heartbeat_interval: int = 60
    max_idle_time: int = 300

    def validate(self) -> bool:
        """Validate configuration parameters."""
        return all(
            [
                self.host and self.host.strip(),
                isinstance(self.port, int) and 1 <= self.port <= 65535,
                self.connection_timeout > 0,
                self.historical_data_timeout > 0,
                self.max_retries >= 0,
            ]
        )

    @classmethod
    def from_dict(
        cls, data: Dict[str, Any], overrides: Optional[Dict[str, Any]] = None
    ) -> "IBKRProviderConfig":
        """Create configuration from dictionary with optional overrides."""
        config_data = data.copy()
        if overrides:
            config_data.update(overrides)

        return cls(
            host=config_data.get("host", "localhost"),
            port=config_data.get("port", 7497),
            client_id=config_data.get("client_id"),
            connection_timeout=config_data.get("connection_timeout", 30),
            max_retries=config_data.get("max_retries", 3),
        )


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration for providers."""

    failure_threshold: int = 3
    recovery_timeout: int = 60
    success_threshold: int = 2
    monitored_exceptions: tuple = field(default_factory=lambda: (Exception,))
    half_open_max_calls: int = 1

    def validate(self) -> bool:
        """Validate circuit breaker configuration."""
        return all(
            [
                self.failure_threshold > 0,
                self.recovery_timeout > 0,
                self.success_threshold > 0,
                self.half_open_max_calls > 0,
            ]
        )


@dataclass
class ObservabilityConfig:
    """Observability configuration for providers."""

    # Logging
    log_level: str = "INFO"
    enable_correlation_ids: bool = True
    enable_performance_logging: bool = True

    # Metrics
    enable_metrics: bool = True
    metrics_prefix: str = "vortex.provider"

    # Health checks
    enable_health_checks: bool = True
    health_check_interval: int = 60

    def validate(self) -> bool:
        """Validate observability configuration."""
        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        return all(
            [self.log_level.upper() in valid_log_levels, self.health_check_interval > 0]
        )
