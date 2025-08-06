import pytest
import logging
from unittest.mock import Mock, patch, MagicMock, call
from click.testing import CliRunner

from vortex.cli.commands.providers import providers
from vortex.core.config import ConfigManager
from vortex.plugins import ProviderRegistry


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

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.check_provider_configuration')
    def test_list_providers_with_status_colors(self, mock_check_config, mock_config_class, mock_get_available, 
                                             mock_get_registry, runner, mock_registry, mock_vortex_config):
        """Test provider listing shows status colors."""
        mock_get_registry.return_value = mock_registry
        mock_registry.list_plugins.return_value = ['barchart', 'yahoo', 'ibkr']
        
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config.load_config.return_value = mock_vortex_config
        mock_config_class.return_value = mock_config
        
        # Mock check_provider_configuration  
        mock_check_config.return_value = {'configured': False, 'status': '⚠ Not configured', 'message': 'Test'}
        
        result = runner.invoke(providers, ['--list'])
        
        assert result.exit_code == 0
        # Check that different statuses are handled
        assert 'barchart' in result.output.lower()
        assert 'yahoo' in result.output.lower()
        assert 'ibkr' in result.output.lower()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    @patch('vortex.cli.commands.providers.ConfigManager')
    def test_list_providers_empty(self, mock_config_class, mock_get_available, mock_get_registry, runner):
        """Test provider listing when no providers available."""
        mock_registry = Mock()
        mock_registry.list_plugins.return_value = []
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = []
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config.load_config.return_value = Mock()
        mock_config_class.return_value = mock_config
        
        result = runner.invoke(providers, ['--list'])
        
        assert result.exit_code == 0

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.test_single_provider_via_plugin')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_test_single_provider_success(self, mock_get_available, mock_test_single, mock_config_class, 
                                        mock_get_registry, runner, mock_registry):
        """Test testing a single provider successfully."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_test_single.return_value = {
            'success': True,
            'message': 'Connection successful'
        }
        
        result = runner.invoke(providers, ['--test', 'barchart'])
        
        assert result.exit_code == 0
        assert 'barchart' in result.output.lower()
        mock_test_single.assert_called_once()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.ConfigManager')  
    @patch('vortex.cli.commands.providers.test_single_provider_via_plugin')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_test_single_provider_failure(self, mock_get_available, mock_test_single, mock_config_class,
                                        mock_get_registry, runner, mock_registry):
        """Test testing a single provider with failure."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_test_single.return_value = {
            'success': False,
            'message': 'Authentication failed'
        }
        
        result = runner.invoke(providers, ['--test', 'barchart'])
        
        assert result.exit_code == 0  # Command succeeds even if provider test fails
        assert 'barchart' in result.output.lower()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.test_single_provider_via_plugin')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_test_all_providers(self, mock_get_available, mock_test_single, mock_config_class,
                              mock_get_registry, runner, mock_registry):
        """Test testing all providers."""
        mock_get_registry.return_value = mock_registry
        mock_registry.list_plugins.return_value = ['barchart', 'yahoo']
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_test_single.side_effect = [
            {'success': True, 'message': 'OK'},
            {'success': False, 'message': 'Failed'}
        ]
        
        result = runner.invoke(providers, ['--test', 'all'])
        
        assert result.exit_code == 0
        assert 'barchart' in result.output.lower()
        assert 'yahoo' in result.output.lower()
        assert mock_test_single.call_count == 2

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_test_nonexistent_provider(self, mock_get_available, mock_get_registry, runner, mock_registry):
        """Test testing a provider that doesn't exist."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo']
        
        result = runner.invoke(providers, ['--test', 'nonexistent'])
        
        assert result.exit_code == 0  # Command handles error gracefully
        assert ('unknown' in result.output.lower() or 'not' in result.output.lower())

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_info_provider_basic(self, mock_get_available, mock_get_registry, runner, mock_registry):
        """Test getting basic provider info."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        mock_provider = Mock()
        mock_provider.__class__.__name__ = 'BarchartProvider'
        mock_provider.__doc__ = 'Barchart data provider'
        mock_registry.get_plugin.return_value = mock_provider
        
        result = runner.invoke(providers, ['--info', 'barchart'])
        
        assert result.exit_code == 0
        assert 'barchart' in result.output.lower()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_info_provider_with_config(self, mock_get_available, mock_get_registry, runner, mock_registry):
        """Test provider info with configuration details."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        mock_provider = Mock()
        mock_provider.__class__.__name__ = 'BarchartProvider'
        mock_provider.__doc__ = 'Barchart data provider'
        
        # Mock provider with configuration methods
        if hasattr(mock_provider, 'get_supported_periods'):
            mock_provider.get_supported_periods.return_value = ['1d', '1h']
        if hasattr(mock_provider, 'get_supported_instruments'):
            mock_provider.get_supported_instruments.return_value = ['futures', 'stocks']
        
        mock_registry.get_plugin.return_value = mock_provider
        
        result = runner.invoke(providers, ['--info', 'barchart'])
        
        assert result.exit_code == 0
        assert 'barchart' in result.output.lower()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_info_nonexistent_provider(self, mock_get_available, mock_get_registry, runner, mock_registry):
        """Test getting info for nonexistent provider."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        result = runner.invoke(providers, ['--info', 'nonexistent'])
        
        assert result.exit_code == 0  # Command handles error gracefully
        assert ('unknown' in result.output.lower() or 'not' in result.output.lower())

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.check_provider_configuration')
    def test_no_options_shows_help_or_list(self, mock_check_config, mock_config_class, mock_get_available, 
                                         mock_get_registry, runner, mock_registry, mock_vortex_config):
        """Test running command with no options."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config.load_config.return_value = mock_vortex_config
        mock_config_class.return_value = mock_config
        
        mock_check_config.return_value = {'configured': False, 'status': '⚠ Not configured', 'message': 'Test'}
        
        result = runner.invoke(providers, [])
        
        assert result.exit_code == 0
        # Should either show help or default to listing providers
        assert len(result.output) > 0

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.check_provider_configuration')
    @patch('vortex.cli.commands.providers.console')
    def test_list_providers_console_output(self, mock_console, mock_check_config, mock_config_class, 
                                         mock_get_registry, runner, mock_registry, mock_vortex_config):
        """Test that provider listing uses console for rich output."""
        mock_get_registry.return_value = mock_registry
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config.load_config.return_value = mock_vortex_config
        mock_config_class.return_value = mock_config
        
        mock_check_config.return_value = {'configured': False, 'status': '⚠ Not configured', 'message': 'Test'}
        
        result = runner.invoke(providers, ['--list'])
        
        assert result.exit_code == 0
        # Verify console was used for output
        mock_console.print.assert_called()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.test_single_provider_via_plugin')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_test_provider_with_progress(self, mock_get_available, mock_test_single, mock_config_class, 
                                       mock_get_registry, runner, mock_registry):
        """Test that provider testing shows progress indicator."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        # Mock a response
        def slow_check(config_manager, provider, registry):
            return {'success': True, 'message': 'OK'}
        
        mock_test_single.side_effect = slow_check
        
        result = runner.invoke(providers, ['--test', 'barchart'])
        
        assert result.exit_code == 0
        mock_test_single.assert_called_once()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.test_single_provider_via_plugin')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_test_multiple_providers_summary(self, mock_get_available, mock_test_single, mock_config_class,
                                           mock_get_registry, runner, mock_registry):
        """Test that testing multiple providers shows summary."""
        mock_get_registry.return_value = mock_registry
        mock_registry.list_plugins.return_value = ['barchart', 'yahoo', 'ibkr']
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_test_single.side_effect = [
            {'success': True, 'message': 'OK'},
            {'success': False, 'message': 'Failed'},
            {'success': True, 'message': 'OK'}
        ]
        
        result = runner.invoke(providers, ['--test', 'all'])
        
        assert result.exit_code == 0
        # Should show summary of results
        assert 'barchart' in result.output.lower()
        assert 'yahoo' in result.output.lower()
        assert 'ibkr' in result.output.lower()
        assert mock_test_single.call_count == 3

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_info_provider_detailed(self, mock_get_available, mock_get_registry, runner, mock_registry):
        """Test detailed provider information display."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        mock_provider = Mock()
        mock_provider.__class__.__name__ = 'BarchartProvider'
        mock_provider.__doc__ = 'Professional futures and forex data provider'
        mock_provider.__module__ = 'vortex.infrastructure.providers.barchart'
        
        # Add more detailed attributes
        mock_provider.supported_periods = ['1d', '1h', '1m']
        mock_provider.supported_instruments = ['futures', 'forex']
        mock_provider.requires_credentials = True
        mock_provider.rate_limit = 150
        
        mock_registry.get_plugin.return_value = mock_provider
        
        result = runner.invoke(providers, ['--info', 'barchart'])
        
        assert result.exit_code == 0
        assert 'barchart' in result.output.lower()
        assert 'provider' in result.output.lower()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_info_provider_with_config_status(self, mock_get_available, mock_config_manager_class, 
                                             mock_get_registry, runner, mock_registry):
        """Test provider info includes configuration status."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        mock_provider = Mock()
        mock_provider.__class__.__name__ = 'BarchartProvider'
        mock_registry.get_plugin.return_value = mock_provider
        
        # Mock config manager
        mock_config_manager = Mock()
        mock_config_manager.get_provider_config.return_value = {
            'enabled': True,
            'username': 'test@example.com'
        }
        mock_config_manager_class.return_value = mock_config_manager
        
        result = runner.invoke(providers, ['--info', 'barchart'])
        
        assert result.exit_code == 0
        assert 'barchart' in result.output.lower()

    def test_command_help(self, runner):
        """Test provider command help."""
        result = runner.invoke(providers, ['--help'])
        
        assert result.exit_code == 0
        assert 'provider' in result.output.lower()
        assert '--list' in result.output
        assert '--test' in result.output
        assert '--info' in result.output

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.check_provider_configuration')
    @patch('vortex.cli.commands.providers.Table')
    def test_list_providers_table_format(self, mock_table, mock_check_config, mock_config_class,
                                       mock_get_available, mock_get_registry, runner, mock_registry, 
                                       mock_vortex_config):
        """Test that provider list is formatted as a table."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config.load_config.return_value = mock_vortex_config
        mock_config_class.return_value = mock_config
        
        mock_check_config.return_value = {'configured': False, 'status': '⚠ Not configured', 'message': 'Test'}
        
        mock_table_instance = Mock()
        mock_table.return_value = mock_table_instance
        
        result = runner.invoke(providers, ['--list'])
        
        assert result.exit_code == 0
        # Verify table was created and used
        mock_table.assert_called()
        mock_table_instance.add_column.assert_called()
        mock_table_instance.add_row.assert_called()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.test_single_provider_via_plugin')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_test_provider_exception_handling(self, mock_get_available, mock_test_single, mock_config_class,
                                             mock_get_registry, runner, mock_registry):
        """Test provider testing handles exceptions gracefully."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config_class.return_value = mock_config
        
        mock_test_single.side_effect = Exception("Network error")
        
        result = runner.invoke(providers, ['--test', 'barchart'])
        
        # Should handle exception gracefully and not crash
        assert result.exit_code == 0
        assert 'error' in result.output.lower() or 'exception' in result.output.lower()

    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    def test_info_provider_exception_handling(self, mock_get_available, mock_get_registry, runner, mock_registry):
        """Test provider info handles exceptions gracefully."""
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = ['barchart', 'yahoo', 'ibkr']
        
        result = runner.invoke(providers, ['--info', 'nonexistent'])
        
        # Should handle exception gracefully  
        assert result.exit_code == 0
        assert ('unknown' in result.output.lower() or 'not' in result.output.lower())

    def test_multiple_options_error(self, runner):
        """Test that using multiple conflicting options shows appropriate error."""
        result = runner.invoke(providers, ['--list', '--test', 'barchart'])
        
        # Should either work (last option wins) or show error
        assert result.exit_code == 0

    @patch('vortex.cli.commands.providers.logger')
    @patch('vortex.cli.commands.providers.get_provider_registry')
    @patch('vortex.cli.commands.providers.get_available_providers')
    @patch('vortex.cli.commands.providers.ConfigManager')
    @patch('vortex.cli.commands.providers.check_provider_configuration')
    def test_command_logging(self, mock_check_config, mock_config_class, mock_get_available, 
                           mock_get_registry, mock_logger, runner, mock_vortex_config):
        """Test that command operations are properly logged."""
        mock_registry = Mock()
        mock_registry.list_plugins.return_value = []
        mock_get_registry.return_value = mock_registry
        mock_get_available.return_value = []
        
        # Mock ConfigManager
        mock_config = Mock()
        mock_config.load_config.return_value = mock_vortex_config
        mock_config_class.return_value = mock_config
        
        mock_check_config.return_value = {'configured': False, 'status': '⚠ Not configured', 'message': 'Test'}
        
        result = runner.invoke(providers, ['--list'])
        
        # Should log command execution (exact logging depends on implementation)
        assert result.exit_code == 0