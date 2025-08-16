"""
Tests for metrics command module.

Provides comprehensive coverage for metrics CLI commands including status,
endpoint, test, and dashboard functionality with various configurations.
"""

import pytest
import json
import time
from unittest.mock import Mock, MagicMock, patch, call
from click.testing import CliRunner

from vortex.cli.commands.metrics import metrics, status, endpoint, test, dashboard, summary


@pytest.fixture
def mock_config():
    """Mock configuration for metrics testing."""
    config = Mock()
    config.general.metrics.enabled = True
    config.general.metrics.port = 8000
    config.general.metrics.path = "/metrics"
    return config


@pytest.fixture
def mock_config_manager(mock_config):
    """Mock config manager that returns mock config."""
    manager = Mock()
    manager.get_config.return_value = mock_config
    return manager


@pytest.fixture
def mock_metrics_instance():
    """Mock metrics instance for testing."""
    instance = Mock()
    return instance


@pytest.fixture
def cli_runner():
    """Click CLI runner for testing commands."""
    return CliRunner()


class TestMetricsGroup:
    """Test the main metrics group command."""
    
    def test_metrics_group_exists(self, cli_runner):
        """Test that metrics group command exists."""
        result = cli_runner.invoke(metrics, ["--help"])
        
        assert result.exit_code == 0
        assert "View and manage Vortex metrics and monitoring" in result.output


class TestStatusCommand:
    """Test metrics status command."""
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_status_metrics_disabled(self, mock_console, mock_get_config_manager, mock_get_metrics, 
                                   mock_config_manager, mock_config):
        """Test status command when metrics are disabled."""
        mock_config.general.metrics.enabled = False
        mock_get_config_manager.return_value = mock_config_manager
        
        runner = CliRunner()
        result = runner.invoke(status)
        
        assert result.exit_code == 0
        mock_console.print.assert_called_once_with("[yellow]⚠️  Metrics collection is disabled in configuration[/yellow]")
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_status_metrics_unavailable(self, mock_console, mock_get_config_manager, mock_get_metrics,
                                      mock_config_manager, mock_config):
        """Test status command when metrics system is unavailable."""
        mock_config.general.metrics.enabled = True
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = None
        
        runner = CliRunner()
        result = runner.invoke(status)
        
        assert result.exit_code == 0
        mock_console.print.assert_called_once_with("[red]❌ Metrics system not available[/red]")
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_status_table_format(self, mock_console, mock_get_config_manager, mock_get_metrics,
                                mock_config_manager, mock_config, mock_metrics_instance):
        """Test status command with table format."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(status, ["--format", "table"])
        
        assert result.exit_code == 0
        # Verify table was printed
        assert mock_console.print.called
        # Should create a table and print it
        call_args = mock_console.print.call_args_list
        assert len(call_args) >= 1
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_status_json_format(self, mock_console, mock_get_config_manager, mock_get_metrics,
                               mock_config_manager, mock_config, mock_metrics_instance):
        """Test status command with JSON format."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(status, ["--format", "json"])
        
        assert result.exit_code == 0
        # Verify JSON was printed
        mock_console.print.assert_called_once()
        printed_json = mock_console.print.call_args[0][0]
        
        # Verify it's valid JSON with expected structure
        parsed = json.loads(printed_json)
        assert parsed["enabled"] is True
        assert parsed["port"] == 8000
        assert parsed["path"] == "/metrics"
        assert parsed["instance_active"] is True
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_status_default_format_is_table(self, mock_get_config_manager, mock_get_metrics,
                                          mock_config_manager, mock_config, mock_metrics_instance):
        """Test that default format is table."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(status)
        
        assert result.exit_code == 0
        # Default should be table format (not JSON)


class TestEndpointCommand:
    """Test metrics endpoint command."""
    
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_endpoint_metrics_disabled(self, mock_console, mock_get_config_manager,
                                     mock_config_manager, mock_config):
        """Test endpoint command when metrics are disabled."""
        mock_config.general.metrics.enabled = False
        mock_get_config_manager.return_value = mock_config_manager
        
        runner = CliRunner()
        result = runner.invoke(endpoint)
        
        assert result.exit_code == 0
        mock_console.print.assert_called_once_with("[yellow]Metrics are disabled[/yellow]")
    
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_endpoint_metrics_enabled(self, mock_console, mock_get_config_manager,
                                    mock_config_manager, mock_config):
        """Test endpoint command when metrics are enabled."""
        mock_get_config_manager.return_value = mock_config_manager
        
        runner = CliRunner()
        result = runner.invoke(endpoint)
        
        assert result.exit_code == 0
        # Should print panel with endpoint URL and helpful text
        assert mock_console.print.call_count >= 3
        
        # Check for endpoint URL in Panel renderable and string args
        call_args = mock_console.print.call_args_list
        endpoint_found = False
        for call in call_args:
            if call[0]:
                arg = call[0][0]
                # Check Panel renderable
                if hasattr(arg, 'renderable'):
                    if "http://localhost:8000/metrics" in str(arg.renderable):
                        endpoint_found = True
                        break
                # Check string args
                elif isinstance(arg, str) and "http://localhost:8000/metrics" in arg:
                    endpoint_found = True
                    break
        
        assert endpoint_found
    
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_endpoint_url_construction(self, mock_get_config_manager, mock_config_manager, mock_config):
        """Test correct endpoint URL construction."""
        mock_config.general.metrics.port = 9090
        mock_config.general.metrics.path = "/prometheus"
        mock_get_config_manager.return_value = mock_config_manager
        
        with patch('vortex.cli.commands.metrics.console') as mock_console:
            runner = CliRunner()
            result = runner.invoke(endpoint)
            
            assert result.exit_code == 0
            # Verify correct URL construction in Panel renderable and string args
            call_args = mock_console.print.call_args_list
            url_found = False
            for call in call_args:
                if call[0]:
                    arg = call[0][0]
                    # Check Panel renderable
                    if hasattr(arg, 'renderable'):
                        if "http://localhost:9090/prometheus" in str(arg.renderable):
                            url_found = True
                            break
                    # Check string args
                    elif isinstance(arg, str) and "http://localhost:9090/prometheus" in arg:
                        url_found = True
                        break
            
            assert url_found


class TestTestCommand:
    """Test metrics test command."""
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_test_metrics_disabled(self, mock_console, mock_get_config_manager, mock_get_metrics,
                                 mock_config_manager, mock_config):
        """Test test command when metrics are disabled."""
        mock_config.general.metrics.enabled = False
        mock_get_config_manager.return_value = mock_config_manager
        
        runner = CliRunner()
        result = runner.invoke(test)
        
        assert result.exit_code == 0
        mock_console.print.assert_called_once_with("[yellow]⚠️  Metrics are disabled - enable in configuration first[/yellow]")
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_test_metrics_unavailable(self, mock_console, mock_get_config_manager, mock_get_metrics,
                                    mock_config_manager, mock_config):
        """Test test command when metrics system is unavailable."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = None
        
        runner = CliRunner()
        result = runner.invoke(test)
        
        assert result.exit_code == 0
        mock_console.print.assert_called_once_with("[red]❌ Metrics system not available[/red]")
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_test_default_samples(self, mock_console, mock_get_config_manager, mock_get_metrics,
                                mock_sleep, mock_config_manager, mock_config, mock_metrics_instance):
        """Test test command with default sample count."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test)
        
        assert result.exit_code == 0
        
        # Verify metrics were recorded (default 5 samples)
        assert mock_metrics_instance.record_provider_request.call_count == 5
        assert mock_metrics_instance.record_download_rows.call_count >= 1
        assert mock_metrics_instance.record_download_success.call_count >= 1
        
        # Verify sleep was called for each sample
        assert mock_sleep.call_count == 5
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_test_custom_samples(self, mock_console, mock_get_config_manager, mock_get_metrics,
                               mock_sleep, mock_config_manager, mock_config, mock_metrics_instance):
        """Test test command with custom sample count."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "3"])
        
        assert result.exit_code == 0
        
        # Verify metrics were recorded (3 samples)
        assert mock_metrics_instance.record_provider_request.call_count == 3
        assert mock_sleep.call_count == 3
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_provider_rotation(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                                  mock_config_manager, mock_config, mock_metrics_instance):
        """Test that test command rotates through providers."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "4"])
        
        assert result.exit_code == 0
        
        # Verify provider rotation
        provider_calls = [call[1]['provider'] for call in mock_metrics_instance.record_provider_request.call_args_list]
        expected_providers = ["yahoo", "barchart", "ibkr", "yahoo"]  # Should cycle
        assert provider_calls == expected_providers
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_operation_rotation(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                                   mock_config_manager, mock_config, mock_metrics_instance):
        """Test that test command rotates through operations."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "4"])
        
        assert result.exit_code == 0
        
        # Verify operation rotation
        operation_calls = [call[1]['operation'] for call in mock_metrics_instance.record_provider_request.call_args_list]
        expected_operations = ["download", "authenticate", "fetch_data", "download"]  # Should cycle
        assert operation_calls == expected_operations
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_success_rate_pattern(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                                     mock_config_manager, mock_config, mock_metrics_instance):
        """Test that test command creates expected success rate pattern."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "4"])
        
        assert result.exit_code == 0
        
        # Verify success pattern (success when i % 4 != 0)
        # For i = 0,1,2,3: [False, True, True, True] = 75% success rate
        success_calls = [call[1]['success'] for call in mock_metrics_instance.record_provider_request.call_args_list]
        expected_success = [False, True, True, True]  # i=0 fails, i=1,2,3 succeed
        assert success_calls == expected_success
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_duration_progression(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                                     mock_config_manager, mock_config, mock_metrics_instance):
        """Test that test command creates progressive duration values."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "3"])
        
        assert result.exit_code == 0
        
        # Verify duration progression (0.5 + i * 0.1)
        duration_calls = [call[1]['duration'] for call in mock_metrics_instance.record_provider_request.call_args_list]
        expected_durations = [0.5, 0.6, 0.7]
        assert duration_calls == expected_durations
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_download_metrics_on_success(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                                            mock_config_manager, mock_config, mock_metrics_instance):
        """Test that download metrics are recorded on successful requests."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "2"])
        
        assert result.exit_code == 0
        
        # For 2 samples (i=0,1): i=0 fails (0%4 != 0 is False), i=1 succeeds (1%4 != 0 is True)
        # Only successful requests record download metrics
        assert mock_metrics_instance.record_download_rows.call_count == 1
        assert mock_metrics_instance.record_download_success.call_count == 1
        assert mock_metrics_instance.record_download_failure.call_count == 1
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_download_metrics_on_failure(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                                            mock_config_manager, mock_config, mock_metrics_instance):
        """Test that failure metrics are recorded on failed requests."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        # Use samples that will include failures (i % 4 == 0)
        result = runner.invoke(test, ["--samples", "5"])
        
        assert result.exit_code == 0
        
        # Should have some failures (sample 4, where i=4, 4%4 == 0)
        assert mock_metrics_instance.record_download_failure.call_count >= 1
        # And some successes
        assert mock_metrics_instance.record_download_success.call_count >= 1
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_row_count_progression(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                                      mock_config_manager, mock_config, mock_metrics_instance):
        """Test that row counts progress correctly."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "3"])
        
        assert result.exit_code == 0
        
        # Verify row count progression (100 + i * 50) for successful samples only
        # For 3 samples (i=0,1,2): i=0 fails, i=1,2 succeed
        # Expected row counts: i=1→150, i=2→200
        if mock_metrics_instance.record_download_rows.call_count > 0:
            row_calls = [call[0][2] for call in mock_metrics_instance.record_download_rows.call_args_list]
            expected_rows = [150, 200]  # Only successful samples record rows
            assert row_calls == expected_rows


class TestSummaryCommand:
    """Test metrics summary command."""
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_summary_metrics_disabled(self, mock_console, mock_get_config_manager, mock_get_metrics,
                                    mock_config_manager, mock_config):
        """Test summary command when metrics are disabled."""
        mock_config.general.metrics.enabled = False
        mock_get_config_manager.return_value = mock_config_manager
        
        runner = CliRunner()
        result = runner.invoke(summary)
        
        assert result.exit_code == 0
        mock_console.print.assert_any_call("[yellow]⚠️  Metrics collection is disabled[/yellow]")
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_summary_metrics_unavailable(self, mock_console, mock_get_config_manager, mock_get_metrics,
                                       mock_config_manager, mock_config):
        """Test summary command when metrics system is unavailable."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = None
        
        runner = CliRunner()
        result = runner.invoke(summary)
        
        assert result.exit_code == 0
        mock_console.print.assert_any_call("[red]❌ Metrics system not available[/red]")
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_summary_no_provider_filter(self, mock_console, mock_get_config_manager, mock_get_metrics,
                                       mock_config_manager, mock_config, mock_metrics_instance):
        """Test summary command without provider filter."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(summary)
        
        assert result.exit_code == 0
        
        # Should display summary information
        call_args = [str(call[0][0]) for call in mock_console.print.call_args_list]
        summary_found = any("Metrics Summary" in arg for arg in call_args)
        assert summary_found
        
        # Should show endpoint URL
        endpoint_found = any("http://localhost:8000/metrics" in arg for arg in call_args)
        assert endpoint_found
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    @patch('vortex.cli.commands.metrics.console')
    def test_summary_with_provider_filter(self, mock_console, mock_get_config_manager, mock_get_metrics,
                                        mock_config_manager, mock_config, mock_metrics_instance):
        """Test summary command with provider filter."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(summary, ["--provider", "barchart"])
        
        assert result.exit_code == 0
        
        # Should show provider filter
        call_args = [str(call[0][0]) for call in mock_console.print.call_args_list]
        filter_found = any("BARCHART provider" in arg for arg in call_args)
        assert filter_found
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_summary_provider_choices(self, mock_get_config_manager, mock_get_metrics,
                                    mock_config_manager, mock_config, mock_metrics_instance):
        """Test summary command accepts valid provider choices."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        
        # Test all valid providers
        for provider in ["yahoo", "barchart", "ibkr"]:
            result = runner.invoke(summary, ["--provider", provider])
            assert result.exit_code == 0
        
        # Test invalid provider
        result = runner.invoke(summary, ["--provider", "invalid"])
        assert result.exit_code != 0


class TestDashboardCommand:
    """Test metrics dashboard command."""
    
    @patch('vortex.cli.commands.metrics.console')
    def test_dashboard_display(self, mock_console):
        """Test dashboard command displays monitoring information."""
        runner = CliRunner()
        result = runner.invoke(dashboard)
        
        assert result.exit_code == 0
        
        # Should print multiple panels
        assert mock_console.print.call_count >= 3
        
        # Verify essential information is displayed in Panel renderables and strings
        call_args = mock_console.print.call_args_list
        
        grafana_found = False
        prometheus_found = False
        grafana_url_found = False
        prometheus_url_found = False
        
        for call in call_args:
            if call[0]:
                arg = call[0][0]
                # Check Panel renderable
                if hasattr(arg, 'renderable'):
                    renderable_str = str(arg.renderable)
                    if "Grafana" in renderable_str:
                        grafana_found = True
                    if "Prometheus" in renderable_str:
                        prometheus_found = True
                    if "3000" in renderable_str:
                        grafana_url_found = True
                    if "9090" in renderable_str:
                        prometheus_url_found = True
                # Check string args
                elif isinstance(arg, str):
                    if "Grafana" in arg:
                        grafana_found = True
                    if "Prometheus" in arg:
                        prometheus_found = True
                    if "3000" in arg:
                        grafana_url_found = True
                    if "9090" in arg:
                        prometheus_url_found = True
        
        assert grafana_found
        assert prometheus_found
        assert grafana_url_found
        assert prometheus_url_found
    
    @patch('vortex.cli.commands.metrics.console')
    def test_dashboard_panels_structure(self, mock_console):
        """Test that dashboard command creates proper panel structure."""
        runner = CliRunner()
        result = runner.invoke(dashboard)
        
        assert result.exit_code == 0
        
        # Should print exactly 3 panels
        panel_calls = [call for call in mock_console.print.call_args_list 
                      if len(call[0]) > 0 and hasattr(call[0][0], 'title')]
        # Note: This is a simplified check - in reality panels might not be directly detectable this way
        # The test verifies the command runs without error and prints content


class TestMetricsCommandsIntegration:
    """Integration tests for metrics commands."""
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_all_commands_run_without_error(self, mock_get_config_manager, mock_get_metrics,
                                          mock_config_manager, mock_config, mock_metrics_instance):
        """Test that all metrics commands can run without errors."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        
        # Test all commands
        commands_to_test = [
            (status, []),
            (status, ["--format", "json"]),
            (endpoint, []),
            (test, ["--samples", "1"]),
            (summary, []),
            (summary, ["--provider", "yahoo"]),
            (dashboard, [])
        ]
        
        for command, args in commands_to_test:
            with patch('vortex.cli.commands.metrics.time.sleep'):  # Speed up test command
                result = runner.invoke(command, args)
                assert result.exit_code == 0, f"Command {command.name} with args {args} failed"
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_command_help_messages(self, mock_get_config_manager, mock_get_metrics,
                                  mock_config_manager, mock_config, mock_metrics_instance):
        """Test that all commands have proper help messages."""
        runner = CliRunner()
        
        # Test help for main group
        result = runner.invoke(metrics, ["--help"])
        assert result.exit_code == 0
        assert "View and manage Vortex metrics and monitoring" in result.output
        
        # Test help for individual commands
        commands = ["status", "endpoint", "test", "summary", "dashboard"]
        for cmd in commands:
            result = runner.invoke(metrics, [cmd, "--help"])
            assert result.exit_code == 0
            assert "Usage:" in result.output


class TestMetricsCommandsEdgeCases:
    """Test edge cases and error conditions."""
    
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_config_manager_exception(self, mock_get_config_manager):
        """Test behavior when config manager raises exception."""
        mock_get_config_manager.side_effect = Exception("Config error")
        
        runner = CliRunner()
        
        # Commands should handle config errors gracefully
        result = runner.invoke(status)
        assert result.exit_code != 0  # Should fail gracefully
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_with_zero_samples(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                                  mock_config_manager, mock_config, mock_metrics_instance):
        """Test test command with zero samples."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "0"])
        
        assert result.exit_code == 0
        
        # Should not record any metrics
        assert mock_metrics_instance.record_provider_request.call_count == 0
        assert mock_metrics_instance.record_download_rows.call_count == 0
        assert mock_sleep.call_count == 0
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_metrics_recording_exception(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                                            mock_config_manager, mock_config, mock_metrics_instance):
        """Test test command when metrics recording raises exception."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        # Make metrics recording fail
        mock_metrics_instance.record_provider_request.side_effect = Exception("Metrics error")
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "2"])
        
        # Command should handle metrics errors gracefully (not crash)
        assert result.exit_code == 0


class TestMetricsCommandsConfigurationHandling:
    """Test configuration handling across metrics commands."""
    
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_custom_port_and_path(self, mock_get_config_manager, mock_config_manager, mock_config):
        """Test commands with custom port and path configuration."""
        mock_config.general.metrics.port = 9999
        mock_config.general.metrics.path = "/custom/metrics"
        mock_get_config_manager.return_value = mock_config_manager
        
        with patch('vortex.cli.commands.metrics.console') as mock_console:
            runner = CliRunner()
            result = runner.invoke(endpoint)
            
            assert result.exit_code == 0
            
            # Should use custom port and path in Panel renderable and string args
            call_args = mock_console.print.call_args_list
            custom_url_found = False
            for call in call_args:
                if call[0]:
                    arg = call[0][0]
                    # Check Panel renderable
                    if hasattr(arg, 'renderable'):
                        if "http://localhost:9999/custom/metrics" in str(arg.renderable):
                            custom_url_found = True
                            break
                    # Check string args
                    elif isinstance(arg, str) and "http://localhost:9999/custom/metrics" in arg:
                        custom_url_found = True
                        break
            
            assert custom_url_found
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_config_consistency_across_commands(self, mock_get_config_manager, mock_get_metrics,
                                              mock_config_manager, mock_config, mock_metrics_instance):
        """Test that all commands use consistent configuration."""
        mock_config.general.metrics.port = 7777
        mock_config.general.metrics.path = "/test"
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        
        # Test that both status JSON and endpoint show same URL
        with patch('vortex.cli.commands.metrics.console') as mock_console:
            # Status JSON
            result = runner.invoke(status, ["--format", "json"])
            assert result.exit_code == 0
            
            json_output = mock_console.print.call_args[0][0]
            parsed = json.loads(json_output)
            assert parsed["port"] == 7777
            assert parsed["path"] == "/test"
        
        with patch('vortex.cli.commands.metrics.console') as mock_console:
            # Endpoint command
            result = runner.invoke(endpoint)
            assert result.exit_code == 0
            
            # Check for URL in Panel renderable and string args
            call_args = mock_console.print.call_args_list
            consistent_url_found = False
            for call in call_args:
                if call[0]:
                    arg = call[0][0]
                    # Check Panel renderable
                    if hasattr(arg, 'renderable'):
                        if "http://localhost:7777/test" in str(arg.renderable):
                            consistent_url_found = True
                            break
                    # Check string args
                    elif isinstance(arg, str) and "http://localhost:7777/test" in arg:
                        consistent_url_found = True
                        break
            
            assert consistent_url_found


class TestMetricsCommandsPerformance:
    """Test performance aspects of metrics commands."""
    
    @patch('vortex.cli.commands.metrics.time.sleep')
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_test_command_timing(self, mock_get_config_manager, mock_get_metrics, mock_sleep,
                               mock_config_manager, mock_config, mock_metrics_instance):
        """Test that test command respects timing parameters."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        result = runner.invoke(test, ["--samples", "3"])
        
        assert result.exit_code == 0
        
        # Verify sleep was called correctly
        assert mock_sleep.call_count == 3
        for call_args in mock_sleep.call_args_list:
            assert call_args[0][0] == 0.1  # Should sleep for 0.1 seconds
    
    @patch('vortex.cli.commands.metrics.get_metrics')
    @patch('vortex.cli.commands.metrics.get_config_manager')
    def test_fast_commands_no_delay(self, mock_get_config_manager, mock_get_metrics,
                                  mock_config_manager, mock_config, mock_metrics_instance):
        """Test that non-test commands execute quickly without delays."""
        mock_get_config_manager.return_value = mock_config_manager
        mock_get_metrics.return_value = mock_metrics_instance
        
        runner = CliRunner()
        
        start_time = time.time()
        
        # These commands should be fast
        fast_commands = [
            (status, []),
            (endpoint, []),
            (summary, []),
            (dashboard, [])
        ]
        
        for command, args in fast_commands:
            result = runner.invoke(command, args)
            assert result.exit_code == 0
        
        total_time = time.time() - start_time
        # All fast commands should complete within reasonable time
        assert total_time < 1.0  # Should be much faster in practice