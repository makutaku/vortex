"""
Plugin registry for data providers.

This module provides a plugin system for managing data provider implementations.
Now enhanced with dependency injection support through ProviderFactory.
"""

from typing import Dict, List, Any, Type, Optional
import warnings

from vortex.exceptions.plugins import PluginNotFoundError
from vortex.infrastructure.providers import BarchartDataProvider, YahooDataProvider, IbkrDataProvider
from vortex.infrastructure.providers.factory import ProviderFactory
from vortex.infrastructure.config import get_config_service


class ProviderRegistry:
    """Registry for data provider plugins with dependency injection support."""
    
    def __init__(self) -> None:
        self._plugins = {
            'barchart': BarchartDataProvider,
            'yahoo': YahooDataProvider,
            'ibkr': IbkrDataProvider,
        }
        # Use factory pattern for better dependency injection
        self._factory = ProviderFactory(get_config_service()._manager)
    
    def get_plugin(self, name: str) -> Type:
        """Get a plugin by name."""
        if name not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{name}' not found")
        return self._plugins[name]
    
    def list_plugins(self) -> List[str]:
        """List all available plugins."""
        return list(self._plugins.keys())
    
    def register_plugin(self, name: str, plugin_class: Type) -> None:
        """Register a new plugin."""
        self._plugins[name] = plugin_class
    
    def create_provider(self, name: str, config: Dict[str, Any]) -> Any:
        """Create a provider instance with the given configuration.
        
        This method now delegates to ProviderFactory for better dependency injection.
        The old direct instantiation is deprecated but maintained for compatibility.
        """
        try:
            # Use the new factory pattern
            return self._factory.create_provider(name, config)
        except Exception as e:
            # Fallback to legacy behavior if factory fails
            warnings.warn(
                f"Using legacy provider instantiation for {name}. "
                "Consider updating to use ProviderFactory directly.",
                DeprecationWarning,
                stacklevel=2
            )
            
            if name not in self._plugins:
                raise PluginNotFoundError(f"Plugin '{name}' not found")
            
            provider_class = self._plugins[name]
            
            # Handle different provider constructor signatures (legacy)
            if name == 'yahoo':
                return provider_class()
            elif name == 'barchart':
                return provider_class(
                    username=config.get('username'),
                    password=config.get('password'),
                    daily_download_limit=config.get('daily_limit', 150)
                )
            else:
                return provider_class(config)
    
    def get_plugin_info(self, name: str) -> Dict[str, Any]:
        """Get plugin information."""
        if name not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{name}' not found")
        
        # Plugin info structure expected by the providers command
        plugin_info = {
            'barchart': {
                'supported_assets': ['Futures', 'Options', 'Stocks'],
                'requires_auth': True,
                'description': 'Premium financial data from Barchart.com',
                'rate_limits': 'Daily limit varies by subscription',
                'config_schema': {'username': 'string', 'password': 'string', 'daily_limit': 'integer'}
            },
            'yahoo': {
                'supported_assets': ['Stocks', 'ETFs', 'Indices', 'Currencies'],
                'requires_auth': False,
                'description': 'Free financial data from Yahoo Finance',
                'rate_limits': 'Rate limited by Yahoo',
                'config_schema': {}
            },
            'ibkr': {
                'supported_assets': ['Stocks', 'Futures', 'Options', 'Forex'],
                'requires_auth': True,
                'description': 'Interactive Brokers TWS/Gateway integration',
                'rate_limits': 'No specific limits',
                'config_schema': {'host': 'string', 'port': 'integer', 'client_id': 'integer'}
            }
        }
        
        return plugin_info[name]


# Global registry instance
_registry = None


def get_provider_registry() -> ProviderRegistry:
    """Get the global provider registry instance."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry