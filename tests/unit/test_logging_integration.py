"""
Unit tests for logging_integration module.

Tests the logging integration functionality including health checks,
configuration management, and logger setup.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from vortex.logging_integration import (
    configure_logging_from_config, reconfigure_if_changed, 
    get_logger, _logging_configured, _current_config,
    HealthChecker
)
from vortex.core.config import VortexConfig, GeneralConfig, LoggingConfig


class TestLoggingIntegration:
    """Test logging integration functionality."""
    
    def setup_method(self):
        """Reset global state before each test."""
        import vortex.logging_integration
        vortex.logging_integration._logging_configured = False
        vortex.logging_integration._current_config = None

    def test_reconfigure_if_changed_not_configured(self):
        """Test reconfigure_if_changed when logging not yet configured."""
        config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="DEBUG",
                    format="json",
                    output=["console"]
                )
            )
        )
        
        with patch('vortex.logging_integration.configure_logging_from_config') as mock_configure:
            reconfigure_if_changed(config)
            mock_configure.assert_called_once_with(config)

    def test_reconfigure_if_changed_no_current_config(self):
        """Test reconfigure_if_changed with no current config stored."""
        import vortex.logging_integration
        vortex.logging_integration._logging_configured = True
        vortex.logging_integration._current_config = None
        
        config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="DEBUG",
                    format="json",
                    output=["console"]
                )
            )
        )
        
        with patch('vortex.logging_integration.configure_logging_from_config') as mock_configure:
            reconfigure_if_changed(config)
            mock_configure.assert_called_once_with(config)

    def test_reconfigure_if_changed_level_changed(self):
        """Test reconfigure_if_changed when log level changed."""
        import vortex.logging_integration
        vortex.logging_integration._logging_configured = True
        
        old_config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="INFO",
                    format="console",
                    output=["console"]
                )
            )
        )
        vortex.logging_integration._current_config = old_config
        
        new_config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="DEBUG",  # Changed from INFO
                    format="console",
                    output=["console"]
                )
            )
        )
        
        with patch('vortex.logging_integration.configure_logging_from_config') as mock_configure:
            reconfigure_if_changed(new_config)
            mock_configure.assert_called_once_with(new_config)

    def test_reconfigure_if_changed_format_changed(self):
        """Test reconfigure_if_changed when log format changed."""
        import vortex.logging_integration
        vortex.logging_integration._logging_configured = True
        
        old_config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="INFO",
                    format="console",
                    output=["console"]
                )
            )
        )
        vortex.logging_integration._current_config = old_config
        
        new_config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="INFO",
                    format="json",  # Changed from console
                    output=["console"]
                )
            )
        )
        
        with patch('vortex.logging_integration.configure_logging_from_config') as mock_configure:
            reconfigure_if_changed(new_config)
            mock_configure.assert_called_once_with(new_config)

    def test_reconfigure_if_changed_output_changed(self):
        """Test reconfigure_if_changed when output changed."""
        import vortex.logging_integration
        vortex.logging_integration._logging_configured = True
        
        old_config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="INFO",
                    format="console",
                    output=["console"]
                )
            )
        )
        vortex.logging_integration._current_config = old_config
        
        new_config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="INFO",
                    format="console",
                    output=["file"]  # Changed from console
                )
            )
        )
        
        with patch('vortex.logging_integration.configure_logging_from_config') as mock_configure:
            reconfigure_if_changed(new_config)
            mock_configure.assert_called_once_with(new_config)

    def test_reconfigure_if_changed_file_path_changed(self):
        """Test reconfigure_if_changed when file_path changed."""
        import vortex.logging_integration
        vortex.logging_integration._logging_configured = True
        
        old_config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="INFO",
                    format="console",
                    output=["file"],
                    file_path="/old/path.log"
                )
            )
        )
        vortex.logging_integration._current_config = old_config
        
        new_config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="INFO",
                    format="console",
                    output=["file"],
                    file_path="/new/path.log"  # Changed path
                )
            )
        )
        
        with patch('vortex.logging_integration.configure_logging_from_config') as mock_configure:
            reconfigure_if_changed(new_config)
            mock_configure.assert_called_once_with(new_config)

    def test_reconfigure_if_changed_no_changes(self):
        """Test reconfigure_if_changed when no config changes."""
        import vortex.logging_integration
        vortex.logging_integration._logging_configured = True
        
        config = VortexConfig(
            general=GeneralConfig(
                logging=LoggingConfig(
                    level="INFO",
                    format="console",
                    output=["console"]
                )
            )
        )
        vortex.logging_integration._current_config = config
        
        # Same config
        with patch('vortex.logging_integration.configure_logging_from_config') as mock_configure:
            reconfigure_if_changed(config)
            mock_configure.assert_not_called()


class TestHealthChecker:
    """Test logging health monitor functionality."""
    
    def test_health_monitor_initialization(self):
        """Test health monitor initialization."""
        monitor = HealthChecker()
        
        assert monitor.checks == {}
        assert hasattr(monitor, 'logger')

    def test_register_check(self):
        """Test registering a health check."""
        monitor = HealthChecker()
        
        def dummy_check():
            return True
        
        with patch.object(monitor.logger, 'debug') as mock_debug:
            monitor.register_check("test_check", dummy_check)
            
            assert "test_check" in monitor.checks
            assert monitor.checks["test_check"] == dummy_check
            mock_debug.assert_called_once_with("Registered health check: test_check")

    def test_run_checks_empty(self):
        """Test running checks when no checks registered."""
        monitor = HealthChecker()
        
        with patch('vortex.logging_integration.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.isoformat.return_value = "2024-01-01T12:00:00Z"
            mock_datetime.now.return_value = mock_now
            
            results = monitor.run_checks()
            
            expected = {
                "status": "healthy",
                "timestamp": "2024-01-01T12:00:00Z",
                "checks": {}
            }
            assert results == expected

    def test_run_checks_boolean_result(self):
        """Test running checks with boolean result."""
        monitor = HealthChecker()
        
        def healthy_check():
            return True
        
        def unhealthy_check():
            return False
        
        monitor.register_check("healthy", healthy_check)
        monitor.register_check("unhealthy", unhealthy_check)
        
        with patch('vortex.logging_integration.datetime') as mock_datetime:
            mock_start = Mock()
            mock_end = Mock()
            mock_now = Mock()
            mock_now.isoformat.return_value = "2024-01-01T12:00:00Z"
            
            # Mock the datetime.now() calls in sequence
            mock_datetime.now.side_effect = [
                mock_now,  # First call for timestamp
                mock_start, mock_end,  # healthy check timing
                mock_start, mock_end   # unhealthy check timing
            ]
            
            # Mock time delta calculation
            mock_end.__sub__ = Mock(return_value=Mock(total_seconds=Mock(return_value=0.05)))
            mock_start.__sub__ = Mock(return_value=Mock(total_seconds=Mock(return_value=0.05)))
            
            results = monitor.run_checks()
            
            assert results["status"] == "unhealthy"  # Because one check failed
            assert results["timestamp"] == "2024-01-01T12:00:00Z"
            assert "healthy" in results["checks"]
            assert "unhealthy" in results["checks"]
            assert results["checks"]["healthy"]["healthy"] is True
            assert results["checks"]["unhealthy"]["healthy"] is False

    def test_run_checks_dict_result(self):
        """Test running checks with dict result."""
        monitor = HealthChecker()
        
        def dict_check():
            return {"healthy": True, "details": "All good", "value": 42}
        
        monitor.register_check("dict_check", dict_check)
        
        with patch('vortex.logging_integration.datetime') as mock_datetime:
            mock_start = Mock()
            mock_end = Mock()
            mock_now = Mock()
            mock_now.isoformat.return_value = "2024-01-01T12:00:00Z"
            
            mock_datetime.now.side_effect = [
                mock_now,  # timestamp
                mock_start, mock_end   # check timing
            ]
            
            # Mock duration calculation
            mock_end.__sub__ = Mock(return_value=Mock(total_seconds=Mock(return_value=0.1)))
            
            results = monitor.run_checks()
            
            check_result = results["checks"]["dict_check"]
            assert check_result["healthy"] is True
            assert check_result["details"] == "All good"
            assert check_result["value"] == 42
            assert check_result["duration_ms"] == 100.0

    def test_run_checks_string_result(self):
        """Test running checks with string result."""
        monitor = HealthChecker()
        
        def string_check():
            return "Everything is fine"
        
        monitor.register_check("string_check", string_check)
        
        with patch('vortex.logging_integration.datetime') as mock_datetime:
            mock_start = Mock()
            mock_end = Mock()
            mock_now = Mock()
            mock_now.isoformat.return_value = "2024-01-01T12:00:00Z"
            
            mock_datetime.now.side_effect = [
                mock_now,
                mock_start, mock_end
            ]
            
            mock_end.__sub__ = Mock(return_value=Mock(total_seconds=Mock(return_value=0.02)))
            
            results = monitor.run_checks()
            
            check_result = results["checks"]["string_check"]
            assert check_result["healthy"] is True  # Non-empty string is truthy
            assert check_result["details"] == "Everything is fine"
            assert check_result["duration_ms"] == 20.0

    def test_run_checks_exception_handling(self):
        """Test running checks with exception handling."""
        monitor = HealthChecker()
        
        def failing_check():
            raise RuntimeError("Check failed")
        
        def working_check():
            return True
        
        monitor.register_check("failing", failing_check)
        monitor.register_check("working", working_check)
        
        with patch('vortex.logging_integration.datetime') as mock_datetime:
            with patch.object(monitor.logger, 'error') as mock_error:
                mock_start = Mock()
                mock_end = Mock()
                mock_now = Mock()
                mock_now.isoformat.return_value = "2024-01-01T12:00:00Z"
                
                mock_datetime.now.side_effect = [
                    mock_now,
                    mock_start, mock_end,  # failing check
                    mock_start, mock_end   # working check
                ]
                
                mock_end.__sub__ = Mock(return_value=Mock(total_seconds=Mock(return_value=0.01)))
                
                results = monitor.run_checks()
                
                # Should log the error
                mock_error.assert_called_once()
                
                # Overall status should be unhealthy due to failure
                assert results["status"] == "unhealthy"
                
                # Failed check should be marked as unhealthy
                assert results["checks"]["failing"]["healthy"] is False
                assert "error" in results["checks"]["failing"]
                
                # Working check should still work
                assert results["checks"]["working"]["healthy"] is True

    def test_run_checks_overall_status_logic(self):
        """Test overall status determination logic."""
        monitor = HealthChecker()
        
        def healthy1():
            return True
        
        def healthy2():
            return {"healthy": True}
        
        monitor.register_check("h1", healthy1)
        monitor.register_check("h2", healthy2)
        
        with patch('vortex.logging_integration.datetime') as mock_datetime:
            mock_start = Mock()
            mock_end = Mock()
            mock_now = Mock()
            mock_now.isoformat.return_value = "2024-01-01T12:00:00Z"
            
            mock_datetime.now.side_effect = [
                mock_now,
                mock_start, mock_end,
                mock_start, mock_end
            ]
            
            mock_end.__sub__ = Mock(return_value=Mock(total_seconds=Mock(return_value=0.01)))
            
            results = monitor.run_checks()
            
            # All checks healthy, so overall should be healthy
            assert results["status"] == "healthy"