"""
Provider factory with dependency injection support.

This module implements a factory pattern with proper dependency injection
for creating data provider instances.
"""

from typing import Any, Callable, Dict, Optional, Type

from vortex.core.config import ConfigManager
from vortex.exceptions.plugins import PluginNotFoundError
from vortex.infrastructure.providers.protocol import DataProviderProtocol

from .barchart import BarchartDataProvider
from .yahoo import YahooDataProvider
from .ibkr import IbkrDataProvider


class ProviderFactory:
    """Factory for creating data provider instances with dependency injection."""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """Initialize the factory with optional configuration manager.
        
        Args:
            config_manager: Configuration manager for provider settings
        """
        self.config_manager = config_manager or ConfigManager()
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
    
    def _build_barchart_provider(self, config_override: Optional[Dict[str, Any]] = None) -> BarchartDataProvider:
        """Build Barchart provider with configuration."""
        # Get base configuration from config manager
        provider_config = self.config_manager.get_provider_config('barchart')
        
        # Apply overrides if provided
        if config_override:
            provider_config.update(config_override)
        
        # Validate required fields
        required_fields = ['username', 'password']
        missing_fields = [field for field in required_fields if not provider_config.get(field)]
        
        if missing_fields:
            raise ValueError(
                f"Missing required configuration for Barchart provider: {', '.join(missing_fields)}"
            )
        
        # Create provider with injected dependencies
        return BarchartDataProvider(
            username=provider_config['username'],
            password=provider_config['password'],
            daily_download_limit=provider_config.get('daily_limit', 150)
        )
    
    def _build_yahoo_provider(self, config_override: Optional[Dict[str, Any]] = None) -> YahooDataProvider:
        """Build Yahoo provider (no configuration required)."""
        return YahooDataProvider()
    
    def _build_ibkr_provider(self, config_override: Optional[Dict[str, Any]] = None) -> IbkrDataProvider:
        """Build IBKR provider with configuration."""
        # Get base configuration from config manager
        provider_config = self.config_manager.get_provider_config('ibkr')
        
        # Apply overrides if provided
        if config_override:
            provider_config.update(config_override)
        
        # IBKR takes individual parameters
        return IbkrDataProvider(
            ip_address=provider_config.get('host', 'localhost'),
            port=provider_config.get('port', 7497)
        )
    
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