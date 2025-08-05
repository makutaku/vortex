"""
Plugin registry for data providers.

This module provides a plugin system for managing data provider implementations.
"""

from vortex.exceptions.plugins import PluginNotFoundError
from vortex.providers import BarchartDataProvider, YahooDataProvider, IbkrDataProvider


class ProviderRegistry:
    """Registry for data provider plugins."""
    
    def __init__(self):
        self._plugins = {
            'barchart': BarchartDataProvider,
            'yahoo': YahooDataProvider,
            'ibkr': IbkrDataProvider,
        }
    
    def get_plugin(self, name: str):
        """Get a plugin by name."""
        if name not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{name}' not found")
        return self._plugins[name]
    
    def list_plugins(self):
        """List all available plugins."""
        return list(self._plugins.keys())
    
    def register_plugin(self, name: str, plugin_class):
        """Register a new plugin."""
        self._plugins[name] = plugin_class
    
    def get_plugin_info(self, name: str):
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


def get_provider_registry():
    """Get the global provider registry instance."""
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry