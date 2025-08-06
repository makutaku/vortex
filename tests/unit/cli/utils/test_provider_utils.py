"""Tests for provider utility functions."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import click

from vortex.cli.utils.provider_utils import (
    get_available_providers,
    create_provider_choice,
    create_provider_choice_with_all,
    get_provider_config_from_vortex_config,
    validate_provider_exists,
    get_provider_display_name,
    get_provider_auth_requirements,
    check_provider_configuration
)
from vortex.plugins import PluginNotFoundError


class TestProviderUtils:
    """Test cases for provider utility functions."""

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_get_available_providers_success(self, mock_get_registry):
        """Test get_available_providers when registry works."""
        mock_registry = Mock()
        mock_registry.list_plugins.return_value = ['barchart', 'yahoo', 'ibkr']
        mock_get_registry.return_value = mock_registry

        result = get_available_providers()

        assert result == ['barchart', 'yahoo', 'ibkr']
        mock_registry.list_plugins.assert_called_once()

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    @patch('vortex.cli.utils.provider_utils.logger')
    def test_get_available_providers_fallback(self, mock_logger, mock_get_registry):
        """Test get_available_providers fallback when registry fails."""
        mock_get_registry.side_effect = Exception("Registry error")

        result = get_available_providers()

        assert result == ['barchart', 'yahoo', 'ibkr']
        mock_logger.warning.assert_called_once()

    @patch('vortex.cli.utils.provider_utils.get_available_providers')
    def test_create_provider_choice(self, mock_get_providers):
        """Test create_provider_choice."""
        mock_get_providers.return_value = ['barchart', 'yahoo']

        result = create_provider_choice()

        assert isinstance(result, click.Choice)
        assert result.choices == ('barchart', 'yahoo')  # Click converts to tuple
        assert not result.case_sensitive

    @patch('vortex.cli.utils.provider_utils.get_available_providers')
    def test_create_provider_choice_with_all(self, mock_get_providers):
        """Test create_provider_choice_with_all."""
        mock_get_providers.return_value = ['barchart', 'yahoo']

        result = create_provider_choice_with_all()

        assert isinstance(result, click.Choice)
        assert result.choices == ('barchart', 'yahoo', 'all')  # Click converts to tuple
        assert not result.case_sensitive

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    @patch('vortex.cli.utils.provider_utils.logger')
    def test_get_provider_config_success(self, mock_logger, mock_get_registry):
        """Test get_provider_config_from_vortex_config success."""
        # Mock registry and plugin
        mock_registry = Mock()
        mock_plugin = Mock()
        mock_get_registry.return_value = mock_registry
        mock_registry.get_plugin.return_value = mock_plugin

        # Mock vortex config - use actual objects with the data
        class MockProviderConfig:
            def __init__(self):
                self.username = 'test'
                self.password = 'secret'
        
        class MockProviders:
            def __init__(self):
                self.barchart = MockProviderConfig()
        
        class MockGeneral:
            def __init__(self):
                self.timeout = 60
                self.max_retries = 5
        
        class MockVortexConfig:
            def __init__(self):
                self.providers = MockProviders()
                self.general = MockGeneral()
        
        mock_vortex_config = MockVortexConfig()

        result = get_provider_config_from_vortex_config('barchart', mock_vortex_config)

        expected = {
            'username': 'test',
            'password': 'secret',
            'timeout': 60,
            'max_retries': 5,
            'enabled': True
        }
        assert result == expected
        mock_registry.get_plugin.assert_called_once_with('barchart')

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    @patch('vortex.cli.utils.provider_utils.logger')
    def test_get_provider_config_with_dict_method(self, mock_logger, mock_get_registry):
        """Test get_provider_config with dict() method."""
        mock_registry = Mock()
        mock_plugin = Mock()
        mock_get_registry.return_value = mock_registry
        mock_registry.get_plugin.return_value = mock_plugin

        # Mock config with dict() method - don't inherit __dict__
        class MockProviderConfig:
            __slots__ = ('_data',)  # Prevent __dict__ creation
            
            def __init__(self):
                self._data = {'api_key': 'test_key'}
                
            def dict(self):
                return self._data
        
        class MockProviders:
            def __init__(self):
                self.yahoo = MockProviderConfig()
        
        class MockGeneral:
            def __init__(self):
                self.timeout = 30
                self.max_retries = 3
        
        class MockVortexConfig:
            def __init__(self):
                self.providers = MockProviders()
                self.general = MockGeneral()
        
        mock_vortex_config = MockVortexConfig()

        result = get_provider_config_from_vortex_config('yahoo', mock_vortex_config)

        expected = {
            'api_key': 'test_key',
            'timeout': 30,
            'max_retries': 3,
            'enabled': True
        }
        assert result == expected

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    @patch('vortex.cli.utils.provider_utils.logger')
    def test_get_provider_config_with_plain_dict(self, mock_logger, mock_get_registry):
        """Test get_provider_config with plain dictionary."""
        mock_registry = Mock()
        mock_plugin = Mock()
        mock_get_registry.return_value = mock_registry
        mock_registry.get_plugin.return_value = mock_plugin

        # Mock config as plain dict
        mock_vortex_config = Mock()
        
        mock_providers = Mock()
        mock_providers.ibkr = {'host': 'localhost', 'port': 7497}
        mock_vortex_config.providers = mock_providers
        
        mock_general = Mock()
        mock_general.timeout = 45
        mock_general.max_retries = 2
        mock_vortex_config.general = mock_general

        result = get_provider_config_from_vortex_config('ibkr', mock_vortex_config)

        expected = {
            'host': 'localhost',
            'port': 7497,
            'timeout': 45,
            'max_retries': 2,
            'enabled': True
        }
        assert result == expected

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    @patch('vortex.cli.utils.provider_utils.logger')
    def test_get_provider_config_plugin_not_found(self, mock_logger, mock_get_registry):
        """Test get_provider_config when plugin not found."""
        mock_registry = Mock()
        mock_get_registry.return_value = mock_registry
        mock_registry.get_plugin.side_effect = PluginNotFoundError("Plugin not found")

        mock_vortex_config = Mock()

        with pytest.raises(PluginNotFoundError):
            get_provider_config_from_vortex_config('unknown', mock_vortex_config)

        mock_logger.error.assert_called_with("Provider plugin 'unknown' not found")

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    @patch('vortex.cli.utils.provider_utils.logger')
    def test_get_provider_config_general_exception(self, mock_logger, mock_get_registry):
        """Test get_provider_config with general exception."""
        mock_registry = Mock()
        mock_get_registry.return_value = mock_registry
        mock_registry.get_plugin.side_effect = Exception("General error")

        mock_vortex_config = Mock()

        result = get_provider_config_from_vortex_config('barchart', mock_vortex_config)

        # Should return fallback config
        expected = {
            'timeout': 30,
            'max_retries': 3,
            'enabled': True
        }
        assert result == expected
        mock_logger.error.assert_called_with("Failed to get config for provider 'barchart': General error")

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_validate_provider_exists_success(self, mock_get_registry):
        """Test validate_provider_exists when provider exists."""
        mock_registry = Mock()
        mock_registry.get_plugin.return_value = Mock()
        mock_get_registry.return_value = mock_registry

        result = validate_provider_exists('barchart')

        assert result is True
        mock_registry.get_plugin.assert_called_once_with('barchart')

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_validate_provider_exists_not_found(self, mock_get_registry):
        """Test validate_provider_exists when provider not found."""
        mock_registry = Mock()
        mock_registry.get_plugin.side_effect = PluginNotFoundError("Not found")
        mock_get_registry.return_value = mock_registry

        result = validate_provider_exists('unknown')

        assert result is False

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    @patch('vortex.cli.utils.provider_utils.logger')
    def test_validate_provider_exists_exception(self, mock_logger, mock_get_registry):
        """Test validate_provider_exists with general exception."""
        mock_registry = Mock()
        mock_registry.get_plugin.side_effect = Exception("Registry error")
        mock_get_registry.return_value = mock_registry

        result = validate_provider_exists('barchart')

        assert result is False
        mock_logger.warning.assert_called_with("Error checking provider 'barchart': Registry error")

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_get_provider_display_name_success(self, mock_get_registry):
        """Test get_provider_display_name when successful."""
        mock_registry = Mock()
        mock_registry.get_plugin_info.return_value = {'display_name': 'Barchart Data'}
        mock_get_registry.return_value = mock_registry

        result = get_provider_display_name('barchart')

        assert result == 'Barchart Data'
        mock_registry.get_plugin_info.assert_called_once_with('barchart')

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_get_provider_display_name_fallback(self, mock_get_registry):
        """Test get_provider_display_name fallback."""
        mock_registry = Mock()
        mock_registry.get_plugin_info.side_effect = Exception("Error")
        mock_get_registry.return_value = mock_registry

        result = get_provider_display_name('barchart')

        assert result == 'Barchart'

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_get_provider_auth_requirements_success(self, mock_get_registry):
        """Test get_provider_auth_requirements success."""
        mock_registry = Mock()
        plugin_info = {
            'requires_auth': True,
            'config_schema': {'username': str, 'password': str},
            'display_name': 'Barchart Data'
        }
        mock_registry.get_plugin_info.return_value = plugin_info
        mock_get_registry.return_value = mock_registry

        result = get_provider_auth_requirements('barchart')

        expected = {
            'requires_auth': True,
            'config_schema': {'username': str, 'password': str},
            'display_name': 'Barchart Data'
        }
        assert result == expected

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    @patch('vortex.cli.utils.provider_utils.logger')
    def test_get_provider_auth_requirements_exception(self, mock_logger, mock_get_registry):
        """Test get_provider_auth_requirements with exception."""
        mock_registry = Mock()
        mock_registry.get_plugin_info.side_effect = Exception("Error")
        mock_get_registry.return_value = mock_registry

        result = get_provider_auth_requirements('barchart')

        expected = {
            'requires_auth': True,
            'config_schema': None,
            'display_name': 'Barchart'
        }
        assert result == expected
        mock_logger.warning.assert_called_with("Failed to get auth requirements for 'barchart': Error")

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_check_provider_configuration_no_auth_required(self, mock_get_registry):
        """Test check_provider_configuration when no auth required."""
        mock_registry = Mock()
        plugin_info = {'requires_auth': False}
        mock_registry.get_plugin_info.return_value = plugin_info
        mock_get_registry.return_value = mock_registry

        result = check_provider_configuration('yahoo', {})

        expected = {
            'configured': True,
            'status': '✓ Available',
            'message': 'No authentication required'
        }
        assert result == expected

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_check_provider_configuration_auth_required_not_configured(self, mock_get_registry):
        """Test check_provider_configuration when auth required but not configured."""
        mock_registry = Mock()
        plugin_info = {'requires_auth': True}
        mock_registry.get_plugin_info.return_value = plugin_info
        mock_get_registry.return_value = mock_registry

        result = check_provider_configuration('barchart', {})

        expected = {
            'configured': False,
            'status': '⚠ Not configured',
            'message': 'Authentication required but not configured'
        }
        assert result == expected

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_check_provider_configuration_valid_config(self, mock_get_registry):
        """Test check_provider_configuration with valid config."""
        mock_registry = Mock()
        plugin_info = {'requires_auth': True}
        mock_registry.get_plugin_info.return_value = plugin_info
        
        mock_plugin = Mock()
        mock_plugin.validate_config.return_value = None  # No exception = valid
        mock_registry.get_plugin.return_value = mock_plugin
        mock_get_registry.return_value = mock_registry

        config = {'username': 'test', 'password': 'secret'}
        result = check_provider_configuration('barchart', config)

        expected = {
            'configured': True,
            'status': '✓ Available',
            'message': 'Configuration valid'
        }
        assert result == expected
        mock_plugin.validate_config.assert_called_once_with(config)

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    def test_check_provider_configuration_invalid_config(self, mock_get_registry):
        """Test check_provider_configuration with invalid config."""
        mock_registry = Mock()
        plugin_info = {'requires_auth': True}
        mock_registry.get_plugin_info.return_value = plugin_info
        
        mock_plugin = Mock()
        mock_plugin.validate_config.side_effect = Exception("Invalid username format")
        mock_registry.get_plugin.return_value = mock_plugin
        mock_get_registry.return_value = mock_registry

        config = {'username': '', 'password': 'secret'}
        result = check_provider_configuration('barchart', config)

        expected = {
            'configured': False,
            'status': '⚠ Configuration error',
            'message': 'Invalid configuration: Invalid username format...'
        }
        assert result == expected

    @patch('vortex.cli.utils.provider_utils.get_provider_registry')
    @patch('vortex.cli.utils.provider_utils.logger')
    def test_check_provider_configuration_plugin_error(self, mock_logger, mock_get_registry):
        """Test check_provider_configuration with plugin error."""
        mock_registry = Mock()
        mock_registry.get_plugin_info.side_effect = Exception("Plugin error")
        mock_get_registry.return_value = mock_registry

        result = check_provider_configuration('unknown', {'key': 'value'})

        expected = {
            'configured': False,
            'status': '✗ Error',
            'message': 'Plugin error: Plugin error...'
        }
        assert result == expected
        mock_logger.warning.assert_called_with("Failed to check configuration for 'unknown': Plugin error")

    def test_get_provider_config_missing_general_attrs(self):
        """Test get_provider_config when general config attrs are missing."""
        with patch('vortex.cli.utils.provider_utils.get_provider_registry') as mock_get_registry:
            mock_registry = Mock()
            mock_plugin = Mock()
            mock_get_registry.return_value = mock_registry
            mock_registry.get_plugin.return_value = mock_plugin

            # Mock config without general attrs
            mock_vortex_config = Mock()
            
            mock_providers = Mock()
            mock_providers.test = {}
            mock_vortex_config.providers = mock_providers
            
            # Make getattr return defaults
            mock_general = Mock()
            del mock_general.timeout
            del mock_general.max_retries
            mock_vortex_config.general = mock_general

            result = get_provider_config_from_vortex_config('test', mock_vortex_config)

            # Should use defaults
            assert result['timeout'] == 30
            assert result['max_retries'] == 3
            assert result['enabled'] is True

    def test_get_provider_config_unsupported_config_type(self):
        """Test get_provider_config with unsupported config object type."""
        with patch('vortex.cli.utils.provider_utils.get_provider_registry') as mock_get_registry:
            mock_registry = Mock()
            mock_plugin = Mock()
            mock_get_registry.return_value = mock_registry
            mock_registry.get_plugin.return_value = mock_plugin

            # Mock config object without __dict__ or dict() method
            mock_vortex_config = Mock()
            
            mock_providers = Mock()
            mock_providers.test = "unsupported_type"
            mock_vortex_config.providers = mock_providers
            
            mock_general = Mock()
            mock_general.timeout = 30
            mock_general.max_retries = 3
            mock_vortex_config.general = mock_general

            result = get_provider_config_from_vortex_config('test', mock_vortex_config)

            # Should use empty config and merge with general
            expected = {
                'timeout': 30,
                'max_retries': 3,
                'enabled': True
            }
            assert result == expected