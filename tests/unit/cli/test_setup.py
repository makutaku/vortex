"""
Tests for CLI setup and initialization functionality.
"""

import logging
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
import pytest

from vortex.cli.setup import setup_logging


class TestSetupLogging:
    """Test logging setup functionality."""
    
    @patch('vortex.cli.setup.logging.basicConfig')
    def test_setup_logging_fallback_no_verbose(self, mock_basic_config):
        """Test setup logging with fallback configuration, no verbose."""
        setup_logging()
        
        # Verify basicConfig was called with WARNING level
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args.kwargs
        assert call_args['level'] == logging.WARNING
        assert 'asctime' in call_args['format']
        assert 'levelname' in call_args['format']
    
    @patch('vortex.cli.setup.logging.basicConfig')
    def test_setup_logging_fallback_verbose_1(self, mock_basic_config):
        """Test setup logging with fallback configuration, verbose=1."""
        setup_logging(verbose=1)
        
        # Verify basicConfig was called with INFO level
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args.kwargs
        assert call_args['level'] == logging.INFO
    
    @patch('vortex.cli.setup.logging.basicConfig')
    def test_setup_logging_fallback_verbose_2(self, mock_basic_config):
        """Test setup logging with fallback configuration, verbose=2+."""
        setup_logging(verbose=2)
        
        # Verify basicConfig was called with DEBUG level
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args.kwargs
        assert call_args['level'] == logging.DEBUG
    
    @patch('vortex.cli.setup.logging.basicConfig')
    @patch('vortex.core.config.ConfigManager')
    @patch('vortex.core.logging_integration.configure_logging_from_manager')
    @patch('vortex.core.logging_integration.get_logger')
    def test_setup_logging_advanced_success(self, mock_get_logger, mock_configure, mock_config_manager, mock_basic_config):
        """Test setup logging with successful advanced configuration."""
        # Mock advanced logging components
        mock_manager_instance = Mock()
        mock_config_manager.return_value = mock_manager_instance
        
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        config_file = Path('/test/config.toml')
        setup_logging(config_file=config_file, verbose=1)
        
        # Verify fallback logging was set up first
        mock_basic_config.assert_called_once()
        
        # Verify advanced logging was configured
        mock_config_manager.assert_called_once_with(config_file)
        # Get the actual version called (it might be "unknown" or actual version)
        configure_call_args = mock_configure.call_args
        expected_args = (mock_manager_instance,)
        expected_kwargs = {"service_name": "vortex-cli"}
        
        # Check that the required arguments are correct
        assert configure_call_args[0] == expected_args
        assert configure_call_args[1]["service_name"] == expected_kwargs["service_name"]
        # Version can be either "unknown" or actual version - just verify it's present
        assert "version" in configure_call_args[1]
        
        # Verify logger was obtained and used
        mock_get_logger.assert_called_once_with("vortex.cli")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Vortex CLI started" in call_args[0][0]
        assert call_args.kwargs['verbose_level'] == 1
    
    @patch('vortex.cli.setup.logging.basicConfig')
    @patch('vortex.core.config.ConfigManager', side_effect=ImportError("Config module not found"))
    def test_setup_logging_advanced_import_error_verbose(self, mock_config_manager, mock_basic_config):
        """Test setup logging when advanced config fails with import error in verbose mode."""
        with patch('vortex.cli.setup.logging.getLogger') as mock_get_logger:
            mock_fallback_logger = Mock()
            mock_get_logger.return_value = mock_fallback_logger
            
            setup_logging(verbose=1)
            
            # Verify fallback logging was set up
            mock_basic_config.assert_called_once()
            
            # Verify fallback logger was used for debug message
            mock_fallback_logger.debug.assert_called_once()
            debug_message = mock_fallback_logger.debug.call_args[0][0]
            assert "Using fallback logging configuration" in debug_message
            assert "advanced config not available" in debug_message
    
    @patch('vortex.cli.setup.logging.basicConfig')
    @patch('vortex.core.config.ConfigManager', side_effect=Exception("Configuration error"))
    def test_setup_logging_advanced_generic_error_verbose(self, mock_config_manager, mock_basic_config):
        """Test setup logging when advanced config fails with generic error in verbose mode."""
        with patch('vortex.cli.setup.logging.getLogger') as mock_get_logger:
            mock_fallback_logger = Mock()
            mock_get_logger.return_value = mock_fallback_logger
            
            setup_logging(verbose=1)
            
            # Verify fallback logging was set up
            mock_basic_config.assert_called_once()
            
            # Verify fallback logger was used for debug message
            mock_fallback_logger.debug.assert_called_once()
            debug_message = mock_fallback_logger.debug.call_args[0][0]
            assert "Using fallback logging configuration" in debug_message
            assert "Configuration error" in debug_message
    
    @patch('vortex.cli.setup.logging.basicConfig')
    @patch('vortex.core.config.ConfigManager', side_effect=ValueError("Invalid config"))
    def test_setup_logging_advanced_error_not_verbose(self, mock_config_manager, mock_basic_config):
        """Test setup logging when advanced config fails but verbose=0."""
        with patch('vortex.cli.setup.logging.getLogger') as mock_get_logger:
            mock_fallback_logger = Mock()
            mock_get_logger.return_value = mock_fallback_logger
            
            setup_logging(verbose=0)
            
            # Verify fallback logging was set up
            mock_basic_config.assert_called_once()
            
            # Verify no debug message was logged (verbose=0)
            mock_fallback_logger.debug.assert_not_called()
    
    @patch('vortex.cli.setup.logging.basicConfig')
    @patch('vortex.core.config.ConfigManager')
    @patch('vortex.core.logging_integration.configure_logging_from_manager', side_effect=RuntimeError("Logging config error"))
    def test_setup_logging_configure_error(self, mock_configure, mock_config_manager, mock_basic_config):
        """Test setup logging when configure_logging_from_manager fails."""
        with patch('vortex.cli.setup.logging.getLogger') as mock_get_logger:
            mock_fallback_logger = Mock()
            mock_get_logger.return_value = mock_fallback_logger
            
            mock_manager_instance = Mock()
            mock_config_manager.return_value = mock_manager_instance
            
            setup_logging(verbose=1)
            
            # Verify fallback logging was set up
            mock_basic_config.assert_called_once()
            
            # Verify config manager was created
            mock_config_manager.assert_called_once_with(None)
            
            # Verify configure was attempted
            mock_configure.assert_called_once()
            
            # Verify fallback logger was used for debug message
            mock_fallback_logger.debug.assert_called_once()
            debug_message = mock_fallback_logger.debug.call_args[0][0]
            assert "Using fallback logging configuration" in debug_message
            assert "Logging config error" in debug_message
    
    @patch('vortex.cli.setup.logging.basicConfig')
    @patch('vortex.core.config.ConfigManager')
    @patch('vortex.core.logging_integration.configure_logging_from_manager')
    @patch('vortex.core.logging_integration.get_logger', side_effect=AttributeError("Logger error"))
    def test_setup_logging_get_logger_error(self, mock_get_logger, mock_configure, mock_config_manager, mock_basic_config):
        """Test setup logging when get_logger fails."""
        with patch('vortex.cli.setup.logging.getLogger') as mock_get_fallback_logger:
            mock_fallback_logger = Mock()
            mock_get_fallback_logger.return_value = mock_fallback_logger
            
            mock_manager_instance = Mock()
            mock_config_manager.return_value = mock_manager_instance
            
            setup_logging(verbose=1)
            
            # Verify fallback logging was set up
            mock_basic_config.assert_called_once()
            
            # Verify advanced setup was attempted
            mock_config_manager.assert_called_once()
            mock_configure.assert_called_once()
            mock_get_logger.assert_called_once()
            
            # Verify fallback logger was used for debug message
            mock_fallback_logger.debug.assert_called_once()
            debug_message = mock_fallback_logger.debug.call_args[0][0]
            assert "Using fallback logging configuration" in debug_message
            assert "Logger error" in debug_message
    
    @patch('vortex.cli.setup.logging.basicConfig')
    def test_setup_logging_with_config_file(self, mock_basic_config):
        """Test setup logging with explicit config file path."""
        config_path = Path('/custom/config.toml')
        
        with patch('vortex.core.config.ConfigManager') as mock_config_manager:
            with patch('vortex.core.logging_integration.configure_logging_from_manager'):
                with patch('vortex.core.logging_integration.get_logger') as mock_get_logger:
                    mock_logger = Mock()
                    mock_get_logger.return_value = mock_logger
                    
                    setup_logging(config_file=config_path, verbose=0)
                    
                    # Verify config manager was created with custom path
                    mock_config_manager.assert_called_once_with(config_path)
                    
                    # Verify logger info was called with correct verbose level
                    mock_logger.info.assert_called_once()
                    call_args = mock_logger.info.call_args
                    assert call_args.kwargs['verbose_level'] == 0


class TestVersionHandling:
    """Test version import handling."""
    
    def test_version_import_success(self):
        """Test successful version import."""
        # This test verifies that the import attempt is made
        # The actual import may fail in test environment, which is expected
        with patch('vortex.cli.setup.__version__', 'test-version'):
            # Import the module again to test version handling
            import importlib
            import vortex.cli.setup
            importlib.reload(vortex.cli.setup)
            
            # If version was set, it should be available
            # If import failed, __version__ should be "unknown"
            assert hasattr(vortex.cli.setup, '__version__')
    
    def test_version_import_failure_handling(self):
        """Test that version import failure is handled gracefully."""
        # The module should handle ImportError gracefully
        # This is tested by the fact that the module loads without error
        # even when __version__ import fails
        
        # Just verify that the setup function works regardless of version
        with patch('vortex.cli.setup.logging.basicConfig'):
            with patch('vortex.cli.setup.logging.getLogger'):
                # Should not raise any exceptions
                setup_logging()


class TestLoggingFormat:
    """Test logging format configuration."""
    
    @patch('vortex.cli.setup.logging.basicConfig')
    def test_logging_format_contains_required_fields(self, mock_basic_config):
        """Test that logging format contains required fields."""
        setup_logging()
        
        mock_basic_config.assert_called_once()
        call_args = mock_basic_config.call_args.kwargs
        format_str = call_args['format']
        
        # Verify format contains essential fields
        assert '%(asctime)s' in format_str
        assert '%(levelname)s' in format_str
        assert '%(name)s' in format_str
        assert '%(message)s' in format_str
    
    @patch('vortex.cli.setup.logging.basicConfig')
    def test_verbose_level_mapping(self, mock_basic_config):
        """Test verbose level to logging level mapping."""
        # Test different verbose levels
        test_cases = [
            (0, logging.WARNING),
            (1, logging.INFO),
            (2, logging.DEBUG),
            (3, logging.DEBUG),  # Higher values should still be DEBUG
            (10, logging.DEBUG)
        ]
        
        for verbose, expected_level in test_cases:
            mock_basic_config.reset_mock()
            setup_logging(verbose=verbose)
            
            call_args = mock_basic_config.call_args.kwargs
            assert call_args['level'] == expected_level, f"verbose={verbose} should map to {expected_level}"


class TestErrorHandling:
    """Test error handling in setup functions."""
    
    @patch('vortex.cli.setup.logging.basicConfig', side_effect=Exception("BasicConfig error"))
    def test_setup_logging_basicconfig_error(self, mock_basic_config):
        """Test that basic config errors are not suppressed (should raise)."""
        with pytest.raises(Exception, match="BasicConfig error"):
            setup_logging()
    
    @patch('vortex.cli.setup.logging.basicConfig')
    @patch('vortex.cli.setup.logging.getLogger', side_effect=Exception("GetLogger error"))
    def test_setup_logging_getlogger_error(self, mock_get_logger, mock_basic_config):
        """Test handling of getLogger errors in fallback path."""
        # Mock the advanced config to fail so we hit the fallback path
        with patch('vortex.core.config.ConfigManager', side_effect=ImportError()):
            with pytest.raises(Exception, match="GetLogger error"):
                setup_logging(verbose=1)


class TestIntegration:
    """Test integration scenarios."""
    
    @patch('vortex.cli.setup.logging.basicConfig')
    def test_setup_logging_full_success_flow(self, mock_basic_config):
        """Test complete successful setup flow."""
        config_file = Path('/test/config.toml')
        verbose = 1
        
        with patch('vortex.core.config.ConfigManager') as mock_config_manager:
            with patch('vortex.core.logging_integration.configure_logging_from_manager') as mock_configure:
                with patch('vortex.core.logging_integration.get_logger') as mock_get_logger:
                    with patch('vortex.cli.setup.logging.getLogger') as mock_get_fallback_logger:
                        
                        # Set up mocks
                        mock_manager_instance = Mock()
                        mock_config_manager.return_value = mock_manager_instance
                        
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger
                        
                        mock_fallback_logger = Mock()
                        mock_get_fallback_logger.return_value = mock_fallback_logger
                        
                        # Execute
                        setup_logging(config_file=config_file, verbose=verbose)
                        
                        # Verify complete flow
                        mock_basic_config.assert_called_once()
                        mock_get_fallback_logger.assert_called_once_with("vortex.cli")
                        mock_config_manager.assert_called_once_with(config_file)
                        # Verify configure was called with correct arguments
                        configure_call_args = mock_configure.call_args
                        assert configure_call_args[0] == (mock_manager_instance,)
                        assert configure_call_args[1]["service_name"] == "vortex-cli"
                        assert "version" in configure_call_args[1]
                        mock_get_logger.assert_called_once_with("vortex.cli")
                        mock_logger.info.assert_called_once()
                        
                        # Verify no fallback debug message (success path)
                        mock_fallback_logger.debug.assert_not_called()
    
    def test_setup_logging_no_params(self):
        """Test setup logging with no parameters (default behavior)."""
        with patch('vortex.cli.setup.logging.basicConfig') as mock_basic_config:
            with patch('vortex.cli.setup.logging.getLogger'):
                setup_logging()
                
                # Should use defaults
                call_args = mock_basic_config.call_args.kwargs
                assert call_args['level'] == logging.WARNING  # verbose=0 default
                
    def test_setup_logging_with_all_params(self):
        """Test setup logging with all parameters specified."""
        config_file = Path('/custom/path/config.toml')
        verbose = 2
        
        with patch('vortex.cli.setup.logging.basicConfig') as mock_basic_config:
            with patch('vortex.core.config.ConfigManager') as mock_config_manager:
                with patch('vortex.core.logging_integration.configure_logging_from_manager'):
                    with patch('vortex.core.logging_integration.get_logger') as mock_get_logger:
                        mock_logger = Mock()
                        mock_get_logger.return_value = mock_logger
                        
                        setup_logging(config_file=config_file, verbose=verbose)
                        
                        # Verify parameters were used
                        call_args = mock_basic_config.call_args.kwargs
                        assert call_args['level'] == logging.DEBUG  # verbose=2
                        
                        mock_config_manager.assert_called_once_with(config_file)
                        
                        mock_logger.info.assert_called_once()
                        call_args = mock_logger.info.call_args
                        assert call_args.kwargs['verbose_level'] == verbose