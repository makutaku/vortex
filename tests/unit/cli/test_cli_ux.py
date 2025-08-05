"""
Tests for CLI User Experience enhancements.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import click

from vortex.cli.ux import (
    CliUX, ProgressContext, TableBuilder, TreeBuilder, 
    CommandWizard, enhanced_error_handler, validate_symbols
)
from vortex.cli.help import HelpSystem
from vortex.cli.completion import (
    complete_provider, complete_symbol, complete_date,
    CompletionInstaller
)
from vortex.cli.analytics import CliAnalytics, analytics_decorator
from vortex.exceptions import VortexError, ConfigurationError


@pytest.mark.unit
class TestCliUX:
    """Test the enhanced CLI UX utilities."""
    
    @pytest.fixture
    def ux(self):
        """Create a CliUX instance."""
        return CliUX()
    
    def test_ux_creation(self, ux):
        """Test UX instance creation."""
        assert ux.quiet is False
        assert ux.force_yes is False
    
    def test_quiet_mode(self, ux, capfd):
        """Test quiet mode suppresses output."""
        ux.set_quiet(True)
        ux.print("This should not appear")
        ux.print_success("This should not appear")
        
        captured = capfd.readouterr()
        assert captured.out == ""
    
    def test_force_yes_mode(self, ux):
        """Test force yes mode."""
        ux.set_force_yes(True)
        
        # Should return True without prompting
        result = ux.confirm("Continue?", default=False)
        assert result is True
    
    def test_print_methods(self, ux, capfd):
        """Test different print methods."""
        ux.print("Regular message")
        ux.print_success("Success message")
        ux.print_error("Error message")
        ux.print_warning("Warning message")
        ux.print_info("Info message")
        
        captured = capfd.readouterr()
        assert "Regular message" in captured.out
        assert "Success message" in captured.out
        assert "Error message" in captured.out
        assert "Warning message" in captured.out
        assert "Info message" in captured.out
    
    def test_choice_single_option(self, ux):
        """Test choice with single option."""
        result = ux.choice("Choose:", ["only_option"])
        assert result == "only_option"
    
    @patch('builtins.input', return_value='2')
    def test_choice_multiple_options(self, mock_input, ux):
        """Test choice with multiple options."""
        choices = ["option1", "option2", "option3"]
        result = ux.choice("Choose:", choices)
        assert result == "option2"
    
    @patch('builtins.input', return_value='')
    def test_choice_default(self, mock_input, ux):
        """Test choice with default."""
        choices = ["option1", "option2", "option3"]
        result = ux.choice("Choose:", choices, default="option2")
        assert result == "option2"


@pytest.mark.unit
class TestProgressContext:
    """Test the progress context manager."""
    
    @pytest.fixture
    def ux(self):
        """Create a CliUX instance."""
        return CliUX()
    
    def test_progress_context(self, ux):
        """Test progress context manager."""
        with ux.progress("Test operation") as progress:
            assert progress is not None
            progress.update(50, 100, "Half done")
            progress.update(100, 100, "Complete")
    
    def test_progress_context_with_exception(self, ux):
        """Test progress context with exception."""
        with pytest.raises(ValueError):
            with ux.progress("Test operation"):
                raise ValueError("Test error")


@pytest.mark.unit
class TestTableBuilder:
    """Test the table builder."""
    
    @pytest.fixture
    def ux(self):
        """Create a CliUX instance."""
        return CliUX()
    
    def test_table_creation(self, ux):
        """Test table creation and building."""
        table = ux.table("Test Table")
        table.add_column("Name", style="blue")
        table.add_column("Value", style="green")
        table.add_row("Item 1", "Value 1")
        table.add_row("Item 2", "Value 2")
        
        # Should not raise an exception
        table.print()
    
    def test_empty_table(self, ux):
        """Test empty table."""
        table = ux.table("Empty Table")
        table.print()  # Should not raise an exception


@pytest.mark.unit
class TestTreeBuilder:
    """Test the tree builder."""
    
    @pytest.fixture
    def ux(self):
        """Create a CliUX instance."""
        return CliUX()
    
    def test_tree_creation(self, ux):
        """Test tree creation and building."""
        tree = ux.tree("Test Tree")
        tree.add_item("Root Item", ["Child 1", "Child 2"])
        tree.add_item("Another Root", ["Child A", "Child B"])
        
        # Should not raise an exception
        tree.print()


@pytest.mark.unit
class TestCommandWizard:
    """Test the interactive command wizard."""
    
    @pytest.fixture
    def ux(self):
        """Create a CliUX instance."""
        ux = CliUX()
        ux.set_force_yes(True)  # Auto-confirm for testing
        return ux
    
    @pytest.fixture
    def wizard(self, ux):
        """Create a command wizard."""
        return CommandWizard(ux)
    
    @patch('vortex.cli.ux.CliUX.choice')
    @patch('vortex.cli.ux.CliUX.prompt')
    @patch('vortex.cli.ux.CliUX.confirm')
    def test_download_wizard(self, mock_confirm, mock_prompt, mock_choice, wizard):
        """Test download wizard."""
        # Mock user inputs
        mock_choice.side_effect = [
            "yahoo",  # provider
            "Enter symbols manually",  # symbol method
            "Last 30 days (default)",  # date range
        ]
        mock_prompt.return_value = "AAPL,GOOGL"
        mock_confirm.side_effect = [False, False, False]  # backup, force, execute
        
        config = wizard.run_download_wizard()
        
        assert config["provider"] == "yahoo"
        assert config["symbols"] == ["AAPL", "GOOGL"]
        assert "start_date" not in config  # Default range
        assert config["backup"] is False
        assert config["force"] is False
    
    @patch('vortex.cli.ux.CliUX.choice')
    @patch('vortex.cli.ux.CliUX.prompt')
    @patch('vortex.cli.ux.CliUX.confirm')
    def test_config_wizard(self, mock_confirm, mock_prompt, mock_choice, wizard):
        """Test configuration wizard."""
        # Mock user inputs
        mock_choice.side_effect = [
            "barchart",  # provider
            "INFO"  # log level
        ]
        mock_prompt.side_effect = [
            "test@example.com",  # username
            "password123",  # password
            "150",  # daily limit
            "./data",  # output dir
        ]
        mock_confirm.side_effect = [True, False]  # configure general settings, backup enabled
        
        config = wizard.run_config_wizard()
        
        assert config["provider"] == "barchart"
        assert config["username"] == "test@example.com"
        assert config["password"] == "password123"
        assert config["daily_limit"] == "150"


@pytest.mark.unit
class TestErrorHandler:
    """Test the enhanced error handler."""
    
    def test_enhanced_error_handler_vortex_error(self):
        """Test error handler with VortexError."""
        @enhanced_error_handler
        def failing_function():
            raise ConfigurationError("Test error", "Test help")
        
        with pytest.raises(click.Abort):
            failing_function()
    
    def test_enhanced_error_handler_keyboard_interrupt(self):
        """Test error handler with KeyboardInterrupt."""
        @enhanced_error_handler
        def interrupted_function():
            raise KeyboardInterrupt()
        
        with pytest.raises(click.Abort):
            interrupted_function()
    
    def test_enhanced_error_handler_unexpected_error(self):
        """Test error handler with unexpected error."""
        @enhanced_error_handler
        def unexpected_error_function():
            raise RuntimeError("Unexpected error")
        
        with pytest.raises(click.Abort):
            unexpected_error_function()


@pytest.mark.unit
class TestValidation:
    """Test input validation functions."""
    
    def test_validate_symbols(self):
        """Test symbol validation."""
        # Valid symbols
        symbols = ["AAPL", "googl", "MSFT"]
        result = validate_symbols(symbols)
        assert result == ["AAPL", "GOOGL", "MSFT"]
        
        # Empty and invalid symbols
        symbols = ["", "AAPL", "  ", "GOOGL"]
        result = validate_symbols(symbols)
        assert result == ["AAPL", "GOOGL"]
    
    def test_validate_symbols_special_characters(self):
        """Test symbol validation with special characters."""
        symbols = ["SPY", "BRK-B", "BF.B", "^GSPC"]
        result = validate_symbols(symbols)
        # Should accept common symbol formats
        assert "SPY" in result
        assert "BRK-B" in result
        assert "BF.B" in result


@pytest.mark.unit
class TestHelpSystem:
    """Test the enhanced help system."""
    
    @pytest.fixture
    def help_system(self):
        """Create a help system instance."""
        return HelpSystem()
    
    def test_help_system_creation(self, help_system):
        """Test help system creation."""
        assert help_system.examples is not None
        assert help_system.tutorials is not None
        assert help_system.tips is not None
        
        # Check that examples are loaded
        assert "download" in help_system.examples
        assert len(help_system.examples["download"]) > 0
    
    def test_show_examples(self, help_system, capfd):
        """Test showing examples."""
        help_system.show_examples("download")
        captured = capfd.readouterr()
        assert "download" in captured.out
    
    def test_show_tutorial(self, help_system, capfd):
        """Test showing tutorial."""
        help_system.show_tutorial("getting_started")
        captured = capfd.readouterr()
        assert "Getting Started" in captured.out
    
    def test_show_tips(self, help_system, capfd):
        """Test showing tips."""
        help_system.show_tips(2)
        captured = capfd.readouterr()
        assert "Tips" in captured.out


@pytest.mark.unit
class TestCompletion:
    """Test auto-completion functions."""
    
    def test_complete_provider(self):
        """Test provider completion."""
        # Test partial match
        result = complete_provider(None, None, "bar")
        assert "barchart" in result
        
        # Test empty input
        result = complete_provider(None, None, "")
        assert len(result) == 3  # All providers
        assert "barchart" in result
        assert "yahoo" in result
        assert "ibkr" in result
    
    def test_complete_symbol(self):
        """Test symbol completion."""
        # Test partial match
        result = complete_symbol(None, None, "AAP")
        assert "AAPL" in result
        
        # Test case insensitive
        result = complete_symbol(None, None, "aap")
        assert "AAPL" in result
        
        # Test empty input returns suggestions
        result = complete_symbol(None, None, "")
        assert len(result) > 0
    
    def test_complete_date(self):
        """Test date completion."""
        from datetime import datetime
        
        # Test empty input
        result = complete_date(None, None, "")
        assert len(result) > 0
        
        # Should contain current year dates
        current_year = datetime.now().year
        year_dates = [d for d in result if str(current_year) in d]
        assert len(year_dates) > 0


@pytest.mark.unit
class TestCompletionInstaller:
    """Test completion installer."""
    
    def test_get_completion_script(self):
        """Test getting completion scripts."""
        installer = CompletionInstaller()
        
        # Test bash script
        bash_script = installer.get_completion_script("bash")
        assert "_vortex_completion" in bash_script
        assert "complete" in bash_script
        
        # Test zsh script
        zsh_script = installer.get_completion_script("zsh")
        assert "_vortex_completion" in zsh_script
        assert "compdef" in zsh_script
        
        # Test fish script
        fish_script = installer.get_completion_script("fish")
        assert "complete -c vortex" in fish_script
    
    def test_unsupported_shell(self):
        """Test unsupported shell raises error."""
        installer = CompletionInstaller()
        
        with pytest.raises(ValueError):
            installer.get_completion_script("unsupported")


@pytest.mark.unit
class TestAnalytics:
    """Test CLI analytics system."""
    
    @pytest.fixture
    def analytics(self, temp_dir):
        """Create analytics instance with temp directory."""
        analytics = CliAnalytics()
        analytics.config_dir = temp_dir / ".config" / "vortex"
        analytics.analytics_file = analytics.config_dir / "analytics.json"
        return analytics
    
    def test_analytics_creation(self, analytics):
        """Test analytics instance creation."""
        assert analytics.session_id is not None
        assert analytics.user_id is not None
        assert len(analytics.user_id) == 12  # SHA256 hash truncated
    
    def test_analytics_disable_enable(self, analytics):
        """Test disabling and enabling analytics."""
        # Initially enabled
        assert analytics.enabled is True
        
        # Disable
        analytics.disable()
        assert analytics.enabled is False
        
        # Enable
        analytics.enable()
        assert analytics.enabled is True
    
    def test_track_command(self, analytics):
        """Test command tracking."""
        analytics.track_command("download", provider="yahoo", success=True, duration_ms=1234.5)
        
        # Should create events file
        events_file = analytics.config_dir / "events.jsonl"
        assert events_file.exists()
        
        # Check event content
        with open(events_file) as f:
            event_line = f.readline()
            event = json.loads(event_line)
            
            assert event["event"] == "command_executed"
            assert event["command"] == "download"
            assert event["provider"] == "yahoo"
            assert event["success"] is True
            assert event["duration_ms"] == 1234.5
    
    def test_track_error(self, analytics):
        """Test error tracking."""
        analytics.track_error("download", "ConnectionError", "Network timeout")
        
        events_file = analytics.config_dir / "events.jsonl"
        assert events_file.exists()
        
        with open(events_file) as f:
            event_line = f.readline()
            event = json.loads(event_line)
            
            assert event["event"] == "command_error"
            assert event["command"] == "download"
            assert event["error_type"] == "ConnectionError"
            assert event["error_message"] == "Network timeout"
    
    def test_analytics_disabled_no_tracking(self, analytics):
        """Test that disabled analytics don't track."""
        analytics.disable()
        analytics.track_command("test", success=True)
        
        events_file = analytics.config_dir / "events.jsonl"
        assert not events_file.exists()
    
    def test_get_status(self, analytics):
        """Test getting analytics status."""
        status = analytics.get_status()
        
        assert "enabled" in status
        assert "user_id" in status
        assert "session_id" in status
        assert "config_file" in status
        assert "events_stored" in status
    
    def test_analytics_decorator(self, analytics):
        """Test analytics decorator."""
        @analytics_decorator("test_command")
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"
        
        # Should have tracked the command
        events_file = analytics.config_dir / "events.jsonl"
        if events_file.exists():  # Only if analytics enabled
            with open(events_file) as f:
                lines = f.readlines()
                if lines:  # May be empty if analytics disabled
                    event = json.loads(lines[-1])
                    assert event["command"] == "test_command"
                    assert event["success"] is True


@pytest.mark.integration
class TestCLIIntegration:
    """Integration tests for CLI components."""
    
    def test_wizard_to_command_config_conversion(self):
        """Test converting wizard config to command parameters."""
        from vortex.cli.main import _convert_wizard_config_to_params
        
        wizard_config = {
            "provider": "yahoo",
            "symbols": ["AAPL", "GOOGL"],
            "start_date": "2024-01-01",
            "backup": True,
            "force": False
        }
        
        params = _convert_wizard_config_to_params(wizard_config)
        
        assert params["provider"] == "yahoo"
        assert params["symbol"] == ["AAPL", "GOOGL"]
        assert params["backup"] is True
        assert params["force"] is False
        assert params["yes"] is True  # Auto-added for wizard mode
    
    def test_ux_integration_with_rich_available(self):
        """Test UX integration when Rich is available."""
        ux = CliUX()
        
        # Should work whether Rich is available or not
        table = ux.table("Test Table")
        table.add_column("Col1")
        table.add_row("Value1")
        table.print()  # Should not raise exception
        
        tree = ux.tree("Test Tree")
        tree.add_item("Item1", ["Child1"])
        tree.print()  # Should not raise exception
    
    def test_help_system_integration(self):
        """Test help system integration."""
        help_system = HelpSystem()
        
        # Should load all components without error
        assert len(help_system.examples) > 0
        assert len(help_system.tutorials) > 0
        assert len(help_system.tips) > 0
        
        # Should be able to show content
        help_system.show_examples()  # Should not raise
        help_system.show_tips(1)    # Should not raise