import pytest
import logging
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

from vortex.logging.manager import LoggingManager, logging_manager, configure_logging
from vortex.logging.config import LoggingConfig
from vortex.logging.loggers import VortexLogger
from vortex.logging.performance import PerformanceLogger


class TestLoggingManager:
    def setup_method(self):
        """Reset the singleton for each test."""
        # Reset the singleton instance
        LoggingManager._instance = None
        LoggingManager._initialized = False

    def test_singleton_behavior(self):
        """Test that LoggingManager is a singleton."""
        manager1 = LoggingManager()
        manager2 = LoggingManager()
        
        assert manager1 is manager2
        assert LoggingManager._instance is manager1

    def test_initialization(self):
        """Test LoggingManager initialization."""
        manager = LoggingManager()
        
        assert manager.config is None
        assert manager.handlers == []
        assert LoggingManager._initialized is True

    def test_multiple_init_calls_dont_reinitialize(self):
        """Test that multiple __init__ calls don't reinitialize."""
        manager = LoggingManager()
        original_handlers = manager.handlers
        
        # Call __init__ again
        manager.__init__()
        
        # Should be the same handlers list object
        assert manager.handlers is original_handlers

    @patch('vortex.logging.manager.rich_available', True)
    @patch('vortex.logging.manager.create_rich_handler')
    def test_configure_with_rich_console_output(self, mock_create_rich_handler):
        """Test configure with rich console output."""
        mock_handler = Mock()
        mock_create_rich_handler.return_value = mock_handler
        
        config = LoggingConfig(
            level=logging.INFO,
            output=["console"],
            format_type="rich"
        )
        
        manager = LoggingManager()
        manager.configure(config)
        
        assert manager.config == config
        mock_create_rich_handler.assert_called_once()
        mock_handler.setFormatter.assert_called_once()
        mock_handler.setLevel.assert_called_once_with(logging.INFO)

    @patch('vortex.logging.manager.rich_available', False)
    @patch('logging.StreamHandler')
    @patch('vortex.logging.manager.create_console_formatter')
    def test_configure_with_console_output_no_rich(self, mock_create_formatter, mock_stream_handler):
        """Test configure with console output when rich is not available."""
        mock_handler = Mock()
        mock_stream_handler.return_value = mock_handler
        mock_formatter = Mock()
        mock_create_formatter.return_value = mock_formatter
        
        config = LoggingConfig(
            level=logging.DEBUG,
            output=["console"],
            format_type="rich"  # Should fall back to console format
        )
        
        manager = LoggingManager()
        manager.configure(config)
        
        mock_stream_handler.assert_called_with(sys.stderr)
        mock_handler.setFormatter.assert_called_with(mock_formatter)
        mock_handler.setLevel.assert_called_with(logging.DEBUG)

    @patch('logging.StreamHandler')
    @patch('vortex.logging.manager.StructuredFormatter')
    def test_configure_with_json_console_output(self, mock_structured_formatter, mock_stream_handler):
        """Test configure with JSON console output."""
        mock_handler = Mock()
        mock_stream_handler.return_value = mock_handler
        mock_formatter = Mock()
        mock_structured_formatter.return_value = mock_formatter
        
        config = LoggingConfig(
            level=logging.WARNING,
            output=["console"],
            format_type="json",
            service_name="test-service",
            version="1.0.0"
        )
        
        manager = LoggingManager()
        manager.configure(config)
        
        mock_stream_handler.assert_called_with(sys.stderr)
        mock_structured_formatter.assert_called_with("test-service", "1.0.0")
        mock_handler.setFormatter.assert_called_with(mock_formatter)

    def test_configure_with_file_output(self):
        """Test configure with file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            config = LoggingConfig(
                level=logging.ERROR,
                output=["file"],
                format_type="console",
                file_path=log_file,
                max_file_size=1024 * 1024,
                backup_count=3
            )
            
            manager = LoggingManager()
            manager.configure(config)
            
            assert len(manager.handlers) == 1
            handler = manager.handlers[0]
            assert isinstance(handler, logging.handlers.RotatingFileHandler)
            assert handler.maxBytes == 1024 * 1024
            assert handler.backupCount == 3

    def test_configure_with_file_output_default_path(self):
        """Test configure with file output using default path."""
        config = LoggingConfig(
            level=logging.INFO,
            output=["file"],
            format_type="console"
        )
        
        manager = LoggingManager()
        
        with patch('pathlib.Path.mkdir') as mock_mkdir:
            with patch('logging.handlers.RotatingFileHandler') as mock_handler_class:
                mock_handler = Mock()
                mock_handler_class.return_value = mock_handler
                
                manager.configure(config)
                
                # Should use default path
                expected_path = Path("logs/vortex.log")
                mock_handler_class.assert_called_once_with(
                    expected_path,
                    maxBytes=config.max_file_size,
                    backupCount=config.backup_count
                )
                mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch('vortex.logging.manager.StructuredFormatter')
    def test_configure_with_file_json_output(self, mock_structured_formatter):
        """Test configure with JSON file output."""
        mock_formatter = Mock()
        mock_structured_formatter.return_value = mock_formatter
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            config = LoggingConfig(
                level=logging.INFO,
                output=["file"],
                format_type="json",
                file_path=log_file,
                service_name="test-service",
                version="2.0.0"
            )
            
            manager = LoggingManager()
            manager.configure(config)
            
            mock_structured_formatter.assert_called_with("test-service", "2.0.0")
            assert len(manager.handlers) == 1

    def test_configure_with_multiple_outputs(self):
        """Test configure with both console and file outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            config = LoggingConfig(
                level=logging.INFO,
                output=["console", "file"],
                format_type="console",
                file_path=log_file
            )
            
            manager = LoggingManager()
            manager.configure(config)
            
            assert len(manager.handlers) == 2

    def test_configure_clears_existing_handlers(self):
        """Test that configure clears existing handlers."""
        manager = LoggingManager()
        
        # Add some dummy handlers first
        dummy_handler = Mock()
        manager.handlers.append(dummy_handler)
        logging.getLogger().addHandler(dummy_handler)
        
        config = LoggingConfig(
            level=logging.INFO,
            output=["console"],
            format_type="console"
        )
        
        manager.configure(config)
        
        # Old handler should be removed, new handler should be added
        assert dummy_handler not in manager.handlers
        assert len(manager.handlers) == 1

    def test_configure_sets_vortex_logger_levels(self):
        """Test that configure sets levels for vortex loggers."""
        # Create some mock vortex loggers
        with patch('logging.Logger.manager') as mock_manager:
            mock_manager.loggerDict = {
                'vortex.test1': Mock(),
                'vortex.test2': Mock(),
                'other.logger': Mock()
            }
            
            with patch('logging.getLogger') as mock_get_logger:
                mock_loggers = {
                    'vortex.test1': Mock(),
                    'vortex.test2': Mock(),
                    'other.logger': Mock(),
                    '': Mock()  # root logger
                }
                mock_get_logger.side_effect = lambda name='': mock_loggers.get(name, Mock())
                
                config = LoggingConfig(
                    level=logging.WARNING,
                    output=["console"],
                    format_type="console"
                )
                
                manager = LoggingManager()
                manager.configure(config)
                
                # Vortex loggers should have level set
                mock_loggers['vortex.test1'].setLevel.assert_called_with(logging.WARNING)
                mock_loggers['vortex.test2'].setLevel.assert_called_with(logging.WARNING)
                
                # Other logger should not have level set
                mock_loggers['other.logger'].setLevel.assert_not_called()

    def test_get_logger(self):
        """Test get_logger method."""
        manager = LoggingManager()
        
        logger = manager.get_logger("test.logger", "correlation-123")
        
        assert isinstance(logger, VortexLogger)
        assert logger.name == "test.logger"
        assert logger.correlation_id == "correlation-123"

    def test_get_logger_without_correlation_id(self):
        """Test get_logger method without correlation ID."""
        manager = LoggingManager()
        
        logger = manager.get_logger("test.logger")
        
        assert isinstance(logger, VortexLogger)
        assert logger.name == "test.logger"
        assert logger.correlation_id is None

    def test_get_performance_logger(self):
        """Test get_performance_logger method."""
        manager = LoggingManager()
        
        logger = manager.get_performance_logger("perf.logger", "correlation-456")
        
        assert isinstance(logger, PerformanceLogger)
        assert logger.name == "perf.logger"
        assert logger.correlation_id == "correlation-456"

    def test_get_performance_logger_without_correlation_id(self):
        """Test get_performance_logger method without correlation ID."""
        manager = LoggingManager()
        
        logger = manager.get_performance_logger("perf.logger")
        
        assert isinstance(logger, PerformanceLogger)
        assert logger.name == "perf.logger"
        assert logger.correlation_id is None


class TestGlobalLoggingManager:
    def test_global_logging_manager_is_singleton(self):
        """Test that the global logging_manager is the singleton instance."""
        manager = LoggingManager()
        assert logging_manager is manager

    def test_configure_logging_function(self):
        """Test the configure_logging convenience function."""
        config = LoggingConfig(
            level=logging.INFO,
            output=["console"],
            format_type="console"
        )
        
        with patch.object(logging_manager, 'configure') as mock_configure:
            configure_logging(config)
            mock_configure.assert_called_once_with(config)


class TestLoggingManagerEdgeCases:
    def setup_method(self):
        """Reset the singleton for each test."""
        LoggingManager._instance = None
        LoggingManager._initialized = False

    def test_configure_with_empty_output_list(self):
        """Test configure with empty output list."""
        config = LoggingConfig(
            level=logging.INFO,
            output=[],  # Empty list
            format_type="console"
        )
        
        manager = LoggingManager()
        manager.configure(config)
        
        assert len(manager.handlers) == 0

    def test_configure_with_unknown_output_type(self):
        """Test configure with unknown output type."""
        config = LoggingConfig(
            level=logging.INFO,
            output=["unknown_output"],
            format_type="console"
        )
        
        manager = LoggingManager()
        manager.configure(config)
        
        # Should not create any handlers for unknown output types
        assert len(manager.handlers) == 0

    def test_file_handler_directory_creation_error(self):
        """Test file handler when directory creation fails."""
        with patch('pathlib.Path.mkdir', side_effect=OSError("Permission denied")):
            config = LoggingConfig(
                level=logging.INFO,
                output=["file"],
                file_path=Path("/invalid/path/test.log")
            )
            
            manager = LoggingManager()
            
            # Should raise the OSError from mkdir
            with pytest.raises(OSError):
                manager.configure(config)