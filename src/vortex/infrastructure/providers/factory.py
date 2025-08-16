"""
Provider factory with dependency injection support.

This module implements a factory pattern with proper dependency injection
for creating data provider instances.
"""

from typing import Any, Callable, Dict, Optional, Type

from vortex.core.config import ConfigManager
from vortex.exceptions.plugins import PluginNotFoundError
from vortex.infrastructure.providers.protocol import DataProviderProtocol
from vortex.infrastructure.storage.raw_storage import RawDataStorage

from .barchart import BarchartDataProvider
from .yahoo import YahooDataProvider
from .ibkr import IbkrDataProvider
from .config import BarchartProviderConfig, YahooProviderConfig, IBKRProviderConfig, CircuitBreakerConfig
from .builders import BarchartProviderBuilder, YahooProviderBuilder, IBKRProviderBuilder
from .interfaces import (
    CacheManagerProtocol, DataFetcherProtocol, ConnectionManagerProtocol, HTTPClientProtocol,
    YahooCacheManager, YahooDataFetcher, IBKRConnectionManager, BarchartHTTPClient,
    create_yahoo_cache_manager, create_yahoo_data_fetcher, 
    create_ibkr_connection_manager, create_barchart_http_client
)


class ProviderFactory:
    """Enhanced factory for creating data provider instances with comprehensive DI support."""
    
    def __init__(self, 
                 config_manager: Optional[ConfigManager] = None,
                 raw_storage: Optional[RawDataStorage] = None):
        """Initialize the factory with optional configuration manager and raw data storage.
        
        Args:
            config_manager: Configuration manager for provider settings
            raw_storage: Raw data storage for data trail
        """
        self.config_manager = config_manager or ConfigManager()
        self.raw_storage = raw_storage or self._create_raw_storage_from_config()
        self._providers: Dict[str, Type[DataProviderProtocol]] = {
            'barchart': BarchartDataProvider,
            'yahoo': YahooDataProvider,
            'ibkr': IbkrDataProvider,
        }
        self._provider_builders: Dict[str, Callable] = {
            'barchart': self._build_barchart_provider,
            'yahoo': self._build_yahoo_provider,
            'ibkr': self._build_ibkr_provider,
        }
        self._builder_classes: Dict[str, Type] = {
            'barchart': BarchartProviderBuilder,
            'yahoo': YahooProviderBuilder,
            'ibkr': IBKRProviderBuilder,
        }
    
    def create_provider(
        self, 
        provider_name: str, 
        config_override: Optional[Dict[str, Any]] = None
    ) -> DataProviderProtocol:
        """Create a provider instance with proper dependency injection.
        
        Args:
            provider_name: Name of the provider to create
            config_override: Optional configuration to override defaults
            
        Returns:
            Configured provider instance
            
        Raises:
            PluginNotFoundError: If provider name is not recognized
        """
        if provider_name not in self._providers:
            raise PluginNotFoundError(
                f"Provider '{provider_name}' not found. "
                f"Available providers: {', '.join(self._providers.keys())}"
            )
        
        # Get builder for this provider
        builder = self._provider_builders[provider_name]
        
        # Build with configuration
        return builder(config_override)
    
    def get_builder(self, provider_name: str):
        """Get a fresh builder instance for the specified provider.
        
        Args:
            provider_name: Name of the provider to create builder for
            
        Returns:
            Fresh builder instance for the provider
            
        Raises:
            PluginNotFoundError: If provider name is not recognized
        """
        if provider_name not in self._builder_classes:
            raise PluginNotFoundError(
                f"Provider '{provider_name}' not found. "
                f"Available providers: {', '.join(self._builder_classes.keys())}"
            )
        
        return self._builder_classes[provider_name]()
    
    def create_provider_with_builder(self, provider_name: str, builder_config_func=None):
        """Create provider using fluent builder interface.
        
        Args:
            provider_name: Name of the provider to create
            builder_config_func: Optional function to configure the builder
            
        Returns:
            Configured provider instance
            
        Example:
            # Create Barchart provider with custom configuration
            provider = factory.create_provider_with_builder(
                'barchart', 
                lambda b: b.with_credentials('user', 'pass')
                          .with_timeouts(30, 60)
                          .with_rate_limiting(200, 3)
            )
        """
        builder = self.get_builder(provider_name)
        
        if builder_config_func:
            builder = builder_config_func(builder)
        
        return builder.build()
    
    def _build_barchart_provider(self, config_override: Optional[Dict[str, Any]] = None) -> BarchartDataProvider:
        """Build Barchart provider with enhanced configuration and dependency injection."""
        # Get base configuration from config manager
        base_config = self.config_manager.get_provider_config('barchart')
        
        # Create configuration object with overrides
        try:
            config = BarchartProviderConfig.from_dict(base_config, config_override)
        except TypeError as e:
            if "missing" in str(e) and "positional arguments" in str(e):
                raise ValueError("Missing required configuration for Barchart provider: username, password")
            raise
        
        # Use builder for complex construction
        builder = BarchartProviderBuilder()
        builder.with_config(config)
        
        # Inject raw data storage if available
        if self.raw_storage:
            builder.with_raw_storage(self.raw_storage)
        
        # Apply any injected dependencies from config_override
        if config_override:
            if 'http_client' in config_override:
                builder.with_http_client(config_override['http_client'])
            if 'auth_handler' in config_override:
                builder.with_auth_handler(config_override['auth_handler'])
            if 'parser' in config_override:
                builder.with_parser(config_override['parser'])
        
        provider = builder.build()
        
        # Perform explicit login now that provider is configured
        provider.login()
        
        return provider
    
    def _build_yahoo_provider(self, config_override: Optional[Dict[str, Any]] = None) -> YahooDataProvider:
        """Build Yahoo provider with enhanced configuration and dependency injection."""
        # Get base configuration from config manager
        base_config = self.config_manager.get_provider_config('yahoo') or {}
        
        # Create configuration object with overrides
        config = YahooProviderConfig.from_dict(base_config, config_override)
        
        # Use builder for complex construction
        builder = YahooProviderBuilder()
        builder.with_config(config)
        
        # Inject raw data storage if available
        if self.raw_storage:
            builder.with_raw_storage(self.raw_storage)
        
        # Apply any injected dependencies from config_override
        if config_override:
            if 'cache_manager' in config_override:
                builder.with_cache_manager(config_override['cache_manager'])
            if 'data_fetcher' in config_override:
                builder.with_data_fetcher(config_override['data_fetcher'])
        
        return builder.build()
    
    def _build_ibkr_provider(self, config_override: Optional[Dict[str, Any]] = None) -> IbkrDataProvider:
        """Build IBKR provider with enhanced configuration and dependency injection."""
        # Get base configuration from config manager
        base_config = self.config_manager.get_provider_config('ibkr') or {}
        
        # Create configuration object with overrides
        config = IBKRProviderConfig.from_dict(base_config, config_override)
        
        # Use builder for complex construction
        builder = IBKRProviderBuilder()
        builder.with_config(config)
        
        # Inject raw data storage if available
        if self.raw_storage:
            builder.with_raw_storage(self.raw_storage)
        
        # Apply any injected dependencies from config_override
        if config_override:
            if 'connection_manager' in config_override:
                builder.with_connection_manager(config_override['connection_manager'])
        
        provider = builder.build()
        
        # Perform explicit login now that provider is configured
        provider.login()
        
        return provider
    
    def register_provider(
        self, 
        name: str, 
        provider_class: Type[DataProviderProtocol],
        builder: Optional[Callable] = None
    ) -> None:
        """Register a new provider type with the factory.
        
        Args:
            name: Provider name
            provider_class: Provider class implementing DataProviderProtocol
            builder: Optional custom builder function
        """
        self._providers[name] = provider_class
        
        if builder:
            self._provider_builders[name] = builder
        else:
            # Default builder that passes config dictionary
            self._provider_builders[name] = lambda config: provider_class(config or {})
    
    def list_providers(self) -> list[str]:
        """Get list of available provider names."""
        return list(self._providers.keys())
    
    def get_provider_info(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a provider.
        
        Args:
            name: Provider name
            
        Returns:
            Dictionary with provider information
            
        Raises:
            PluginNotFoundError: If provider not found
        """
        if name not in self._providers:
            raise PluginNotFoundError(f"Provider '{name}' not found")
        
        # Return standardized provider information
        provider_info = {
            'barchart': {
                'class': 'BarchartDataProvider',
                'supported_assets': ['Futures', 'Options', 'Stocks'],
                'requires_auth': True,
                'description': 'Premium financial data from Barchart.com',
                'rate_limits': 'Daily limit varies by subscription',
                'required_config': ['username', 'password'],
                'optional_config': ['daily_limit']
            },
            'yahoo': {
                'class': 'YahooDataProvider',
                'supported_assets': ['Stocks', 'ETFs', 'Indices', 'Currencies'],
                'requires_auth': False,
                'description': 'Free financial data from Yahoo Finance',
                'rate_limits': 'Rate limited by Yahoo',
                'required_config': [],
                'optional_config': []
            },
            'ibkr': {
                'class': 'IbkrDataProvider',
                'supported_assets': ['Stocks', 'Futures', 'Options', 'Forex'],
                'requires_auth': True,
                'description': 'Interactive Brokers TWS/Gateway integration',
                'rate_limits': 'No specific limits',
                'required_config': ['host', 'port', 'client_id'],
                'optional_config': []
            }
        }
        
        return provider_info.get(name, {})
    
    def _create_raw_storage_from_config(self) -> Optional[RawDataStorage]:
        """Create raw data storage instance based on configuration.
        
        Returns:
            RawDataStorage instance if raw data storage is enabled, None otherwise
        """
        try:
            config = self.config_manager.load_config()
            raw_config = config.general.raw
            
            if not raw_config.enabled:
                return None
            
            # Create raw data storage with configuration
            return RawDataStorage(
                base_dir=str(config.general.raw_directory),
                enabled=raw_config.enabled,
                retention_days=raw_config.retention_days,
                compress=raw_config.compress,
                include_metadata=raw_config.include_metadata
            )
        except Exception:
            # If configuration loading fails, return None to disable raw data storage
            return None