"""
Unit tests for the provider factory with dependency injection.
"""

import pytest
from unittest.mock import Mock, patch

from vortex.infrastructure.providers.factory import ProviderFactory
from vortex.infrastructure.providers.protocol import DataProviderProtocol
from vortex.exceptions.plugins import PluginNotFoundError


class TestProviderFactory:
    """Test the ProviderFactory class."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager."""
        mock = Mock()
        mock.get_provider_config.return_value = {
            'username': 'test_user',
            'password': 'test_pass',
            'daily_limit': 150
        }
        return mock
    
    @pytest.fixture
    def factory(self, mock_config_manager):
        """Create a factory instance with mock config."""
        return ProviderFactory(mock_config_manager)
    
    def test_factory_initialization(self, factory):
        """Test factory initializes with correct providers."""
        providers = factory.list_providers()
        assert 'barchart' in providers
        assert 'yahoo' in providers
        assert 'ibkr' in providers
        assert len(providers) == 3
    
    def test_create_yahoo_provider(self, factory):
        """Test creating Yahoo provider (no config required)."""
        provider = factory.create_provider('yahoo')
        
        assert provider is not None
        assert isinstance(provider, DataProviderProtocol)
        assert provider.get_name() == 'YahooFinance'
    
    @patch('vortex.infrastructure.providers.barchart.provider.BarchartAuth')
    def test_create_barchart_provider(self, mock_auth_class, factory, mock_config_manager):
        """Test creating Barchart provider with configuration."""
        # Mock the auth to avoid login issues
        mock_auth = Mock()
        mock_auth_class.return_value = mock_auth
        
        provider = factory.create_provider('barchart')
        
        assert provider is not None
        assert isinstance(provider, DataProviderProtocol)
        assert provider.get_name() == 'Barchart'
        
        # Verify config manager was called
        mock_config_manager.get_provider_config.assert_called_with('barchart')
    
    @patch('vortex.infrastructure.providers.barchart.provider.BarchartAuth')
    def test_create_barchart_with_override(self, mock_auth_class, factory):
        """Test creating Barchart provider with config override."""
        # Mock the auth to avoid login issues
        mock_auth = Mock()
        mock_auth_class.return_value = mock_auth
        
        override_config = {
            'username': 'override_user',
            'password': 'override_pass',
            'daily_limit': 250
        }
        
        provider = factory.create_provider('barchart', override_config)
        
        assert provider is not None
        assert provider.daily_limit == 250
    
    def test_create_provider_not_found(self, factory):
        """Test creating non-existent provider raises error."""
        with pytest.raises(PluginNotFoundError) as exc_info:
            factory.create_provider('nonexistent')
        
        assert "Provider 'nonexistent' not found" in str(exc_info.value)
        assert "Available providers: barchart, yahoo, ibkr" in str(exc_info.value)
    
    def test_create_barchart_missing_credentials(self, factory, mock_config_manager):
        """Test creating Barchart without required credentials."""
        mock_config_manager.get_provider_config.return_value = {}
        
        with pytest.raises(ValueError) as exc_info:
            factory.create_provider('barchart')
        
        assert "Missing required configuration" in str(exc_info.value)
        assert "username, password" in str(exc_info.value)
    
    def test_register_provider(self, factory):
        """Test registering a new provider."""
        mock_provider_class = Mock()
        mock_builder = Mock(return_value=Mock())
        
        factory.register_provider('custom', mock_provider_class, mock_builder)
        
        assert 'custom' in factory.list_providers()
        
        # Create the custom provider
        custom_provider = factory.create_provider('custom', {'test': 'config'})
        mock_builder.assert_called_once_with({'test': 'config'})
    
    def test_register_provider_default_builder(self, factory):
        """Test registering provider without custom builder."""
        mock_provider_class = Mock()
        mock_instance = Mock()
        mock_provider_class.return_value = mock_instance
        
        factory.register_provider('custom', mock_provider_class)
        
        # Create with default builder
        provider = factory.create_provider('custom', {'test': 'config'})
        
        mock_provider_class.assert_called_once_with({'test': 'config'})
        assert provider == mock_instance
    
    def test_get_provider_info_barchart(self, factory):
        """Test getting Barchart provider information."""
        info = factory.get_provider_info('barchart')
        
        assert info['class'] == 'BarchartDataProvider'
        assert 'Futures' in info['supported_assets']
        assert info['requires_auth'] is True
        assert 'username' in info['required_config']
        assert 'password' in info['required_config']
        assert 'daily_limit' in info['optional_config']
    
    def test_get_provider_info_yahoo(self, factory):
        """Test getting Yahoo provider information."""
        info = factory.get_provider_info('yahoo')
        
        assert info['class'] == 'YahooDataProvider'
        assert 'Stocks' in info['supported_assets']
        assert info['requires_auth'] is False
        assert len(info['required_config']) == 0
    
    def test_get_provider_info_not_found(self, factory):
        """Test getting info for non-existent provider."""
        with pytest.raises(PluginNotFoundError) as exc_info:
            factory.get_provider_info('nonexistent')
        
        assert "Provider 'nonexistent' not found" in str(exc_info.value)
    
    @patch('vortex.infrastructure.providers.ibkr.provider.IB')
    def test_create_ibkr_provider(self, mock_ib_class, factory, mock_config_manager):
        """Test creating IBKR provider with configuration."""
        # Mock IB to avoid connection attempts
        mock_ib = Mock()
        mock_ib_class.return_value = mock_ib
        
        mock_config_manager.get_provider_config.return_value = {
            'host': 'localhost',
            'port': 7497,
            'client_id': 1
        }
        
        provider = factory.create_provider('ibkr')
        
        assert provider is not None
        assert isinstance(provider, DataProviderProtocol)
        
        # Verify config manager was called
        mock_config_manager.get_provider_config.assert_called_with('ibkr')
    
    def test_factory_without_config_manager(self):
        """Test factory creates default config manager if none provided."""
        with patch('vortex.infrastructure.providers.factory.ConfigManager') as mock_cm_class:
            mock_cm = Mock()
            mock_cm_class.return_value = mock_cm
            
            factory = ProviderFactory()
            
            assert factory.config_manager == mock_cm
            mock_cm_class.assert_called_once()