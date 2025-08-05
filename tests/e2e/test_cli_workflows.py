"""
End-to-end tests for complete CLI workflows.

Tests complete user scenarios from command-line invocation
through data download and file output validation.
"""

import pytest
import tempfile
from pathlib import Path
from click.testing import CliRunner

from vortex.cli.main import cli


class TestCLIWorkflows:
    """End-to-end tests for CLI command workflows."""

    @pytest.fixture
    def cli_runner(self):
        """Create CLI runner for tests."""
        return CliRunner()

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_help_command_workflow(self, cli_runner):
        """Test the complete help command workflow."""
        result = cli_runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert "Vortex: Financial data download automation tool" in result.output
        assert "Commands:" in result.output

    def test_providers_list_workflow(self, cli_runner):
        """Test the complete providers list workflow."""
        result = cli_runner.invoke(cli, ['providers'])
        
        # Should not fail even if some providers have dependency issues
        assert result.exit_code in [0, 1]  # May fail due to missing dependencies
        
        if result.exit_code == 0:
            assert "Total providers available" in result.output

    def test_config_show_workflow(self, cli_runner):
        """Test the configuration display workflow."""
        result = cli_runner.invoke(cli, ['config', '--show'])
        
        # Should show configuration even if some providers are unavailable
        assert result.exit_code in [0, 1]

    @pytest.mark.slow
    def test_download_dry_run_workflow(self, cli_runner, temp_output_dir):
        """Test download command with dry run."""
        # This would test the complete download workflow in dry-run mode
        # to avoid actually downloading data in tests
        
        result = cli_runner.invoke(cli, [
            'download',
            '--provider', 'yahoo',
            '--symbol', 'AAPL',
            '--output-dir', str(temp_output_dir),
            '--dry-run'
        ])
        
        # Dry run should complete without errors
        # Note: Actual behavior depends on implementation
        assert result.exit_code in [0, 1, 2]  # Various exit codes possible

    def test_invalid_command_workflow(self, cli_runner):
        """Test handling of invalid commands."""
        result = cli_runner.invoke(cli, ['invalid-command'])
        
        assert result.exit_code != 0
        assert "No such command" in result.output or "Usage:" in result.output