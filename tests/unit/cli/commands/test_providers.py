import pytest
import logging
from unittest.mock import Mock, patch, MagicMock, call
from click.testing import CliRunner
from datetime import datetime, timedelta

from vortex.cli.commands.providers import (
    providers, show_providers_list, check_providers, check_single_provider_via_plugin,
    check_single_provider, show_provider_info, show_barchart_info, show_yahoo_info,
    show_ibkr_info
)
from vortex.core.config import ConfigManager
from vortex.infrastructure.plugins import ProviderRegistry


class TestProvidersCommand:
    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_registry(self):
        """Create mock provider registry."""
        registry = Mock(spec=ProviderRegistry)
        registry.list_plugins.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock get_plugin_info with complete data structure
        registry.get_plugin_info.return_value = {
            'supported_assets': ['futures', 'stocks'],
            'requires_auth': True,
            'description': 'Test provider',
            'rate_limits': '150/day',
            'display_name': 'Test Provider',
            'config_schema': {'username': str, 'password': str}
        }
        
        # Mock get_plugin
        mock_plugin = Mock()
        mock_plugin.metadata = Mock()
        mock_plugin.metadata.auth_method = "Username/Password"
        mock_plugin.validate_config = Mock()
        registry.get_plugin.return_value = mock_plugin
        
        
        return registry

    @pytest.fixture
    def mock_config_manager(self):
        """Create mock config manager with proper VortexConfig structure."""
        config = Mock(spec=ConfigManager)
        
        # Create mock VortexConfig-like object
        mock_config = Mock()
        mock_config.providers = Mock()
        
        # Mock provider configs with model_dump method
        for provider in ['barchart', 'yahoo', 'ibkr']:
            provider_config = Mock()
            provider_config.model_dump.return_value = {'enabled': True}
            setattr(mock_config.providers, provider, provider_config)
        
        config.load_config.return_value = mock_config
        config.get_provider_config.return_value = {'enabled': True}
        return config

    @pytest.fixture  
    def mock_vortex_config(self):
        """Create a mock VortexConfig object."""
        config = Mock()
        config.providers = Mock()
        
        # Create provider sub-configs
        barchart_config = Mock()
        barchart_config.model_dump.return_value = {}
        barchart_config.username = None
        barchart_config.password = None
        
        yahoo_config = Mock()
        yahoo_config.model_dump.return_value = {}
        
        ibkr_config = Mock()
        ibkr_config.model_dump.return_value = {}
        ibkr_config.host = "localhost"
        ibkr_config.port = 7497
        
        config.providers.barchart = barchart_config
        config.providers.yahoo = yahoo_config
        config.providers.ibkr = ibkr_config
        
        return config

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.check_provider_configuration')
    def test_list_providers_basic(self, mock_check_config, mock_config_manager_class, mock_get_registry, 
                                runner, mock_registry, mock_vortex_config):
        """Test basic provider listing."""
        mock_get_registry.return_value = mock_registry
        
        # Mock config manager
        mock_config_manager = Mock()
        mock_config_manager.load_config.return_value = mock_vortex_config
        mock_config_manager_class.return_value = mock_config_manager
        
        # Mock check_provider_configuration
        mock_check_config.return_value = {'configured': False, 'status': '⚠ Not configured', 'message': 'Test message'}
        
        result = runner.invoke(providers, ['--list'], obj={'config_file': None})
        
        assert result.exit_code == 0
        # Check that provider table is displayed
        assert 'BARCHART' in result.output
        assert 'YAHOO' in result.output 
        assert 'Total providers available: 3' in result.output

    def test_command_help(self, runner):
        """Test provider command help."""
        result = runner.invoke(providers, ['--help'])
        
        assert result.exit_code == 0
        assert 'provider' in result.output.lower()
        assert '--list' in result.output
        assert '--test' in result.output
        assert '--info' in result.output


class TestProviderInfo:
    """Test provider info display functionality."""
    
    @patch('vortex.cli.commands.providers.show_barchart_info')
    @patch('vortex.cli.commands.providers.console')
    def test_show_provider_info_barchart(self, mock_console, mock_show_barchart):
        """Test showing Barchart provider info."""
        from vortex.cli.commands.providers import show_provider_info
        
        mock_config_manager = Mock()
        
        show_provider_info(mock_config_manager, 'barchart')
        
        mock_console.print.assert_called()
        mock_show_barchart.assert_called_once()
    
    @patch('vortex.cli.commands.providers.show_yahoo_info')
    @patch('vortex.cli.commands.providers.console')
    def test_show_provider_info_yahoo(self, mock_console, mock_show_yahoo):
        """Test showing Yahoo provider info."""
        from vortex.cli.commands.providers import show_provider_info
        
        mock_config_manager = Mock()
        
        show_provider_info(mock_config_manager, 'yahoo')
        
        mock_console.print.assert_called()
        mock_show_yahoo.assert_called_once()
    
    @patch('vortex.cli.commands.providers.show_ibkr_info')
    @patch('vortex.cli.commands.providers.console')
    def test_show_provider_info_ibkr(self, mock_console, mock_show_ibkr):
        """Test showing IBKR provider info."""
        from vortex.cli.commands.providers import show_provider_info
        
        mock_config_manager = Mock()
        
        show_provider_info(mock_config_manager, 'ibkr')
        
        mock_console.print.assert_called()
        mock_show_ibkr.assert_called_once()
    
    @patch('vortex.cli.commands.providers.console')
    def test_show_barchart_info(self, mock_console):
        """Test Barchart info display."""
        from vortex.cli.commands.providers import show_barchart_info
        
        show_barchart_info()
        
        # Should print table and setup instructions
        assert mock_console.print.call_count >= 2
    
    @patch('vortex.cli.commands.providers.console')
    def test_show_yahoo_info(self, mock_console):
        """Test Yahoo info display."""
        from vortex.cli.commands.providers import show_yahoo_info
        
        show_yahoo_info()
        
        # Should print table and setup instructions
        assert mock_console.print.call_count >= 2
    
    @patch('vortex.cli.commands.providers.console')
    def test_show_ibkr_info(self, mock_console):
        """Test IBKR info display."""
        from vortex.cli.commands.providers import show_ibkr_info
        
        show_ibkr_info()
        
        # Should print table and setup instructions
        assert mock_console.print.call_count >= 2


class TestLegacyProviderTesting:
    """Test legacy provider testing functionality."""
    
    def test_check_single_provider_barchart_no_credentials(self):
        """Test Barchart provider check without credentials."""
        from vortex.cli.commands.providers import check_single_provider
        
        mock_config_manager = Mock()
        mock_config_manager.get_provider_config.return_value = {}
        
        result = check_single_provider(mock_config_manager, 'barchart')
        
        assert result['success'] is False
        assert 'credentials' in result['message'].lower()
    
    @patch('socket.socket')
    def test_check_single_provider_ibkr_success(self, mock_socket_class):
        """Test successful IBKR provider check."""
        from vortex.cli.commands.providers import check_single_provider
        
        # Mock socket instance and connection success
        mock_socket = Mock()
        mock_socket.connect_ex.return_value = 0  # Success
        mock_socket_class.return_value = mock_socket
        
        mock_config_manager = Mock()
        mock_config_manager.get_provider_config.return_value = {
            'host': 'localhost',
            'port': 7497
        }
        
        result = check_single_provider(mock_config_manager, 'ibkr')
        
        assert result['success'] is True
        assert 'Successfully connected to localhost:7497' in result['message']
    
    def test_check_single_provider_ibkr_no_host(self):
        """Test IBKR provider check without host."""
        from vortex.cli.commands.providers import check_single_provider
        
        mock_config_manager = Mock()
        mock_config_manager.get_provider_config.return_value = {'host': ''}
        
        result = check_single_provider(mock_config_manager, 'ibkr')
        
        assert result['success'] is False
        assert 'No host configured' in result['message']
    
    @patch('socket.socket')
    def test_check_single_provider_ibkr_connection_failed(self, mock_socket_class):
        """Test IBKR provider check with connection failure."""
        from vortex.cli.commands.providers import check_single_provider
        
        # Mock socket instance and connection failure
        mock_socket = Mock()
        mock_socket.connect_ex.return_value = 1  # Connection failed
        mock_socket_class.return_value = mock_socket
        
        mock_config_manager = Mock()
        mock_config_manager.get_provider_config.return_value = {
            'host': 'localhost',
            'port': 7497
        }
        
        result = check_single_provider(mock_config_manager, 'ibkr')
        
        assert result['success'] is False
        assert 'Cannot connect to localhost:7497' in result['message']
    
    def test_check_single_provider_unknown(self):
        """Test provider check for unknown provider."""
        from vortex.cli.commands.providers import check_single_provider
        
        mock_config_manager = Mock()
        mock_config_manager.get_provider_config.return_value = {}
        
        result = check_single_provider(mock_config_manager, 'unknown')
        
        assert result['success'] is False
        assert 'Unknown provider' in result['message']


class TestProviderTesting:
    """Test provider testing functionality."""
    
    @patch('vortex.cli.commands.providers.check_provider_configuration')
    def test_check_single_provider_via_plugin_success(self, mock_check_config):
        """Test successful provider check via plugin."""
        from vortex.cli.commands.providers import check_single_provider_via_plugin
        
        mock_vortex_config = Mock()
        mock_vortex_config.providers = Mock()
        barchart_config = Mock()
        barchart_config.model_dump.return_value = {'username': 'test', 'password': 'pass'}
        mock_vortex_config.providers.barchart = barchart_config
        
        mock_config_manager = Mock()
        mock_config_manager.load_config.return_value = mock_vortex_config
        
        mock_registry = Mock()
        mock_registry.get_plugin_info.return_value = {'requires_auth': True}
        mock_registry.test_provider.return_value = True
        
        mock_check_config.return_value = {'configured': True}
        
        result = check_single_provider_via_plugin(mock_config_manager, 'barchart', mock_registry)
        
        assert result['success'] is True
        assert result['message'] == 'Connection successful'
    
    @patch('vortex.cli.commands.providers.check_provider_configuration')
    def test_check_single_provider_via_plugin_not_configured(self, mock_check_config):
        """Test provider check when not configured."""
        from vortex.cli.commands.providers import check_single_provider_via_plugin
        
        mock_vortex_config = Mock()
        mock_vortex_config.providers = Mock()
        barchart_config = Mock()
        barchart_config.model_dump.return_value = {}
        mock_vortex_config.providers.barchart = barchart_config
        
        mock_config_manager = Mock()
        mock_config_manager.load_config.return_value = mock_vortex_config
        
        mock_registry = Mock()
        mock_registry.get_plugin_info.return_value = {'requires_auth': True}
        
        mock_check_config.return_value = {
            'configured': False,
            'message': 'Not configured properly'
        }
        
        result = check_single_provider_via_plugin(mock_config_manager, 'barchart', mock_registry)
        
        assert result['success'] is False
        assert result['message'] == 'Not configured properly'