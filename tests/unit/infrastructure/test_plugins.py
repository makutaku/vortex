"""
Tests for the plugin system.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Type

from vortex.infrastructure.plugins import (
    ProviderPlugin, PluginMetadata, ProviderRegistry, 
    get_provider_registry, PluginError, PluginNotFoundError
)
from vortex.infrastructure.plugins.base import BuiltinProviderPlugin, ProviderConfigSchema
from vortex.infrastructure.plugins.builtin.yahoo_plugin import YahooFinancePlugin
from vortex.infrastructure.plugins.builtin.barchart_plugin import BarchartPlugin
from vortex.infrastructure.plugins.builtin.ibkr_plugin import IbkrPlugin
from vortex.infrastructure.providers.data_providers.data_provider import DataProvider

from pydantic import BaseModel, Field


class MockProviderConfigSchema(ProviderConfigSchema):
    """Mock configuration schema for testing."""
    test_param: str = Field(default="test", description="Test parameter")


class MockDataProvider(DataProvider):
    """Mock data provider for testing."""
    
    def get_name(self) -> str:
        return "MockProvider"
    
    def _get_frequency_attributes(self):
        return []
    
    def _fetch_historical_data(self, instrument, frequency_attributes, start_date, end_date):
        return None


class MockProviderPlugin(ProviderPlugin):
    """Mock provider plugin for testing."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="mock",
            display_name="Mock Provider",
            version="1.0.0",
            description="Mock provider for testing",
            author="Test Author",
            requires_auth=False,
            supported_assets=["stocks"]
        )
    
    @property
    def config_schema(self) -> Type[BaseModel]:
        return MockProviderConfigSchema
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        validated = MockProviderConfigSchema(**config)
        return validated.dict()
    
    def create_provider(self, config: Dict[str, Any]) -> DataProvider:
        return MockDataProvider()
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        return True


@pytest.mark.unit
class TestPluginMetadata:
    """Test plugin metadata."""
    
    def test_metadata_creation(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="test",
            display_name="Test Provider",
            version="1.0.0",
            description="Test description",
            author="Test Author"
        )
        
        assert metadata.name == "test"
        assert metadata.display_name == "Test Provider"
        assert metadata.requires_auth is True  # Default
        assert metadata.supported_assets == ["stocks", "futures", "forex"]  # Default
    
    def test_metadata_custom_values(self):
        """Test metadata with custom values."""
        metadata = PluginMetadata(
            name="custom",
            display_name="Custom Provider",
            version="2.0.0",
            description="Custom description",
            author="Custom Author",
            requires_auth=False,
            supported_assets=["crypto", "commodities"],
            rate_limits="100/hour"
        )
        
        assert metadata.requires_auth is False
        assert metadata.supported_assets == ["crypto", "commodities"]
        assert metadata.rate_limits == "100/hour"


@pytest.mark.unit
class TestProviderPlugin:
    """Test provider plugin base class."""
    
    def test_mock_plugin_creation(self):
        """Test creating a mock plugin."""
        plugin = MockProviderPlugin()
        
        assert plugin.metadata.name == "mock"
        assert plugin.metadata.display_name == "Mock Provider"
        assert plugin.config_schema == MockProviderConfigSchema
    
    def test_plugin_validation(self):
        """Test plugin configuration validation."""
        plugin = MockProviderPlugin()
        
        # Valid config
        config = {"test_param": "valid_value"}
        validated = plugin.validate_config(config)
        assert validated["test_param"] == "valid_value"
        
        # Config with defaults
        validated = plugin.validate_config({})
        assert validated["test_param"] == "test"  # Default value
    
    def test_plugin_provider_creation(self):
        """Test creating data provider from plugin."""
        plugin = MockProviderPlugin()
        config = {"test_param": "test_value"}
        
        provider = plugin.create_provider(config)
        assert isinstance(provider, MockDataProvider)
        assert provider.get_name() == "MockProvider"
    
    def test_plugin_connection_test(self):
        """Test plugin connection testing."""
        plugin = MockProviderPlugin()
        config = {"test_param": "test_value"}
        
        result = plugin.test_connection(config)
        assert result is True
    
    def test_plugin_help_text(self):
        """Test plugin help text generation."""
        plugin = MockProviderPlugin()
        help_text = plugin.get_help_text()
        
        assert "Mock Provider Configuration" in help_text
        assert "Mock provider for testing" in help_text
        assert "test_param" in help_text


@pytest.mark.unit
class TestProviderRegistry:
    """Test provider registry."""
    
    @pytest.fixture
    def registry(self):
        """Create a fresh registry for testing."""
        return ProviderRegistry()
    
    @pytest.fixture
    def mock_plugin(self):
        """Create a mock plugin for testing."""
        return MockProviderPlugin()
    
    def test_registry_creation(self, registry):
        """Test creating a registry."""
        assert len(registry._plugins) == 0
        assert registry._initialized is False
    
    def test_plugin_registration(self, registry, mock_plugin):
        """Test registering a plugin."""
        registry.register_plugin(mock_plugin)
        
        assert "mock" in registry._plugins
        assert registry._plugins["mock"] == mock_plugin
    
    def test_plugin_retrieval(self, registry, mock_plugin):
        """Test retrieving a registered plugin."""
        registry.register_plugin(mock_plugin)
        
        retrieved = registry.get_plugin("mock")
        assert retrieved == mock_plugin
        
        # Test case insensitive
        retrieved = registry.get_plugin("MOCK")
        assert retrieved == mock_plugin
    
    def test_plugin_not_found(self, registry):
        """Test retrieving non-existent plugin."""
        with pytest.raises(PluginNotFoundError):
            registry.get_plugin("nonexistent")
    
    def test_list_plugins(self, registry, mock_plugin):
        """Test listing plugins."""
        assert registry.list_plugins() == []
        
        registry.register_plugin(mock_plugin)
        assert registry.list_plugins() == ["mock"]
    
    def test_plugin_info(self, registry, mock_plugin):
        """Test getting plugin information."""
        registry.register_plugin(mock_plugin)
        
        info = registry.get_plugin_info("mock")
        assert info["name"] == "mock"
        assert info["display_name"] == "Mock Provider"
        assert info["version"] == "1.0.0"
        assert info["requires_auth"] is False
        assert info["supported_assets"] == ["stocks"]
    
    def test_create_provider(self, registry, mock_plugin):
        """Test creating provider through registry."""
        registry.register_plugin(mock_plugin)
        
        config = {"test_param": "test_value"}
        provider = registry.create_provider("mock", config)
        
        assert isinstance(provider, MockDataProvider)
        assert provider.get_name() == "MockProvider"
    
    def test_test_provider(self, registry, mock_plugin):
        """Test testing provider through registry."""
        registry.register_plugin(mock_plugin)
        
        config = {"test_param": "test_value"}
        result = registry.test_provider("mock", config)
        
        assert result is True
    
    def test_unregister_plugin(self, registry, mock_plugin):
        """Test unregistering a plugin."""
        registry.register_plugin(mock_plugin)
        assert "mock" in registry._plugins
        
        registry.unregister_plugin("mock")
        assert "mock" not in registry._plugins


@pytest.mark.unit  
class TestBuiltinPlugins:
    """Test built-in provider plugins."""
    
    def test_yahoo_plugin(self):
        """Test Yahoo Finance plugin."""
        plugin = YahooFinancePlugin()
        
        assert plugin.metadata.name == "yahoo"
        assert plugin.metadata.display_name == "Yahoo Finance"
        assert plugin.metadata.requires_auth is False
        
        # Test configuration
        config = {}
        validated = plugin.validate_config(config)
        assert "enabled" in validated
        
        # Test provider creation
        provider = plugin.create_provider(validated)
        assert provider.get_name() == "YahooFinance"
    
    def test_barchart_plugin(self):
        """Test Barchart plugin."""
        plugin = BarchartPlugin()
        
        assert plugin.metadata.name == "barchart"
        assert plugin.metadata.display_name == "Barchart.com"
        assert plugin.metadata.requires_auth is True
        
        # Test configuration validation
        config = {
            "username": "test_user", 
            "password": "test_pass",
            "daily_limit": 100
        }
        validated = plugin.validate_config(config)
        assert validated["username"] == "test_user"
        assert validated["daily_limit"] == 100
        
        # Test invalid config
        with pytest.raises(Exception):  # Should raise validation error
            plugin.validate_config({"username": ""})  # Empty username
    
    def test_ibkr_plugin(self):
        """Test IBKR plugin."""
        plugin = IbkrPlugin()
        
        assert plugin.metadata.name == "ibkr" 
        assert plugin.metadata.display_name == "Interactive Brokers"
        assert plugin.metadata.requires_auth is True
        
        # Test configuration
        config = {
            "host": "localhost",
            "port": 7497,
            "client_id": 1
        }
        validated = plugin.validate_config(config)
        assert validated["host"] == "localhost"
        assert validated["port"] == 7497
        assert validated["client_id"] == 1
        
        # Test invalid port
        with pytest.raises(Exception):
            plugin.validate_config({"port": 99999})  # Invalid port


@pytest.mark.unit
class TestPluginIntegration:
    """Test plugin system integration."""
    
    def test_global_registry(self):
        """Test global registry singleton."""
        registry1 = get_provider_registry()
        registry2 = get_provider_registry()
        
        assert registry1 is registry2  # Should be same instance
    
    @patch('vortex.plugins.registry.importlib')
    def test_builtin_plugin_loading(self, mock_importlib):
        """Test loading built-in plugins."""
        registry = ProviderRegistry()
        
        # Mock successful module import
        mock_module = Mock()
        mock_plugin_class = Mock(return_value=MockProviderPlugin())
        mock_module.MockProviderPlugin = mock_plugin_class
        mock_importlib.import_module.return_value = mock_module
        
        # Test loading
        registry._load_plugin_from_module("test_module")
        
        mock_importlib.import_module.assert_called_with("test_module")
    
    def test_registry_initialization(self):
        """Test registry initialization process."""
        registry = ProviderRegistry()
        
        # Should not be initialized initially
        assert not registry._initialized
        
        # Initialize should load built-in providers
        with patch.object(registry, '_load_builtin_providers') as mock_builtin:
            with patch.object(registry, '_load_external_providers') as mock_external:
                registry.initialize()
                
                mock_builtin.assert_called_once()
                mock_external.assert_called_once()
                assert registry._initialized


@pytest.mark.integration
class TestPluginSystemIntegration:
    """Integration tests for the complete plugin system."""
    
    def test_plugin_system_end_to_end(self):
        """Test complete plugin system workflow."""
        registry = ProviderRegistry()
        
        # Register a plugin
        plugin = MockProviderPlugin()
        registry.register_plugin(plugin)
        
        # Test full workflow
        config = {"test_param": "integration_test"}
        
        # 1. Validate configuration
        validated_config = plugin.validate_config(config)
        assert validated_config["test_param"] == "integration_test"
        
        # 2. Test connection
        connection_ok = registry.test_provider("mock", validated_config)
        assert connection_ok is True
        
        # 3. Create provider
        provider = registry.create_provider("mock", validated_config)
        assert isinstance(provider, MockDataProvider)
        
        # 4. Get plugin info
        info = registry.get_plugin_info("mock")
        assert info["version"] == "1.0.0"
    
    def test_plugin_error_handling(self):
        """Test plugin system error handling."""
        registry = ProviderRegistry()
        
        # Test plugin not found
        with pytest.raises(PluginNotFoundError):
            registry.get_plugin("nonexistent")
        
        # Test invalid configuration
        plugin = MockProviderPlugin()
        registry.register_plugin(plugin)
        
        # This should handle validation errors gracefully
        with pytest.raises(Exception):
            registry.create_provider("mock", {"invalid": "config"})
    
    @patch('vortex.plugins.builtin.yahoo_plugin.YahooDataProvider')
    def test_yahoo_plugin_integration(self, mock_yahoo_provider):
        """Test Yahoo plugin integration."""
        # Mock the YahooDataProvider
        mock_provider_instance = Mock()
        mock_yahoo_provider.return_value = mock_provider_instance
        
        registry = ProviderRegistry()
        plugin = YahooFinancePlugin()
        registry.register_plugin(plugin)
        
        # Test provider creation
        config = {"timeout": 30}
        provider = registry.create_provider("yahoo", config)
        
        # Verify YahooDataProvider was called
        mock_yahoo_provider.assert_called_once()
        assert provider == mock_provider_instance