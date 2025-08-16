"""
Provider builder patterns for comprehensive dependency injection.

This module implements builder patterns for all data providers,
enabling flexible configuration and dependency injection.
"""

from typing import Optional, Type
from abc import ABC, abstractmethod

from .config import BarchartProviderConfig, YahooProviderConfig, IBKRProviderConfig
from ..resilience.circuit_breaker import CircuitBreakerConfig
from .interfaces import HTTPClientProtocol, CacheManagerProtocol, DataFetcherProtocol, ConnectionManagerProtocol
from vortex.infrastructure.storage.raw_storage import RawDataStorage
from .barchart import BarchartDataProvider
from .yahoo import YahooDataProvider  
from .ibkr import IbkrDataProvider
from vortex.infrastructure.resilience.circuit_breaker import get_circuit_breaker


class ProviderBuilder(ABC):
    """Abstract base class for provider builders."""
    
    @abstractmethod
    def build(self):
        """Build and return the configured provider instance."""
        pass
    
    @abstractmethod
    def reset(self):
        """Reset builder to initial state."""
        pass


class BarchartProviderBuilder(ProviderBuilder):
    """Builder for Barchart data provider with comprehensive dependency injection."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to initial state."""
        self._config: Optional[BarchartProviderConfig] = None
        self._auth_handler = None
        self._http_client: Optional[HTTPClientProtocol] = None
        self._parser = None
        self._circuit_breaker_config: Optional[CircuitBreakerConfig] = None
        self._raw_storage: Optional[RawDataStorage] = None
        return self
    
    def with_config(self, config: BarchartProviderConfig):
        """Set provider configuration."""
        if not config.validate():
            raise ValueError("Invalid Barchart provider configuration")
        self._config = config
        return self
    
    def with_credentials(self, username: str, password: str):
        """Set credentials (alternative to full config)."""
        if not self._config:
            self._config = BarchartProviderConfig(username=username, password=password)
        else:
            self._config.username = username
            self._config.password = password
        return self
    
    def with_auth_handler(self, auth_handler):
        """Inject custom authentication handler."""
        self._auth_handler = auth_handler
        return self
    
    def with_http_client(self, http_client: HTTPClientProtocol):
        """Inject custom HTTP client."""
        self._http_client = http_client
        return self
    
    def with_parser(self, parser):
        """Inject custom parser."""
        self._parser = parser
        return self
    
    def with_circuit_breaker_config(self, config: CircuitBreakerConfig):
        """Configure circuit breaker settings."""
        self._circuit_breaker_config = config
        return self
    
    def with_raw_storage(self, raw_storage: RawDataStorage):
        """Inject raw data storage for data trail."""
        self._raw_storage = raw_storage
        return self
    
    def with_timeouts(self, request_timeout: int = 30, download_timeout: int = 60):
        """Configure timeout settings."""
        if self._config:
            self._config.request_timeout = request_timeout
            self._config.download_timeout = download_timeout
        return self
    
    def with_rate_limiting(self, daily_limit: int = 150, max_retries: int = 3):
        """Configure rate limiting settings."""
        if self._config:
            self._config.daily_limit = daily_limit
            self._config.max_retries = max_retries
        return self
    
    def build(self) -> BarchartDataProvider:
        """Build configured Barchart provider."""
        if not self._config:
            raise ValueError("Configuration is required for Barchart provider")
        
        # Import here to avoid circular imports
        from .barchart.auth import BarchartAuth
        from .barchart.client import BarchartClient
        from .barchart.parser import BarchartParser
        from .interfaces import BarchartHTTPClient
        
        # Create dependencies if not injected
        auth = self._auth_handler or BarchartAuth(self._config.username, self._config.password)
        http_client = self._http_client or BarchartHTTPClient(auth.session)
        parser = self._parser or BarchartParser()
        
        # Create circuit breaker configuration
        cb_config = self._circuit_breaker_config or CircuitBreakerConfig(
            failure_threshold=self._config.circuit_breaker_failure_threshold,
            recovery_timeout=self._config.circuit_breaker_recovery_timeout,
            success_threshold=self._config.circuit_breaker_success_threshold
        )
        
        # Create provider with injected dependencies
        provider = BarchartDataProvider(
            config=self._config,
            auth_handler=auth,
            http_client=http_client,
            parser=parser,
            circuit_breaker_config=cb_config,
            raw_storage=self._raw_storage
        )
        
        return provider


class YahooProviderBuilder(ProviderBuilder):
    """Builder for Yahoo Finance provider with dependency injection."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to initial state."""
        self._config: Optional[YahooProviderConfig] = None
        self._cache_manager: Optional[CacheManagerProtocol] = None
        self._data_fetcher: Optional[DataFetcherProtocol] = None
        self._circuit_breaker_config: Optional[CircuitBreakerConfig] = None
        self._raw_storage: Optional[RawDataStorage] = None
        return self
    
    def with_config(self, config: YahooProviderConfig):
        """Set provider configuration."""
        if not config.validate():
            raise ValueError("Invalid Yahoo provider configuration")
        self._config = config
        return self
    
    def with_cache_manager(self, cache_manager: CacheManagerProtocol):
        """Inject custom cache manager."""
        self._cache_manager = cache_manager
        return self
    
    def with_data_fetcher(self, data_fetcher: DataFetcherProtocol):
        """Inject custom data fetcher."""
        self._data_fetcher = data_fetcher
        return self
    
    def with_circuit_breaker_config(self, config: CircuitBreakerConfig):
        """Configure circuit breaker settings."""
        self._circuit_breaker_config = config
        return self
    
    def with_cache_settings(self, cache_enabled: bool = True, cache_ttl_hours: int = 24):
        """Configure cache settings."""
        if not self._config:
            self._config = YahooProviderConfig()
        self._config.cache_enabled = cache_enabled
        self._config.cache_ttl_hours = cache_ttl_hours
        return self
    
    def with_validation_settings(self, validate_data_types: bool = True, repair_data: bool = True):
        """Configure data validation settings."""
        if not self._config:
            self._config = YahooProviderConfig()
        self._config.validate_data_types = validate_data_types
        self._config.repair_data = repair_data
        return self
    
    def with_raw_storage(self, raw_storage: RawDataStorage):
        """Inject raw data storage for data trail."""
        self._raw_storage = raw_storage
        return self
    
    def build(self) -> YahooDataProvider:
        """Build configured Yahoo provider."""
        # Use default config if none provided
        config = self._config or YahooProviderConfig()
        
        # Import here to avoid circular imports
        from .interfaces import YahooCacheManager, YahooDataFetcher
        
        # Create dependencies if not injected
        cache_manager = self._cache_manager or (YahooCacheManager() if config.cache_enabled else None)
        data_fetcher = self._data_fetcher or YahooDataFetcher()
        
        # Create circuit breaker configuration
        cb_config = self._circuit_breaker_config or CircuitBreakerConfig(
            failure_threshold=config.circuit_breaker_failure_threshold,
            recovery_timeout=config.circuit_breaker_recovery_timeout,
            success_threshold=config.circuit_breaker_success_threshold
        )
        
        # Create provider with injected dependencies
        provider = YahooDataProvider(
            config=config,
            cache_manager=cache_manager,
            data_fetcher=data_fetcher,
            circuit_breaker_config=cb_config,
            raw_storage=self._raw_storage
        )
        
        return provider


class IBKRProviderBuilder(ProviderBuilder):
    """Builder for Interactive Brokers provider with dependency injection."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to initial state."""
        self._config: Optional[IBKRProviderConfig] = None
        self._connection_manager: Optional[ConnectionManagerProtocol] = None
        self._circuit_breaker_config: Optional[CircuitBreakerConfig] = None
        self._raw_storage: Optional[RawDataStorage] = None
        return self
    
    def with_config(self, config: IBKRProviderConfig):
        """Set provider configuration."""
        if not config.validate():
            raise ValueError("Invalid IBKR provider configuration")
        self._config = config
        return self
    
    def with_connection_settings(self, host: str = "localhost", port: int = 7497, client_id: Optional[int] = None):
        """Configure connection settings."""
        if not self._config:
            self._config = IBKRProviderConfig()
        self._config.host = host
        self._config.port = port
        self._config.client_id = client_id
        return self
    
    def with_connection_manager(self, connection_manager: ConnectionManagerProtocol):
        """Inject custom connection manager."""
        self._connection_manager = connection_manager
        return self
    
    def with_circuit_breaker_config(self, config: CircuitBreakerConfig):
        """Configure circuit breaker settings."""
        self._circuit_breaker_config = config
        return self
    
    def with_raw_storage(self, raw_storage: RawDataStorage):
        """Inject raw data storage for data trail."""
        self._raw_storage = raw_storage
        return self
    
    def with_timeout_settings(self, connection_timeout: int = 30, data_timeout: int = 120):
        """Configure timeout settings."""
        if not self._config:
            self._config = IBKRProviderConfig()
        self._config.connection_timeout = connection_timeout
        self._config.historical_data_timeout = data_timeout
        return self
    
    def with_data_settings(self, use_rth_only: bool = True, market_data_type: int = 3):
        """Configure data retrieval settings."""
        if not self._config:
            self._config = IBKRProviderConfig()
        self._config.use_rth_only = use_rth_only
        self._config.market_data_type = market_data_type
        return self
    
    def build(self) -> IbkrDataProvider:
        """Build configured IBKR provider."""
        # Use default config if none provided
        config = self._config or IBKRProviderConfig()
        
        # Import here to avoid circular imports
        from .interfaces import IBKRConnectionManager
        from ib_insync import IB
        
        # Create dependencies if not injected
        if not self._connection_manager:
            ib_client = IB()
            self._connection_manager = IBKRConnectionManager(
                ib_client, config.host, config.port, config.client_id or 1
            )
        
        # Create circuit breaker configuration
        cb_config = self._circuit_breaker_config or CircuitBreakerConfig(
            failure_threshold=config.circuit_breaker_failure_threshold,
            recovery_timeout=config.circuit_breaker_recovery_timeout,
            success_threshold=config.circuit_breaker_success_threshold
        )
        
        # Create provider with injected dependencies
        provider = IbkrDataProvider(
            config=config,
            connection_manager=self._connection_manager,
            circuit_breaker_config=cb_config,
            raw_storage=self._raw_storage
        )
        
        return provider


# Factory functions for convenient builder creation
def barchart_builder() -> BarchartProviderBuilder:
    """Create a new Barchart provider builder."""
    return BarchartProviderBuilder()


def yahoo_builder() -> YahooProviderBuilder:
    """Create a new Yahoo provider builder."""
    return YahooProviderBuilder()


def ibkr_builder() -> IBKRProviderBuilder:
    """Create a new IBKR provider builder."""
    return IBKRProviderBuilder()


# Fluent interface examples
def create_barchart_provider_with_defaults(username: str, password: str) -> BarchartDataProvider:
    """Create a Barchart provider with sensible defaults."""
    return (barchart_builder()
            .with_credentials(username, password)
            .with_timeouts(request_timeout=30, download_timeout=60)
            .with_rate_limiting(daily_limit=150, max_retries=3)
            .build())


def create_yahoo_provider_with_caching() -> YahooDataProvider:
    """Create a Yahoo provider with caching enabled."""
    return (yahoo_builder()
            .with_cache_settings(cache_enabled=True, cache_ttl_hours=24)
            .with_validation_settings(validate_data_types=True, repair_data=True)
            .build())


def create_ibkr_provider_with_connection(host: str = "localhost", port: int = 7497) -> IbkrDataProvider:
    """Create an IBKR provider with connection settings."""
    return (ibkr_builder()
            .with_connection_settings(host=host, port=port)
            .with_timeout_settings(connection_timeout=30, data_timeout=120)
            .build())