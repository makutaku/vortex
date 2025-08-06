"""Tests for resilience CLI commands."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from click.testing import CliRunner

from vortex.cli.commands.resilience import (
    resilience,
    status,
    reset, 
    recovery,
    requests,
    health,
    resilience_status,
    _show_summary,
    _show_table,
    _get_health_recommendations,
    _check_resilience_available
)
import vortex.cli.commands.resilience as resilience_module


class TestResilienceCommands:
    """Test cases for resilience CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
    @patch('vortex.cli.commands.resilience.RESILIENCE_AVAILABLE', True)
    @patch('vortex.cli.commands.resilience.get_circuit_breaker_stats')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_status_command_table_format(self, mock_ux, mock_get_stats):
        """Test status command with table format."""
        # Mock circuit breaker stats
        mock_stats = {
            'provider1': {
                'state': 'closed',
                'failure_rate': 0.1,
                'total_calls': 100,
                'circuit_opened_count': 2,
                'last_failure_time': '2023-01-01T12:00:00Z'
            }
        }
        mock_get_stats.return_value = mock_stats
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(status, ['--format', 'table'])
        
        assert result.exit_code == 0
        mock_get_stats.assert_called_once()
        mock_ux_instance.print_table.assert_called_once()

    @patch('vortex.cli.commands.resilience.RESILIENCE_AVAILABLE', True)
    @patch('vortex.cli.commands.resilience.get_circuit_breaker_stats')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_status_command_json_format(self, mock_ux, mock_get_stats):
        """Test status command with JSON format."""
        mock_stats = {
            'provider1': {
                'state': 'closed',
                'failure_rate': 0.0,
                'total_calls': 50,
                'circuit_opened_count': 0,
                'last_failure_time': None
            }
        }
        mock_get_stats.return_value = mock_stats
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(status, ['--format', 'json'])
        
        assert result.exit_code == 0
        mock_ux_instance.print_json.assert_called_once_with(mock_stats)

    @patch('vortex.cli.commands.resilience.RESILIENCE_AVAILABLE', True)
    @patch('vortex.cli.commands.resilience.get_circuit_breaker_stats')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_status_command_summary_format(self, mock_ux, mock_get_stats):
        """Test status command with summary format."""
        mock_stats = {
            'provider1': {
                'state': 'closed',
                'failure_rate': 0.0,
                'total_calls': 100,
                'circuit_opened_count': 0,
                'last_failure_time': None
            }
        }
        mock_get_stats.return_value = mock_stats
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(status, ['--format', 'summary'])
        
        assert result.exit_code == 0
        mock_ux_instance.print_panel.assert_called_once()

    @patch('vortex.cli.commands.resilience.RESILIENCE_AVAILABLE', True)
    @patch('vortex.cli.commands.resilience.get_circuit_breaker_stats')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_status_command_with_provider_filter(self, mock_ux, mock_get_stats):
        """Test status command with provider filter."""
        mock_stats = {
            'provider1': {
                'state': 'closed',
                'failure_rate': 0.1,
                'total_calls': 100,
                'circuit_opened_count': 0,
                'last_failure_time': None
            },
            'provider2': {
                'state': 'open',
                'failure_rate': 0.8,
                'total_calls': 50,
                'circuit_opened_count': 3,
                'last_failure_time': '2023-01-01T12:00:00Z'
            }
        }
        mock_get_stats.return_value = mock_stats
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(status, ['--provider', 'provider1'])
        
        assert result.exit_code == 0
        mock_ux_instance.print_table.assert_called_once()

    @patch('vortex.cli.commands.resilience.RESILIENCE_AVAILABLE', True)
    @patch('vortex.cli.commands.resilience.get_circuit_breaker_stats')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_status_command_no_stats(self, mock_ux, mock_get_stats):
        """Test status command when no stats available."""
        mock_get_stats.return_value = {}
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(status)
        
        assert result.exit_code == 0
        mock_ux_instance.print.assert_called_with("No circuit breakers are currently active")

    @patch('vortex.cli.commands.resilience.get_ux')
    def test_status_command_resilience_unavailable(self, mock_ux):
        """Test status command when resilience is unavailable."""
        with patch('vortex.cli.commands.resilience.RESILIENCE_AVAILABLE', False):
            with patch('vortex.cli.commands.resilience._check_resilience_available', return_value=False):
                mock_ux_instance = Mock()
                mock_ux.return_value = mock_ux_instance
                
                result = self.runner.invoke(status)
                
                assert result.exit_code == 0

    @patch('vortex.cli.commands.resilience.reset_all_circuit_breakers')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_reset_command_with_confirmation(self, mock_ux, mock_reset):
        """Test reset command with confirmation."""
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(reset, ['--confirm'])
        
        assert result.exit_code == 0
        mock_reset.assert_called_once()
        mock_ux_instance.print.assert_called_with("✅ All circuit breakers have been reset to closed state")

    @patch('vortex.cli.commands.resilience.get_ux')
    def test_reset_command_user_cancels(self, mock_ux):
        """Test reset command when user cancels."""
        mock_ux_instance = Mock()
        mock_ux_instance.confirm.return_value = False
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(reset)
        
        assert result.exit_code == 0
        mock_ux_instance.print.assert_called_with("Operation cancelled")

    @patch('vortex.cli.commands.resilience.get_ux')
    def test_recovery_command(self, mock_ux):
        """Test recovery command."""
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(recovery)
        
        assert result.exit_code == 0
        mock_ux_instance.print.assert_any_call("📊 Error Recovery Statistics")

    @patch('vortex.cli.commands.resilience.get_request_tracker')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_requests_command_with_active_requests(self, mock_ux, mock_get_tracker):
        """Test requests command with active requests."""
        mock_tracker = Mock()
        now = datetime.now()
        mock_requests = {
            'corr123': {
                'operation': 'download',
                'start_time': now,
                'metadata': {'provider': 'yahoo'}
            }
        }
        mock_tracker.get_active_requests.return_value = mock_requests
        mock_get_tracker.return_value = mock_tracker
        
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(requests)
        
        assert result.exit_code == 0
        mock_ux_instance.print_table.assert_called_once()

    @patch('vortex.cli.commands.resilience.get_request_tracker')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_requests_command_no_active_requests(self, mock_ux, mock_get_tracker):
        """Test requests command with no active requests."""
        mock_tracker = Mock()
        mock_tracker.get_active_requests.return_value = {}
        mock_get_tracker.return_value = mock_tracker
        
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(requests)
        
        assert result.exit_code == 0
        mock_ux_instance.print.assert_called_with("No active requests are currently being tracked")

    @patch('vortex.cli.commands.resilience.get_request_tracker')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_requests_command_json_format(self, mock_ux, mock_get_tracker):
        """Test requests command with JSON format."""
        mock_tracker = Mock()
        mock_requests = {'corr123': {'operation': 'download'}}
        mock_tracker.get_active_requests.return_value = mock_requests
        mock_get_tracker.return_value = mock_tracker
        
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(requests, ['--format', 'json'])
        
        assert result.exit_code == 0
        mock_ux_instance.print_json.assert_called_once_with(mock_requests)

    @patch('vortex.cli.commands.resilience.get_circuit_breaker_stats')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_health_command_healthy_system(self, mock_ux, mock_get_stats):
        """Test health command with healthy system."""
        mock_stats = {
            'provider1': {
                'state': 'closed',
                'failure_rate': 0.0,
                'total_calls': 100,
                'circuit_opened_count': 0,
                'last_failure_time': None
            },
            'provider2': {
                'state': 'closed',
                'failure_rate': 0.05,
                'total_calls': 200,
                'circuit_opened_count': 0,
                'last_failure_time': None
            }
        }
        mock_get_stats.return_value = mock_stats
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(health)
        
        assert result.exit_code == 0
        mock_ux_instance.print_panel.assert_called_once()
        call_args = mock_ux_instance.print_panel.call_args
        assert "HEALTHY" in call_args[0][0]

    @patch('vortex.cli.commands.resilience.get_circuit_breaker_stats')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_health_command_degraded_system(self, mock_ux, mock_get_stats):
        """Test health command with degraded system."""
        # 4 providers with 3 healthy = 75% (between 70% and 90%)
        mock_stats = {
            'provider1': {
                'state': 'closed',
                'failure_rate': 0.0,
                'total_calls': 100,
                'circuit_opened_count': 0,
                'last_failure_time': None
            },
            'provider2': {
                'state': 'closed',
                'failure_rate': 0.05,
                'total_calls': 200,
                'circuit_opened_count': 0,
                'last_failure_time': None
            },
            'provider3': {
                'state': 'closed',
                'failure_rate': 0.02,
                'total_calls': 150,
                'circuit_opened_count': 0,
                'last_failure_time': None
            },
            'provider4': {
                'state': 'open',
                'failure_rate': 0.8,
                'total_calls': 50,
                'circuit_opened_count': 3,
                'last_failure_time': '2023-01-01T12:00:00Z'
            }
        }
        mock_get_stats.return_value = mock_stats
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(health)
        
        assert result.exit_code == 0
        call_args = mock_ux_instance.print_panel.call_args
        assert "DEGRADED" in call_args[0][0]

    @patch('vortex.cli.commands.resilience.get_circuit_breaker_stats')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_health_command_unhealthy_system(self, mock_ux, mock_get_stats):
        """Test health command with unhealthy system."""
        # 2 providers with 1 healthy = 50% (< 70%)
        mock_stats = {
            'provider1': {
                'state': 'closed',
                'failure_rate': 0.0,
                'total_calls': 100,
                'circuit_opened_count': 0,
                'last_failure_time': None
            },
            'provider2': {
                'state': 'open',
                'failure_rate': 0.9,
                'total_calls': 50,
                'circuit_opened_count': 5,
                'last_failure_time': '2023-01-01T12:00:00Z'
            }
        }
        mock_get_stats.return_value = mock_stats
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(health)
        
        assert result.exit_code == 0
        call_args = mock_ux_instance.print_panel.call_args
        assert "UNHEALTHY" in call_args[0][0]

    @patch('vortex.cli.commands.resilience.get_circuit_breaker_stats')
    @patch('vortex.cli.commands.resilience.get_ux')
    def test_health_command_no_breakers(self, mock_ux, mock_get_stats):
        """Test health command with no circuit breakers."""
        mock_get_stats.return_value = {}
        mock_ux_instance = Mock()
        mock_ux.return_value = mock_ux_instance
        
        result = self.runner.invoke(health)
        
        assert result.exit_code == 0
        call_args = mock_ux_instance.print_panel.call_args
        assert "UNKNOWN" in call_args[0][0]

    def test_show_summary(self):
        """Test _show_summary function."""
        mock_ux = Mock()
        stats = {
            'provider1': {'state': 'closed'},
            'provider2': {'state': 'open'},
            'provider3': {'state': 'half_open'}
        }
        
        _show_summary(mock_ux, stats)
        
        mock_ux.print_panel.assert_called_once()
        call_args = mock_ux.print_panel.call_args[0][0]
        assert "Total Breakers: 3" in call_args
        assert "Healthy (Closed): 1" in call_args
        assert "Failing (Open): 1" in call_args

    def test_show_table(self):
        """Test _show_table function."""
        mock_ux = Mock()
        stats = {
            'provider1': {
                'state': 'closed',
                'failure_rate': 0.1,
                'total_calls': 100,
                'circuit_opened_count': 2,
                'last_failure_time': '2023-01-01T12:00:00Z'
            }
        }
        
        _show_table(mock_ux, stats)
        
        mock_ux.print_table.assert_called_once()
        call_args = mock_ux.print_table.call_args
        rows = call_args[0][0]
        assert len(rows) == 1
        assert rows[0][0] == 'provider1'

    def test_show_table_with_none_failure_time(self):
        """Test _show_table with None failure time."""
        mock_ux = Mock()
        stats = {
            'provider1': {
                'state': 'closed',
                'failure_rate': None,
                'total_calls': 100,
                'circuit_opened_count': 0,
                'last_failure_time': None
            }
        }
        
        _show_table(mock_ux, stats)
        
        mock_ux.print_table.assert_called_once()
        call_args = mock_ux.print_table.call_args
        rows = call_args[0][0]
        assert rows[0][2] == "N/A"  # failure_rate
        assert rows[0][5] == "Never"  # last_failure_time

    def test_get_health_recommendations_healthy(self):
        """Test health recommendations for healthy system."""
        recommendations = _get_health_recommendations(95.0, 0, 0)
        
        assert "System is operating normally" in recommendations
        assert "Continue monitoring" in recommendations

    def test_get_health_recommendations_degraded(self):
        """Test health recommendations for degraded system."""
        recommendations = _get_health_recommendations(75.0, 1, 1)
        
        assert "Some components experiencing issues" in recommendations
        assert "Monitor failing components" in recommendations
        assert "Allow time for recovery testing" in recommendations

    def test_get_health_recommendations_unhealthy(self):
        """Test health recommendations for unhealthy system."""
        recommendations = _get_health_recommendations(50.0, 3, 0)
        
        assert "System health is compromised" in recommendations
        assert "Check provider connectivity" in recommendations
        assert "Review logs for 3 failing component(s)" in recommendations

    def test_check_resilience_available_true(self):
        """Test _check_resilience_available when available."""
        with patch('vortex.cli.commands.resilience.RESILIENCE_AVAILABLE', True):
            result = _check_resilience_available()
            assert result is True

    def test_check_resilience_available_false(self):
        """Test _check_resilience_available when not available."""
        # Test the behavior more directly by patching the global variables
        with patch('vortex.cli.commands.resilience.RESILIENCE_AVAILABLE', False):
            with patch('vortex.cli.commands.resilience._import_error', Exception("Test error"), create=True):
                with patch('vortex.cli.commands.resilience.get_ux') as mock_ux:
                    mock_ux_instance = Mock()
                    mock_ux.return_value = mock_ux_instance
                    
                    result = _check_resilience_available()
                    
                    assert result is False
                    # Check that print was called - the exact message may vary based on implementation
                    mock_ux_instance.print.assert_called()

    def test_resilience_status_command(self):
        """Test resilience_status command."""
        mock_ctx = Mock()
        with patch('vortex.cli.commands.resilience.RESILIENCE_AVAILABLE', True):
            with patch('vortex.cli.commands.resilience.get_circuit_breaker_stats', return_value={}):
                with patch('vortex.cli.commands.resilience.get_ux') as mock_ux:
                    mock_ux_instance = Mock()
                    mock_ux.return_value = mock_ux_instance
                    
                    result = self.runner.invoke(resilience_status)
                    assert result.exit_code == 0

    def test_resilience_group_command(self):
        """Test resilience group command."""
        result = self.runner.invoke(resilience, ['--help'])
        assert result.exit_code == 0
        assert "Monitor and manage system resilience features" in result.output