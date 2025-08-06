"""
Tests for CLI analytics functionality.

Tests simple analytics utility functions for quick coverage gains.
"""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime, timezone


class TestAnalyticsUtilities:
    """Test simple analytics utility functions."""

    def test_track_command_global_function(self):
        """Test global track_command function."""
        from vortex.cli.analytics import track_command

        with patch('vortex.cli.analytics.analytics') as mock_analytics:
            track_command("test_command", provider="yahoo", success=True)
            
            mock_analytics.track_command.assert_called_once_with(
                "test_command", provider="yahoo", success=True
            )

    def test_track_error_global_function(self):
        """Test global track_error function."""
        from vortex.cli.analytics import track_error

        with patch('vortex.cli.analytics.analytics') as mock_analytics:
            track_error("test_command", "ValueError", "Test error message")
            
            mock_analytics.track_error.assert_called_once_with(
                "test_command", "ValueError", "Test error message"
            )

    @patch.dict(os.environ, {"VORTEX_ANALYTICS": "false"})
    def test_check_enabled_env_var_false(self):
        """Test _check_enabled with environment variable set to false."""
        from vortex.cli.analytics import CliAnalytics

        analytics = CliAnalytics()
        assert analytics.enabled is False

    @patch.dict(os.environ, {"VORTEX_ANALYTICS": "true"})
    def test_check_enabled_env_var_true(self):
        """Test _check_enabled with environment variable set to true."""
        from vortex.cli.analytics import CliAnalytics

        analytics = CliAnalytics()
        assert analytics.enabled is True

    @patch.dict(os.environ, {"VORTEX_ANALYTICS": "0"})
    def test_check_enabled_env_var_zero(self):
        """Test _check_enabled with environment variable set to 0."""
        from vortex.cli.analytics import CliAnalytics

        analytics = CliAnalytics()
        assert analytics.enabled is False

    @patch.dict(os.environ, {"VORTEX_ANALYTICS": "1"}) 
    def test_check_enabled_env_var_one(self):
        """Test _check_enabled with environment variable set to 1."""
        from vortex.cli.analytics import CliAnalytics

        analytics = CliAnalytics()
        assert analytics.enabled is True

    @patch.dict(os.environ, {"VORTEX_ANALYTICS": "disabled"})
    def test_check_enabled_env_var_disabled(self):
        """Test _check_enabled with environment variable set to disabled."""
        from vortex.cli.analytics import CliAnalytics

        analytics = CliAnalytics()
        assert analytics.enabled is False

    @patch.dict(os.environ, {"VORTEX_ANALYTICS": "enabled"})
    def test_check_enabled_env_var_enabled(self):
        """Test _check_enabled with environment variable set to enabled."""
        from vortex.cli.analytics import CliAnalytics

        analytics = CliAnalytics()
        assert analytics.enabled is True

    def test_check_enabled_no_env_var_default(self):
        """Test _check_enabled with no environment variable defaults to true."""
        from vortex.cli.analytics import CliAnalytics

        # Ensure no env var is set
        with patch.dict(os.environ, {}, clear=True):
            with patch('pathlib.Path.exists', return_value=False):
                analytics = CliAnalytics()
                assert analytics.enabled is True  # Default to enabled

    def test_analytics_decorator_success(self):
        """Test analytics_decorator for successful function execution."""
        from vortex.cli.analytics import analytics_decorator

        with patch('vortex.cli.analytics.track_command') as mock_track_command:
            @analytics_decorator("test_command")
            def test_func():
                return "success"

            result = test_func()
            
            assert result == "success"
            mock_track_command.assert_called_once()
            call_args = mock_track_command.call_args
            assert call_args[0][0] == "test_command"  # command name
            assert call_args[1]["success"] is True
            assert "duration_ms" in call_args[1]

    def test_analytics_decorator_exception(self):
        """Test analytics_decorator for function that raises exception."""
        from vortex.cli.analytics import analytics_decorator

        with patch('vortex.cli.analytics.track_command') as mock_track_command:
            with patch('vortex.cli.analytics.track_error') as mock_track_error:
                @analytics_decorator("test_command")
                def test_func():
                    raise ValueError("Test error")

                with pytest.raises(ValueError):
                    test_func()

                # Should track error
                mock_track_error.assert_called_once_with(
                    "test_command", "ValueError", "Test error"
                )
                
                # Should track command with success=False
                mock_track_command.assert_called_once()
                call_args = mock_track_command.call_args
                assert call_args[0][0] == "test_command"
                assert call_args[1]["success"] is False

    def test_cli_analytics_init_basic(self):
        """Test CliAnalytics initialization."""
        from vortex.cli.analytics import CliAnalytics

        analytics = CliAnalytics()
        
        # Just test basic properties exist and have correct types
        assert isinstance(analytics.session_id, str)
        assert len(analytics.session_id) > 0
        assert isinstance(analytics.config_dir, Path)
        assert analytics.config_dir.name == "vortex"
        assert isinstance(analytics.analytics_file, Path)
        assert analytics.analytics_file.name == "analytics.json"

    def test_get_status_basic(self):
        """Test get_status returns expected structure."""
        from vortex.cli.analytics import CliAnalytics

        with patch('pathlib.Path.exists', return_value=False):
            analytics = CliAnalytics()
            status = analytics.get_status()

            assert "enabled" in status
            assert "user_id" in status
            assert "session_id" in status
            assert "config_file" in status
            assert "events_stored" in status
            
            assert isinstance(status["enabled"], bool)
            assert isinstance(status["user_id"], str)
            assert isinstance(status["session_id"], str)
            assert isinstance(status["config_file"], str)
            assert isinstance(status["events_stored"], int)

    def test_count_stored_events_no_file(self):
        """Test _count_stored_events when events file doesn't exist."""
        from vortex.cli.analytics import CliAnalytics

        with patch('pathlib.Path.exists', return_value=False):
            analytics = CliAnalytics()
            count = analytics._count_stored_events()
            assert count == 0

    def test_count_stored_events_with_file(self):
        """Test _count_stored_events when events file exists."""
        from vortex.cli.analytics import CliAnalytics

        mock_events_content = '{"event": "test1"}\n{"event": "test2"}\n{"event": "test3"}\n'
        
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=mock_events_content)):
                analytics = CliAnalytics()
                count = analytics._count_stored_events()
                assert count == 3

    def test_enable_analytics(self):
        """Test enable method."""
        from vortex.cli.analytics import CliAnalytics

        with patch('pathlib.Path.exists', return_value=False):
            analytics = CliAnalytics()
            
            with patch.object(analytics, '_save_config') as mock_save:
                analytics.enable()
                
                assert analytics.enabled is True
                mock_save.assert_called_once()
                call_args = mock_save.call_args[0][0]
                assert call_args["enabled"] is True
                assert "user_id" in call_args

    def test_disable_analytics(self):
        """Test disable method."""
        from vortex.cli.analytics import CliAnalytics

        with patch('pathlib.Path.exists', return_value=False):
            analytics = CliAnalytics()
            
            with patch.object(analytics, '_save_config') as mock_save:
                with patch('pathlib.Path.unlink') as mock_unlink:
                    analytics.disable()
                    
                    assert analytics.enabled is False
                    mock_save.assert_called_once()
                    call_args = mock_save.call_args[0][0]
                    assert call_args["enabled"] is False
                    assert "user_id" in call_args

    def test_track_command_disabled(self):
        """Test track_command when analytics disabled."""
        from vortex.cli.analytics import CliAnalytics

        with patch.dict(os.environ, {"VORTEX_ANALYTICS": "false"}):
            analytics = CliAnalytics()
            
            with patch.object(analytics, '_send_event') as mock_send:
                analytics.track_command("test")
                
                # Should not send event when disabled
                mock_send.assert_not_called()

    def test_track_error_disabled(self):
        """Test track_error when analytics disabled."""
        from vortex.cli.analytics import CliAnalytics

        with patch.dict(os.environ, {"VORTEX_ANALYTICS": "false"}):
            analytics = CliAnalytics()
            
            with patch.object(analytics, '_send_event') as mock_send:
                analytics.track_error("test", "Error", "message")
                
                # Should not send event when disabled
                mock_send.assert_not_called()

    @patch('vortex.cli.analytics.datetime')
    def test_track_command_event_structure(self, mock_datetime):
        """Test track_command creates properly structured event."""
        from vortex.cli.analytics import CliAnalytics
        
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        with patch.dict(os.environ, {"VORTEX_ANALYTICS": "true"}):
            analytics = CliAnalytics()
            
            with patch.object(analytics, '_send_event') as mock_send:
                analytics.track_command(
                    "download",
                    provider="yahoo", 
                    success=True,
                    duration_ms=1500.5,
                    symbol_count=5
                )
                
                mock_send.assert_called_once()
                event = mock_send.call_args[0][0]
                
                assert event["event"] == "command_executed"
                assert event["command"] == "download"
                assert event["provider"] == "yahoo"
                assert event["success"] is True
                assert event["duration_ms"] == 1500.5
                assert event["symbol_count"] == 5
                assert "timestamp" in event
                assert "session_id" in event
                assert "user_id" in event
                assert "platform" in event
                assert "python_version" in event

    @patch('vortex.cli.analytics.datetime')
    def test_track_error_event_structure(self, mock_datetime):
        """Test track_error creates properly structured event."""
        from vortex.cli.analytics import CliAnalytics
        
        # Mock datetime
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        with patch.dict(os.environ, {"VORTEX_ANALYTICS": "true"}):
            analytics = CliAnalytics()
            
            with patch.object(analytics, '_send_event') as mock_send:
                analytics.track_error("download", "NetworkError", "Connection timeout")
                
                mock_send.assert_called_once()
                event = mock_send.call_args[0][0]
                
                assert event["event"] == "command_error"
                assert event["command"] == "download"
                assert event["error_type"] == "NetworkError"
                assert event["error_message"] == "Connection timeout"
                assert "timestamp" in event
                assert "session_id" in event
                assert "user_id" in event
                assert "platform" in event
                assert "python_version" in event

    def test_safe_kwargs_filtering(self):
        """Test that sensitive kwargs are filtered out."""
        from vortex.cli.analytics import CliAnalytics

        with patch.dict(os.environ, {"VORTEX_ANALYTICS": "true"}):
            analytics = CliAnalytics()
            
            with patch.object(analytics, '_send_event') as mock_send:
                analytics.track_command(
                    "config",
                    password="secret123",  # Should be filtered
                    username="user",       # Should be filtered  
                    credentials="token",   # Should be filtered
                    provider="yahoo",      # Should be included
                    count=10               # Should be included
                )
                
                event = mock_send.call_args[0][0]
                
                # Sensitive data should be filtered out
                assert "password" not in event
                assert "username" not in event  
                assert "credentials" not in event
                
                # Safe data should be included
                assert event["provider"] == "yahoo"
                assert event["count"] == 10

    def test_large_list_handling(self):
        """Test that large lists are filtered out and small lists converted to counts."""
        from vortex.cli.analytics import CliAnalytics

        with patch.dict(os.environ, {"VORTEX_ANALYTICS": "true"}):
            analytics = CliAnalytics()
            
            with patch.object(analytics, '_send_event') as mock_send:
                large_list = list(range(150))  # Over 100 items - should be filtered out
                small_list = list(range(5))    # Under 100 items - should be converted to count
                
                analytics.track_command(
                    "download",
                    large_symbols=large_list,
                    small_symbols=small_list
                )
                
                event = mock_send.call_args[0][0]
                
                # Large list should be filtered out completely (not included)
                assert "large_symbols" not in event
                # Small list should be converted to count
                assert event["small_symbols"] == 5


class TestAnalyticsErrorHandling:
    """Test analytics functions handle errors gracefully."""

    def test_save_config_error_handling(self):
        """Test _save_config handles errors gracefully."""
        from vortex.cli.analytics import CliAnalytics

        analytics = CliAnalytics()
        
        # Mock mkdir and open to raise exceptions
        with patch('pathlib.Path.mkdir', side_effect=OSError("Permission denied")):
            with patch('builtins.open', side_effect=OSError("Cannot write")):
                # Should not raise exception
                analytics._save_config({"enabled": True})

    def test_track_command_error_handling(self):
        """Test track_command handles errors gracefully."""
        from vortex.cli.analytics import CliAnalytics

        with patch.dict(os.environ, {"VORTEX_ANALYTICS": "true"}):
            analytics = CliAnalytics()
            
            # Mock _send_event to raise exception
            with patch.object(analytics, '_send_event', side_effect=Exception("Network error")):
                # Should not raise exception
                analytics.track_command("test")

    def test_track_error_error_handling(self):
        """Test track_error handles errors gracefully."""
        from vortex.cli.analytics import CliAnalytics

        with patch.dict(os.environ, {"VORTEX_ANALYTICS": "true"}):
            analytics = CliAnalytics()
            
            # Mock _send_event to raise exception
            with patch.object(analytics, '_send_event', side_effect=Exception("Network error")):
                # Should not raise exception
                analytics.track_error("test", "Error", "message")

    def test_count_stored_events_error_handling(self):
        """Test _count_stored_events handles errors gracefully."""
        from vortex.cli.analytics import CliAnalytics

        analytics = CliAnalytics()
        
        # Mock open to raise exception
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', side_effect=OSError("Permission denied")):
                count = analytics._count_stored_events()
                assert count == 0  # Should return 0 on error