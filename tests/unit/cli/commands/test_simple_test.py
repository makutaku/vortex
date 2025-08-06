"""Tests for simple_test command."""

import pytest
from click.testing import CliRunner

from vortex.cli.commands.simple_test import simple_test as simple_test_command


class TestSimpleTestCommand:
    """Test cases for simple test command."""

    def test_simple_test_command_success(self):
        """Test that simple test command executes successfully."""
        runner = CliRunner()
        result = runner.invoke(simple_test_command)
        
        assert result.exit_code == 0
        assert "✓ CLI is working correctly!" in result.output
        assert "Install full dependencies to use all features:" in result.output
        assert "pip install click rich tomli tomli-w" in result.output

    def test_simple_test_command_output_format(self):
        """Test the specific output format of the simple test command."""
        runner = CliRunner()
        result = runner.invoke(simple_test_command)
        
        lines = result.output.strip().split('\n')
        assert len(lines) == 3
        assert lines[0] == "✓ CLI is working correctly!"
        assert lines[1] == "Install full dependencies to use all features:"
        assert lines[2] == "  pip install click rich tomli tomli-w"

    def test_simple_test_command_no_arguments(self):
        """Test that simple test command works without any arguments."""
        runner = CliRunner()
        result = runner.invoke(simple_test_command, [])
        
        assert result.exit_code == 0
        assert "✓ CLI is working correctly!" in result.output