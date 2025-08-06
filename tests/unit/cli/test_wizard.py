"""
Tests for CLI wizard functionality.

Tests the simplest functions in the wizard module for quick coverage gains.
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch


class TestWizardUtilities:
    """Test wizard utility functions without complex mocking."""

    def test_convert_wizard_config_to_params_basic(self):
        """Test _convert_wizard_config_to_params with basic config."""
        from vortex.cli.wizard import _convert_wizard_config_to_params

        config = {
            "provider": "yahoo",
            "symbols": ["AAPL", "GOOGL"]
        }

        params = _convert_wizard_config_to_params(config)

        assert params["provider"] == "yahoo"
        assert params["symbol"] == ["AAPL", "GOOGL"]
        assert params["chunk_size"] == 30
        assert params["yes"] is True
        assert "assets" not in params  # None values filtered out

    def test_convert_wizard_config_to_params_with_dates(self):
        """Test _convert_wizard_config_to_params with date strings."""
        from vortex.cli.wizard import _convert_wizard_config_to_params

        config = {
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        }

        params = _convert_wizard_config_to_params(config)

        assert params["start_date"] == datetime(2024, 1, 1)
        assert params["end_date"] == datetime(2024, 12, 31)

    def test_convert_wizard_config_to_params_with_file_path(self):
        """Test _convert_wizard_config_to_params with symbols file."""
        from vortex.cli.wizard import _convert_wizard_config_to_params

        config = {
            "symbols_file": "/path/to/symbols.txt"
        }

        params = _convert_wizard_config_to_params(config)

        assert isinstance(params["symbols_file"], Path)
        assert str(params["symbols_file"]) == "/path/to/symbols.txt"

    def test_convert_wizard_config_to_params_with_flags(self):
        """Test _convert_wizard_config_to_params with boolean flags."""
        from vortex.cli.wizard import _convert_wizard_config_to_params

        config = {
            "backup": True,
            "force": False
        }

        params = _convert_wizard_config_to_params(config)

        assert params["backup"] is True
        assert params["force"] is False  # False values are kept, only None filtered out

    def test_convert_wizard_config_to_params_filters_none(self):
        """Test that None values are properly filtered out."""
        from vortex.cli.wizard import _convert_wizard_config_to_params

        config = {
            "provider": None,
            "symbols": ["AAPL"],
            "start_date": None,
            "backup": True
        }

        params = _convert_wizard_config_to_params(config)

        # None values should be filtered out
        assert "provider" not in params
        assert "start_date" not in params
        # Valid values should remain
        assert params["symbol"] == ["AAPL"]
        assert params["backup"] is True

    def test_convert_wizard_config_to_params_empty_config(self):
        """Test _convert_wizard_config_to_params with empty config."""
        from vortex.cli.wizard import _convert_wizard_config_to_params

        config = {}

        params = _convert_wizard_config_to_params(config)

        # Should have default values for all non-None fields
        assert params["chunk_size"] == 30
        assert params["yes"] is True
        assert params["symbol"] == []  # Default empty list
        assert params["backup"] is False  # Default False
        assert params["force"] is False  # Default False
        # None values should be filtered out
        assert "provider" not in params
        assert "symbols_file" not in params
        assert "assets" not in params
        assert "start_date" not in params
        assert "end_date" not in params
        assert "output_dir" not in params

    def test_convert_wizard_config_to_params_date_none_handling(self):
        """Test date handling when dates are None or empty."""
        from vortex.cli.wizard import _convert_wizard_config_to_params

        config = {
            "start_date": "",  # Empty string
            "end_date": None   # None value
        }

        params = _convert_wizard_config_to_params(config)

        # Empty/None dates should be filtered out
        assert "start_date" not in params
        assert "end_date" not in params

    def test_convert_wizard_config_to_params_symbols_file_none(self):
        """Test symbols_file handling when None."""
        from vortex.cli.wizard import _convert_wizard_config_to_params

        config = {
            "symbols_file": None
        }

        params = _convert_wizard_config_to_params(config)

        # None symbols_file should be filtered out
        assert "symbols_file" not in params


class TestWizardCommandImports:
    """Test wizard command imports and basic functionality."""

    def test_wizard_command_import(self):
        """Test that wizard_command can be imported."""
        from vortex.cli.wizard import wizard_command
        assert callable(wizard_command)

    def test_convert_wizard_config_import(self):
        """Test that _convert_wizard_config_to_params can be imported."""
        from vortex.cli.wizard import _convert_wizard_config_to_params
        assert callable(_convert_wizard_config_to_params)


class TestWizardCommandMocked:
    """Test wizard command with minimal mocking."""

    @patch('vortex.cli.wizard.get_ux')
    def test_wizard_command_exit_action(self, mock_get_ux):
        """Test wizard command when user selects exit."""
        from vortex.cli.wizard import wizard_command
        from unittest.mock import Mock

        # Setup mocks
        mock_ux = Mock()
        mock_get_ux.return_value = mock_ux
        mock_ux.choice.return_value = "Exit"  # User selects exit

        mock_ctx = Mock()

        # Call wizard command
        wizard_command(mock_ctx)

        # Should call UX methods
        mock_ux.print_panel.assert_called_once()
        mock_ux.choice.assert_called_once()
        mock_ux.print.assert_called_once_with("👋 Goodbye!")

    @patch('vortex.cli.wizard.get_ux')
    @patch('vortex.cli.wizard.CommandWizard')
    def test_wizard_command_view_help_action(self, mock_command_wizard_class, mock_get_ux):
        """Test wizard command when user selects view help."""
        from vortex.cli.wizard import wizard_command

        # Setup mocks
        mock_ux = Mock()
        mock_get_ux.return_value = mock_ux
        mock_ux.choice.return_value = "View help"

        mock_command_wizard = Mock()
        mock_command_wizard_class.return_value = mock_command_wizard

        mock_ctx = Mock()

        with patch('vortex.cli.help.get_help_system') as mock_get_help:
            mock_help_system = Mock()
            mock_get_help.return_value = mock_help_system

            # Call wizard command
            wizard_command(mock_ctx)

            # Should call help system
            mock_get_help.assert_called_once()
            mock_help_system.show_quick_start.assert_called_once()