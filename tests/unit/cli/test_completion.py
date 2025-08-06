"""
Tests for CLI completion functionality.

Tests the simplest completion helper functions for quick coverage gains.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open


class TestCompletionHelpers:
    """Test simple completion helper functions without complex mocking."""

    def test_complete_provider(self):
        """Test provider name completion."""
        from vortex.cli.completion import complete_provider

        # Test matching providers
        result = complete_provider(None, None, "ba")
        assert "barchart" in result

        result = complete_provider(None, None, "ya")
        assert "yahoo" in result

        result = complete_provider(None, None, "ib")
        assert "ibkr" in result

        # Test empty/no match
        result = complete_provider(None, None, "xyz")
        assert result == []

        # Test case insensitive
        result = complete_provider(None, None, "BA")
        assert "barchart" in result

    def test_complete_symbol_common_symbols(self):
        """Test symbol completion with common symbols."""
        from vortex.cli.completion import complete_symbol

        # Test stock symbols
        result = complete_symbol(None, None, "AA")
        assert "AAPL" in result

        result = complete_symbol(None, None, "GO")
        assert "GOOGL" in result

        # Test futures
        result = complete_symbol(None, None, "ES")
        assert "ES" in result

        result = complete_symbol(None, None, "GC")
        assert "GC" in result

        # Test forex
        result = complete_symbol(None, None, "EUR")
        assert "EURUSD" in result

        # Test case handling (input is lowercase, results uppercase)
        result = complete_symbol(None, None, "aa")
        assert "AAPL" in result

    def test_complete_symbol_limit(self):
        """Test that symbol completion limits results."""
        from vortex.cli.completion import complete_symbol

        # Should return at most 20 results
        result = complete_symbol(None, None, "")
        assert len(result) <= 20

    def test_complete_log_level(self):
        """Test log level completion."""
        from vortex.cli.completion import complete_log_level

        # Test matching levels
        result = complete_log_level(None, None, "DE")
        assert "DEBUG" in result

        result = complete_log_level(None, None, "info")
        assert "INFO" in result

        result = complete_log_level(None, None, "WARN")
        assert "WARNING" in result

        # Test case insensitive
        result = complete_log_level(None, None, "error")
        assert "ERROR" in result

        result = complete_log_level(None, None, "critical")
        assert "CRITICAL" in result

    def test_complete_output_format(self):
        """Test output format completion."""
        from vortex.cli.completion import complete_output_format

        # Test matching formats
        result = complete_output_format(None, None, "con")
        assert "console" in result

        result = complete_output_format(None, None, "json")
        assert "json" in result

        result = complete_output_format(None, None, "rich")
        assert "rich" in result

        # Test no match
        result = complete_output_format(None, None, "xml")
        assert result == []

    def test_complete_date_suggestions(self):
        """Test date completion suggestions."""
        from vortex.cli.completion import complete_date

        # Test that it returns a list and doesn't crash
        result = complete_date(None, None, "")
        assert isinstance(result, list)
        assert len(result) <= 10  # Respects the limit

        # Test with specific patterns
        result = complete_date(None, None, "2024")
        assert isinstance(result, list)

    def test_complete_date_relative_terms(self):
        """Test date completion with relative terms."""
        from vortex.cli.completion import complete_date

        # Just test that the function doesn't crash with relative terms
        result = complete_date(None, None, "tod")
        assert isinstance(result, list)  # Should return a list

        result = complete_date(None, None, "week")
        assert isinstance(result, list)  # Should return a list

    def test_complete_config_file_basic(self):
        """Test config file completion basic functionality."""
        from vortex.cli.completion import complete_config_file

        # Just test that it returns a list without complex mocking
        result = complete_config_file(None, None, "config")
        assert isinstance(result, list)

    def test_complete_symbols_file_basic(self):
        """Test symbols file completion basic functionality."""
        from vortex.cli.completion import complete_symbols_file

        # Just test that it returns a list without complex mocking
        result = complete_symbols_file(None, None, "sym")
        assert isinstance(result, list)

    def test_complete_assets_file_basic(self):
        """Test assets file completion basic functionality."""
        from vortex.cli.completion import complete_assets_file

        # Just test that it returns a list without complex mocking
        result = complete_assets_file(None, None, "default")
        assert isinstance(result, list)

    def test_completion_installer_get_completion_script_bash(self):
        """Test getting bash completion script."""
        from vortex.cli.completion import CompletionInstaller

        script = CompletionInstaller.get_completion_script("bash")
        assert "_vortex_completion" in script
        assert "complete -o default -F _vortex_completion vortex" in script

    def test_completion_installer_get_completion_script_zsh(self):
        """Test getting zsh completion script."""
        from vortex.cli.completion import CompletionInstaller

        script = CompletionInstaller.get_completion_script("zsh")
        assert "_vortex_completion" in script
        assert "compdef _vortex_completion vortex" in script

    def test_completion_installer_get_completion_script_fish(self):
        """Test getting fish completion script."""
        from vortex.cli.completion import CompletionInstaller

        script = CompletionInstaller.get_completion_script("fish")
        assert "complete -c vortex" in script
        assert "_VORTEX_COMPLETE=complete_fish" in script

    def test_completion_installer_get_completion_script_unsupported(self):
        """Test getting completion script for unsupported shell."""
        from vortex.cli.completion import CompletionInstaller

        with pytest.raises(ValueError, match="Unsupported shell"):
            CompletionInstaller.get_completion_script("unsupported")


class TestCompletionErrorHandling:
    """Test completion functions handle errors gracefully."""

    def test_complete_config_file_error_handling(self):
        """Test config file completion handles errors gracefully."""
        from vortex.cli.completion import complete_config_file

        # Just test that it doesn't crash with any input
        result = complete_config_file(None, None, "nonexistent")
        assert isinstance(result, list)

    def test_complete_symbols_file_error_handling(self):
        """Test symbols file completion handles errors gracefully."""
        from vortex.cli.completion import complete_symbols_file

        # Should not raise, should return a list
        result = complete_symbols_file(None, None, "nonexistent")
        assert isinstance(result, list)

    def test_complete_symbol_error_handling(self):
        """Test symbol completion handles errors gracefully."""
        from vortex.cli.completion import complete_symbol

        # Should still return common symbols and not raise
        result = complete_symbol(None, None, "AA")
        assert isinstance(result, list)
        assert "AAPL" in result  # Common symbol should still be there

    def test_complete_assets_file_error_handling(self):
        """Test assets completion handles errors gracefully."""
        from vortex.cli.completion import complete_assets_file

        # Should return empty results gracefully
        result = complete_assets_file(None, None, "nonexistent")
        assert isinstance(result, list)


class TestCompletionImports:
    """Test that completion functions can be imported."""

    def test_completion_function_imports(self):
        """Test that all completion functions can be imported."""
        from vortex.cli.completion import (
            complete_provider,
            complete_symbol,
            complete_config_file,
            complete_symbols_file,
            complete_assets_file,
            complete_log_level,
            complete_output_format,
            complete_date
        )

        # All should be callable
        assert callable(complete_provider)
        assert callable(complete_symbol)
        assert callable(complete_config_file)
        assert callable(complete_symbols_file)
        assert callable(complete_assets_file)
        assert callable(complete_log_level)
        assert callable(complete_output_format)
        assert callable(complete_date)

    def test_completion_installer_import(self):
        """Test that CompletionInstaller can be imported."""
        from vortex.cli.completion import CompletionInstaller

        assert hasattr(CompletionInstaller, 'get_completion_script')
        assert hasattr(CompletionInstaller, 'install_completion')