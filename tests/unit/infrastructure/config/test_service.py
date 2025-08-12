"""
Unit tests for the configuration service.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vortex.infrastructure.config.service import (
    ConfigurationService, get_config_service, reset_config_service
)
from vortex.core.config import VortexConfig
from vortex.exceptions.config import ConfigurationError


class TestConfigurationService:
    """Test the ConfigurationService class."""
    
    @pytest.fixture
    def mock_config_manager(self):
        """Create a mock configuration manager."""
        mock = Mock()
        mock.load_config.return_value = VortexConfig()
        mock.get_provider_config.return_value = {
            'username': 'test_user',
            'password': 'test_pass'
        }
        mock.validate_provider_credentials.return_value = True
        mock.get_missing_credentials.return_value = []
        return mock
    
    @pytest.fixture
    def config_service(self, mock_config_manager):
        """Create a configuration service with mock manager."""
        with patch('vortex.infrastructure.config.service.ConfigManager') as mock_cm_class:
            mock_cm_class.return_value = mock_config_manager
            service = ConfigurationService()
            service._manager = mock_config_manager
            return service
    
    def test_service_initialization(self):
        """Test service initializes correctly."""
        with patch('vortex.infrastructure.config.service.ConfigManager') as mock_cm_class:
            mock_cm = Mock()
            mock_cm_class.return_value = mock_cm
            
            service = ConfigurationService()
            
            assert service._manager == mock_cm
            assert service._config is None
            assert service._provider_configs == {}
    
    def test_config_property_lazy_loading(self, config_service, mock_config_manager):
        """Test config property loads configuration lazily."""
        # Config not loaded yet
        assert config_service._config is None
        
        # Access config property
        config = config_service.config
        
        # Should load config
        assert config is not None
        assert isinstance(config, VortexConfig)
        mock_config_manager.load_config.assert_called_once()
        
        # Second access should not reload
        config2 = config_service.config
        assert config2 is config
        assert mock_config_manager.load_config.call_count == 1
    
    def test_reload_config(self, config_service, mock_config_manager):
        """Test reloading configuration."""
        # Load initial config
        config1 = config_service.config
        config_service._provider_configs['test'] = {'cached': 'data'}
        
        # Reload
        config_service.reload_config()
        
        # Should clear caches and reload
        assert config_service._provider_configs == {}
        assert mock_config_manager.load_config.call_count == 2
    
    def test_get_provider_config(self, config_service, mock_config_manager):
        """Test getting provider configuration with caching."""
        # First call should fetch from manager
        config1 = config_service.get_provider_config('barchart')
        
        assert config1 == {'username': 'test_user', 'password': 'test_pass'}
        mock_config_manager.get_provider_config.assert_called_once_with('barchart')
        
        # Second call should use cache
        config2 = config_service.get_provider_config('barchart')
        assert config2 == config1
        assert mock_config_manager.get_provider_config.call_count == 1
        
        # Should return copy to prevent mutation
        config2['username'] = 'modified'
        config3 = config_service.get_provider_config('barchart')
        assert config3['username'] == 'test_user'
    
    def test_get_general_config(self, config_service):
        """Test getting general configuration."""
        general_config = config_service.get_general_config()
        
        assert 'output_directory' in general_config
        assert 'backup_enabled' in general_config
        assert 'dry_run' in general_config
        assert 'default_provider' in general_config
        assert 'logging' in general_config
    
    def test_get_output_directory(self, config_service):
        """Test getting output directory."""
        output_dir = config_service.get_output_directory()
        assert isinstance(output_dir, Path)
    
    def test_get_default_provider(self, config_service):
        """Test getting default provider."""
        provider = config_service.get_default_provider()
        assert provider == 'yahoo'  # Default from VortexConfig
    
    def test_is_backup_enabled(self, config_service):
        """Test checking backup status."""
        enabled = config_service.is_backup_enabled()
        assert isinstance(enabled, bool)
    
    def test_is_dry_run(self, config_service):
        """Test checking dry run status."""
        dry_run = config_service.is_dry_run()
        assert isinstance(dry_run, bool)
    
    def test_get_logging_config(self, config_service):
        """Test getting logging configuration."""
        logging_config = config_service.get_logging_config()
        assert isinstance(logging_config, dict)
    
    def test_validate_provider_config(self, config_service, mock_config_manager):
        """Test validating provider configuration."""
        # Valid config
        assert config_service.validate_provider_config('barchart') is True
        
        # Invalid config
        mock_config_manager.validate_provider_credentials.return_value = False
        assert config_service.validate_provider_config('yahoo') is False
        
        # Error during validation
        mock_config_manager.validate_provider_credentials.side_effect = ConfigurationError("Test error")
        assert config_service.validate_provider_config('ibkr') is False
    
    def test_get_missing_provider_fields(self, config_service, mock_config_manager):
        """Test getting missing provider fields."""
        mock_config_manager.get_missing_credentials.return_value = ['username', 'password']
        
        missing = config_service.get_missing_provider_fields('barchart')
        
        assert missing == ['username', 'password']
        mock_config_manager.get_missing_credentials.assert_called_with('barchart')
    
    def test_update_provider_config(self, config_service, mock_config_manager):
        """Test updating provider configuration."""
        # Reset mock to track calls properly
        mock_config_manager.get_provider_config.reset_mock()
        
        # Update config
        updates = {'username': 'new_user', 'daily_limit': 250}
        config_service.update_provider_config('barchart', updates)
        
        # Should get current config first
        mock_config_manager.get_provider_config.assert_called_with('barchart')
        
        # Should save updated config with merged values
        expected_config = {
            'username': 'new_user',
            'password': 'test_pass',
            'daily_limit': 250
        }
        mock_config_manager.set_provider_config.assert_called_once_with('barchart', expected_config)
    
    def test_save_config(self, config_service, mock_config_manager):
        """Test saving configuration."""
        config_service.save_config()
        
        mock_config_manager.save_config.assert_called_once()


class TestConfigurationServiceSingleton:
    """Test the singleton behavior of configuration service."""
    
    def teardown_method(self):
        """Reset singleton after each test."""
        reset_config_service()
    
    def test_get_config_service_singleton(self):
        """Test that get_config_service returns singleton."""
        with patch('vortex.infrastructure.config.service.ConfigManager'):
            service1 = get_config_service()
            service2 = get_config_service()
            
            assert service1 is service2
    
    def test_get_config_service_with_path(self):
        """Test creating service with custom path."""
        test_path = Path('/tmp/test_config.toml')
        
        with patch('vortex.infrastructure.config.service.ConfigManager') as mock_cm_class:
            service = get_config_service(test_path)
            
            # Path only used on first call
            mock_cm_class.assert_called_once_with(test_path)
    
    def test_reset_config_service(self):
        """Test resetting the singleton."""
        with patch('vortex.infrastructure.config.service.ConfigManager'):
            service1 = get_config_service()
            reset_config_service()
            service2 = get_config_service()
            
            assert service1 is not service2