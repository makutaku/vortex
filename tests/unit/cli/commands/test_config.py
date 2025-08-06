"""Tests for config CLI command."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from rich.table import Table

from vortex.cli.commands.config import (
    show_configuration,
    show_provider_configuration,
    set_provider_credentials
)
from vortex.exceptions import ConfigurationError, InvalidConfigurationError
from vortex.core.config import Provider, LogLevel


class TestShowConfiguration:
    """Test show_configuration function."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_config_manager = Mock()
        self.mock_config = Mock()
        self.mock_config_manager.load_config.return_value = self.mock_config
        self.mock_config_manager.config_file = "/home/user/.config/vortex/config.toml"
    
    def setup_config_mock(self):
        """Setup a complete config mock."""
        self.mock_config.general.output_directory = "/data"
        self.mock_config.general.default_provider = Provider.YAHOO
        self.mock_config.general.backup_enabled = True
        self.mock_config.general.log_level = LogLevel.INFO
        
        # Provider configs
        barchart_config = Mock()
        barchart_config.daily_limit = 150
        yahoo_config = Mock()
        ibkr_config = Mock()
        ibkr_config.host = "localhost"
        ibkr_config.port = 7497
        
        self.mock_config.providers.barchart = barchart_config
        self.mock_config.providers.yahoo = yahoo_config
        self.mock_config.providers.ibkr = ibkr_config
        
        self.mock_config_manager.validate_provider_credentials.return_value = True
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Path')
    def test_show_configuration_basic(self, mock_path, mock_console):
        """Test basic configuration display."""
        self.setup_config_mock()
        
        # Mock assets file checks
        mock_path.return_value.exists.return_value = True
        
        show_configuration(self.mock_config_manager)
        
        # Verify config manager calls
        self.mock_config_manager.load_config.assert_called_once()
        self.mock_config_manager.validate_provider_credentials.assert_called()
        
        # Verify console print was called with tables
        assert mock_console.print.call_count >= 2  # General config table + provider status table
        
        # Verify tables were created by checking call arguments
        print_calls = mock_console.print.call_args_list
        for call in print_calls:
            args = call[0]
            if args and isinstance(args[0], Table):
                assert args[0].title in ["Vortex Configuration", "Provider Status"]
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Path')
    def test_show_configuration_no_assets_files(self, mock_path, mock_console):
        """Test configuration display when no assets files exist."""
        self.setup_config_mock()
        
        # Mock no assets files exist
        mock_path.return_value.exists.return_value = False
        
        show_configuration(self.mock_config_manager)
        
        # Should still display both tables
        assert mock_console.print.call_count >= 2
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Path')
    def test_show_configuration_barchart_no_credentials(self, mock_path, mock_console):
        """Test configuration display when barchart has no credentials."""
        self.setup_config_mock()
        
        # Mock Barchart has no credentials
        self.mock_config_manager.validate_provider_credentials.return_value = False
        mock_path.return_value.exists.return_value = False
        
        show_configuration(self.mock_config_manager)
        
        # Should still display tables with appropriate status
        assert mock_console.print.call_count >= 2


class TestShowProviderConfiguration:
    """Test show_provider_configuration function."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_config_manager = Mock()
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Path')
    def test_show_provider_barchart(self, mock_path, mock_console):
        """Test display of Barchart provider configuration."""
        provider_config = {
            "username": "test@example.com",
            "password": "secret123",
            "daily_limit": 150
        }
        self.mock_config_manager.get_provider_config.return_value = provider_config
        mock_path.return_value.exists.return_value = True
        
        show_provider_configuration(self.mock_config_manager, "barchart")
        
        # Verify provider config was loaded
        self.mock_config_manager.get_provider_config.assert_called_once_with("barchart")
        
        # Verify table was displayed
        mock_console.print.assert_called_once()
        table = mock_console.print.call_args[0][0]
        assert isinstance(table, Table)
        assert table.title == "BARCHART Configuration"
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Path')
    def test_show_provider_yahoo(self, mock_path, mock_console):
        """Test display of Yahoo provider configuration."""
        provider_config = {"enabled": True}
        self.mock_config_manager.get_provider_config.return_value = provider_config
        mock_path.return_value.exists.return_value = False
        
        show_provider_configuration(self.mock_config_manager, "yahoo")
        
        # Verify provider config was loaded
        self.mock_config_manager.get_provider_config.assert_called_once_with("yahoo")
        
        # Verify table was displayed
        mock_console.print.assert_called_once()
        table = mock_console.print.call_args[0][0]
        assert isinstance(table, Table)
        assert table.title == "YAHOO Configuration"
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Path')
    def test_show_provider_ibkr(self, mock_path, mock_console):
        """Test display of IBKR provider configuration."""
        provider_config = {
            "host": "localhost",
            "port": 7497,
            "client_id": 1,
            "timeout": 30
        }
        self.mock_config_manager.get_provider_config.return_value = provider_config
        mock_path.return_value.exists.return_value = True
        
        show_provider_configuration(self.mock_config_manager, "ibkr")
        
        # Verify provider config was loaded
        self.mock_config_manager.get_provider_config.assert_called_once_with("ibkr")
        
        # Verify table was displayed
        mock_console.print.assert_called_once()
        table = mock_console.print.call_args[0][0]
        assert isinstance(table, Table)
        assert table.title == "IBKR Configuration"
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Path')
    def test_show_provider_with_fallback_assets(self, mock_path, mock_console):
        """Test provider display with fallback assets file."""
        provider_config = {}
        self.mock_config_manager.get_provider_config.return_value = provider_config
        
        # Mock specific assets file doesn't exist, but default does
        def mock_exists(path):
            return "default.json" in str(path)
        
        mock_path.return_value.exists.side_effect = mock_exists
        
        show_provider_configuration(self.mock_config_manager, "barchart")
        
        # Should display table
        mock_console.print.assert_called_once()


class TestSetProviderCredentials:
    """Test set_provider_credentials function."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_config_manager = Mock()
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Prompt.ask')
    def test_set_barchart_credentials(self, mock_prompt, mock_console):
        """Test setting Barchart credentials."""
        mock_prompt.side_effect = ["test@example.com", "password123", "150"]
        
        set_provider_credentials(self.mock_config_manager, "barchart")
        
        # Verify prompts were called
        assert mock_prompt.call_count == 3
        from unittest.mock import call
        expected_calls = [
            call("Username (email)"),
            call("Password", password=True),
            call("Daily download limit", default="150")
        ]
        mock_prompt.assert_has_calls(expected_calls)
        
        # Verify config was set
        expected_config = {
            "username": "test@example.com",
            "password": "password123",
            "daily_limit": 150
        }
        self.mock_config_manager.set_provider_config.assert_called_once_with("barchart", expected_config)
        
        # Verify success message
        success_calls = [call for call in mock_console.print.call_args_list 
                        if "✓ BARCHART credentials saved" in str(call)]
        assert len(success_calls) >= 1
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Prompt.ask')
    def test_set_yahoo_credentials(self, mock_prompt, mock_console):
        """Test setting Yahoo credentials (which doesn't need any)."""
        set_provider_credentials(self.mock_config_manager, "yahoo")
        
        # Yahoo doesn't prompt for credentials
        mock_prompt.assert_not_called()
        
        # Verify config was set to enable Yahoo
        expected_config = {"enabled": True}
        self.mock_config_manager.set_provider_config.assert_called_once_with("yahoo", expected_config)
        
        # Verify info message about no credentials needed
        info_calls = [call for call in mock_console.print.call_args_list 
                     if "Yahoo Finance doesn't require credentials" in str(call)]
        assert len(info_calls) >= 1
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Prompt.ask')
    def test_set_ibkr_credentials(self, mock_prompt, mock_console):
        """Test setting IBKR credentials."""
        mock_prompt.side_effect = ["localhost", "7497", "1", "30"]
        
        set_provider_credentials(self.mock_config_manager, "ibkr")
        
        # Verify prompts were called
        assert mock_prompt.call_count == 4
        from unittest.mock import call
        expected_calls = [
            call("Host", default="localhost"),
            call("Port", default="7497"),
            call("Client ID", default="1"),
            call("Timeout (seconds)", default="30")
        ]
        mock_prompt.assert_has_calls(expected_calls)
        
        # Verify config was set
        expected_config = {
            "host": "localhost",
            "port": 7497,
            "client_id": 1,
            "timeout": 30
        }
        self.mock_config_manager.set_provider_config.assert_called_once_with("ibkr", expected_config)
        
        # Verify success message
        success_calls = [call for call in mock_console.print.call_args_list 
                        if "✓ IBKR credentials saved" in str(call)]
        assert len(success_calls) >= 1


class TestConfigCommandIntegration:
    """Integration tests for config command components."""
    
    @patch('vortex.cli.commands.config.console')
    @patch('vortex.cli.commands.config.Path')
    def test_config_display_with_all_providers(self, mock_path, mock_console):
        """Test configuration display covering all provider types."""
        mock_config_manager = Mock()
        mock_config = Mock()
        
        # Setup comprehensive config
        mock_config.general.output_directory = "/data"
        mock_config.general.default_provider = Provider.BARCHART
        mock_config.general.backup_enabled = False
        mock_config.general.log_level = LogLevel.DEBUG
        
        barchart_config = Mock()
        barchart_config.daily_limit = 200
        yahoo_config = Mock()
        ibkr_config = Mock()
        ibkr_config.host = "127.0.0.1"
        ibkr_config.port = 7496
        
        mock_config.providers.barchart = barchart_config
        mock_config.providers.yahoo = yahoo_config
        mock_config.providers.ibkr = ibkr_config
        
        mock_config_manager.load_config.return_value = mock_config
        mock_config_manager.config_file = "/custom/config.toml"
        mock_config_manager.validate_provider_credentials.side_effect = lambda p: p == "barchart"
        
        # Mock various assets file scenarios
        def mock_exists(path):
            return "barchart.json" in str(path) or "default.json" in str(path)
        
        mock_path.return_value.exists.side_effect = mock_exists
        
        show_configuration(mock_config_manager)
        
        # Verify all expected interactions occurred
        mock_config_manager.load_config.assert_called_once()
        assert mock_config_manager.validate_provider_credentials.call_count >= 1
        assert mock_console.print.call_count >= 2