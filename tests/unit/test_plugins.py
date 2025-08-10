"""Tests for the plugin registry system."""

import pytest
from unittest.mock import Mock, patch

from vortex.infrastructure.plugins import ProviderRegistry, get_provider_registry, PluginNotFoundError


class TestProviderRegistry:
    """Test the ProviderRegistry class."""
    
    def test_registry_initialization(self):
        """Test registry initializes with expected plugins."""
        registry = ProviderRegistry()
        
        plugins = registry.list_plugins()
        assert 'barchart' in plugins
        assert 'yahoo' in plugins
        assert 'ibkr' in plugins
        assert len(plugins) == 3
    
    def test_get_plugin_success(self):
        """Test getting an existing plugin."""
        registry = ProviderRegistry()
        
        barchart_plugin = registry.get_plugin('barchart')
        yahoo_plugin = registry.get_plugin('yahoo')
        ibkr_plugin = registry.get_plugin('ibkr')
        
        assert barchart_plugin is not None
        assert yahoo_plugin is not None
        assert ibkr_plugin is not None
    
    def test_get_plugin_not_found(self):
        """Test getting a non-existent plugin raises exception."""
        registry = ProviderRegistry()
        
        with pytest.raises(PluginNotFoundError) as exc_info:
            registry.get_plugin('nonexistent')
        
        assert "Plugin 'nonexistent' not found" in str(exc_info.value)
    
    def test_register_plugin(self):
        """Test registering a new plugin."""
        registry = ProviderRegistry()
        mock_plugin = Mock()
        
        registry.register_plugin('test_provider', mock_plugin)
        
        assert 'test_provider' in registry.list_plugins()
        assert registry.get_plugin('test_provider') == mock_plugin
    
    @patch('vortex.infrastructure.plugins.YahooDataProvider')
    def test_create_yahoo_provider(self, mock_yahoo_class):
        """Test creating Yahoo provider instance."""
        registry = ProviderRegistry()
        mock_instance = Mock()
        mock_yahoo_class.return_value = mock_instance
        
        provider = registry.create_provider('yahoo', {})
        
        # Yahoo provider should be created without config
        mock_yahoo_class.assert_called_once_with()
        assert provider == mock_instance
    
    @patch('vortex.infrastructure.plugins.BarchartDataProvider')
    def test_create_barchart_provider(self, mock_barchart_class):
        """Test creating Barchart provider instance."""
        registry = ProviderRegistry()
        mock_instance = Mock()
        mock_barchart_class.return_value = mock_instance
        config = {'username': 'test', 'password': 'secret'}
        
        provider = registry.create_provider('barchart', config)
        
        # Barchart provider should be created with individual keyword arguments including defaults
        mock_barchart_class.assert_called_once_with(
            username='test', 
            password='secret', 
            daily_download_limit=150
        )
        assert provider == mock_instance
    
    @patch('vortex.infrastructure.plugins.IbkrDataProvider')
    def test_create_ibkr_provider(self, mock_ibkr_class):
        """Test creating IBKR provider instance."""
        registry = ProviderRegistry()
        mock_instance = Mock()
        mock_ibkr_class.return_value = mock_instance
        config = {'host': 'localhost', 'port': 7497}
        
        provider = registry.create_provider('ibkr', config)
        
        # IBKR provider should be created with config
        mock_ibkr_class.assert_called_once_with(config)
        assert provider == mock_instance
    
    def test_create_provider_not_found(self):
        """Test creating provider for non-existent plugin."""
        registry = ProviderRegistry()
        
        with pytest.raises(PluginNotFoundError) as exc_info:
            registry.create_provider('nonexistent', {})
        
        assert "Plugin 'nonexistent' not found" in str(exc_info.value)
    
    def test_get_plugin_info_barchart(self):
        """Test getting Barchart plugin info."""
        registry = ProviderRegistry()
        
        info = registry.get_plugin_info('barchart')
        
        assert info['supported_assets'] == ['Futures', 'Options', 'Stocks']
        assert info['requires_auth'] is True
        assert 'Barchart.com' in info['description']
        assert 'username' in info['config_schema']
        assert 'password' in info['config_schema']
    
    def test_get_plugin_info_yahoo(self):
        """Test getting Yahoo plugin info."""
        registry = ProviderRegistry()
        
        info = registry.get_plugin_info('yahoo')
        
        assert info['supported_assets'] == ['Stocks', 'ETFs', 'Indices', 'Currencies']
        assert info['requires_auth'] is False
        assert 'Yahoo Finance' in info['description']
        assert info['config_schema'] == {}
    
    def test_get_plugin_info_ibkr(self):
        """Test getting IBKR plugin info."""
        registry = ProviderRegistry()
        
        info = registry.get_plugin_info('ibkr')
        
        assert info['supported_assets'] == ['Stocks', 'Futures', 'Options', 'Forex']
        assert info['requires_auth'] is True
        assert 'Interactive Brokers' in info['description']
        assert 'host' in info['config_schema']
        assert 'port' in info['config_schema']
    
    def test_get_plugin_info_not_found(self):
        """Test getting plugin info for non-existent plugin."""
        registry = ProviderRegistry()
        
        with pytest.raises(PluginNotFoundError) as exc_info:
            registry.get_plugin_info('nonexistent')
        
        assert "Plugin 'nonexistent' not found" in str(exc_info.value)


class TestProviderRegistryGlobal:
    """Test the global provider registry functions."""
    
    def test_get_provider_registry_singleton(self):
        """Test that get_provider_registry returns singleton."""
        # Reset global registry
        import vortex.infrastructure.plugins
        vortex.infrastructure.plugins._registry = None
        
        registry1 = get_provider_registry()
        registry2 = get_provider_registry()
        
        assert registry1 is registry2
        assert isinstance(registry1, ProviderRegistry)
    
    def test_get_provider_registry_initialized(self):
        """Test that global registry is properly initialized."""
        registry = get_provider_registry()
        
        plugins = registry.list_plugins()
        assert len(plugins) >= 3
        assert 'barchart' in plugins
        assert 'yahoo' in plugins
        assert 'ibkr' in plugins


class TestProviderRegistryIntegration:
    """Integration tests for the provider registry."""
    
    def test_registry_with_multiple_operations(self):
        """Test registry works correctly with multiple operations."""
        registry = ProviderRegistry()
        
        # Initial state
        initial_plugins = registry.list_plugins()
        assert len(initial_plugins) == 3
        
        # Add a custom plugin
        mock_plugin = Mock()
        registry.register_plugin('custom', mock_plugin)
        
        # Verify addition
        updated_plugins = registry.list_plugins()
        assert len(updated_plugins) == 4
        assert 'custom' in updated_plugins
        
        # Verify we can still access original plugins
        yahoo_plugin = registry.get_plugin('yahoo')
        custom_plugin = registry.get_plugin('custom')
        
        assert yahoo_plugin is not None
        assert custom_plugin == mock_plugin
    
    def test_plugin_info_for_all_providers(self):
        """Test that plugin info is available for all providers."""
        registry = ProviderRegistry()
        
        for plugin_name in registry.list_plugins():
            info = registry.get_plugin_info(plugin_name)
            
            # Each plugin should have required keys
            assert 'supported_assets' in info
            assert 'requires_auth' in info
            assert 'description' in info
            assert 'rate_limits' in info
            assert 'config_schema' in info
            
            # Supported assets should be a list
            assert isinstance(info['supported_assets'], list)
            assert len(info['supported_assets']) > 0
            
            # requires_auth should be boolean
            assert isinstance(info['requires_auth'], bool)
            
            # Config schema should be dict
            assert isinstance(info['config_schema'], dict)