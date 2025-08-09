"""
Unit tests for LoggingManager.

Tests the centralized logging configuration and management functionality.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import pytest

from vortex.logging.config import LoggingConfig
from vortex.logging.manager import LoggingManager, logging_manager, configure_logging


@pytest.mark.unit
class TestLoggingManagerSingleton:
    """Test LoggingManager singleton behavior."""
    
    def test_singleton_pattern(self):
        """Test that LoggingManager is a singleton."""
        manager1 = LoggingManager()
        manager2 = LoggingManager()
        
        assert manager1 is manager2
        assert id(manager1) == id(manager2)
    
    def test_singleton_initialization_once(self):
        """Test that initialization only happens once."""
        # Get fresh instance
        LoggingManager._instance = None
        LoggingManager._initialized = False
        
        manager1 = LoggingManager()
        assert manager1._initialized is True
        assert manager1.config is None
        assert manager1.handlers == []
        
        # Second instance should not re-initialize
        manager2 = LoggingManager()
        manager2.config = "test"
        manager2.handlers = ["test_handler"]
        
        manager3 = LoggingManager()
        assert manager3.config == "test"
        assert manager3.handlers == ["test_handler"]


@pytest.mark.unit
class TestLoggingManagerConfiguration:
    """Test LoggingManager configuration functionality."""
    
    def setup_method(self):
        """Set up fresh LoggingManager for each test."""
        # Save original state
        self._original_instance = LoggingManager._instance
        self._original_initialized = LoggingManager._initialized
        self._original_root_handlers = logging.getLogger().handlers[:]
        self._original_root_level = logging.getLogger().level
        
        # Reset for test
        LoggingManager._instance = None
        LoggingManager._initialized = False
        self.manager = LoggingManager()
    
    def teardown_method(self):
        """Restore original state after each test."""
        # Clear all handlers from root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Restore original handlers and level
        root_logger.handlers.extend(self._original_root_handlers)
        root_logger.setLevel(self._original_root_level)
        
        # Restore singleton state
        LoggingManager._instance = self._original_instance
        LoggingManager._initialized = self._original_initialized
    
    def test_configure_clears_existing_handlers(self):
        """Test that configure clears existing handlers."""
        config = LoggingConfig(
            level=logging.INFO,
            output=["console"],
            format_type="console"
        )
        
        # Add some existing handlers
        root_logger = logging.getLogger()
        existing_handler = logging.StreamHandler()
        root_logger.addHandler(existing_handler)
        
        initial_handler_count = len(root_logger.handlers)
        assert initial_handler_count >= 1
        
        # Configure should clear existing handlers
        self.manager.configure(config)
        
        # Should have exactly one handler (the console handler we added)
        assert len(root_logger.handlers) == 1
        assert len(self.manager.handlers) == 1
    
    def test_configure_sets_root_level(self):
        """Test that configure sets the root logging level."""
        config = LoggingConfig(
            level=logging.DEBUG,
            output=["console"],
            format_type="console"
        )
        
        self.manager.configure(config)
        
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_configure_sets_vortex_logger_levels(self):
        """Test that configure sets levels for all Vortex loggers."""
        # Create some vortex loggers first
        vortex_logger1 = logging.getLogger("vortex.test1")
        vortex_logger2 = logging.getLogger("vortex.test2")
        non_vortex_logger = logging.getLogger("other.test")
        
        config = LoggingConfig(
            level=logging.WARNING,
            output=["console"],
            format_type="console"
        )
        
        self.manager.configure(config)
        
        assert vortex_logger1.level == logging.WARNING
        assert vortex_logger2.level == logging.WARNING
        # Non-vortex logger should not be affected by the vortex-specific setting
        assert non_vortex_logger.level != logging.WARNING or non_vortex_logger.level == logging.NOTSET
    
    def test_configure_console_output(self):
        """Test configuring console output."""
        config = LoggingConfig(
            level=logging.INFO,
            output=["console"],
            format_type="console"
        )
        
        self.manager.configure(config)
        
        assert len(self.manager.handlers) == 1
        handler = self.manager.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr
    
    def test_configure_file_output(self):
        """Test configuring file output."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            config = LoggingConfig(
                level=logging.INFO,
                output=["file"],
                format_type="console",
                file_path=log_file
            )
            
            self.manager.configure(config)
            
            assert len(self.manager.handlers) == 1
            handler = self.manager.handlers[0]
            assert isinstance(handler, logging.handlers.RotatingFileHandler)
    
    def test_configure_multiple_outputs(self):
        """Test configuring multiple output types."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            config = LoggingConfig(
                level=logging.INFO,
                output=["console", "file"],
                format_type="console",
                file_path=log_file
            )
            
            self.manager.configure(config)
            
            assert len(self.manager.handlers) == 2
            handler_types = [type(h).__name__ for h in self.manager.handlers]
            assert "StreamHandler" in handler_types
            assert "RotatingFileHandler" in handler_types


@pytest.mark.unit 
class TestLoggingManagerConsoleHandler:
    """Test console handler configuration."""
    
    def setup_method(self):
        """Set up fresh LoggingManager for each test."""
        # Save original state
        self._original_instance = LoggingManager._instance
        self._original_initialized = LoggingManager._initialized
        self._original_root_handlers = logging.getLogger().handlers[:]
        self._original_root_level = logging.getLogger().level
        
        # Reset for test
        LoggingManager._instance = None
        LoggingManager._initialized = False
        self.manager = LoggingManager()
    
    def teardown_method(self):
        """Restore original state after each test."""
        # Clear all handlers from root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Restore original handlers and level
        root_logger.handlers.extend(self._original_root_handlers)
        root_logger.setLevel(self._original_root_level)
        
        # Restore singleton state
        LoggingManager._instance = self._original_instance
        LoggingManager._initialized = self._original_initialized
    
    @patch('vortex.logging.manager.rich_available', False)
    def test_add_console_handler_console_format_no_rich(self):
        """Test console handler with console format when rich not available."""
        config = LoggingConfig(
            level=logging.INFO,
            format_type="console"
        )
        
        self.manager._add_console_handler(config)
        
        assert len(self.manager.handlers) == 1
        handler = self.manager.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr
    
    def test_add_console_handler_json_format(self):
        """Test console handler with JSON format."""
        config = LoggingConfig(
            level=logging.INFO,
            format_type="json",
            service_name="test-service",
            version="1.0.0"
        )
        
        with patch('vortex.logging.manager.StructuredFormatter') as mock_formatter:
            self.manager._add_console_handler(config)
            
            mock_formatter.assert_called_once_with("test-service", "1.0.0")
            assert len(self.manager.handlers) == 1
    
    @patch('vortex.logging.manager.rich_available', True)
    @patch('vortex.logging.manager.create_rich_handler')
    def test_add_console_handler_rich_format(self, mock_rich_handler):
        """Test console handler with rich format when rich is available."""
        mock_handler = Mock()
        mock_rich_handler.return_value = mock_handler
        
        config = LoggingConfig(
            level=logging.INFO,
            format_type="rich"
        )
        
        self.manager._add_console_handler(config)
        
        mock_rich_handler.assert_called_once()
        mock_handler.setFormatter.assert_called_once()
        assert mock_handler in self.manager.handlers


@pytest.mark.unit
class TestLoggingManagerFileHandler:
    """Test file handler configuration."""
    
    def setup_method(self):
        """Set up fresh LoggingManager for each test."""
        # Save original state
        self._original_instance = LoggingManager._instance
        self._original_initialized = LoggingManager._initialized
        self._original_root_handlers = logging.getLogger().handlers[:]
        self._original_root_level = logging.getLogger().level
        
        # Reset for test
        LoggingManager._instance = None
        LoggingManager._initialized = False
        self.manager = LoggingManager()
    
    def teardown_method(self):
        """Restore original state after each test."""
        # Clear all handlers from root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Restore original handlers and level
        root_logger.handlers.extend(self._original_root_handlers)
        root_logger.setLevel(self._original_root_level)
        
        # Restore singleton state
        LoggingManager._instance = self._original_instance
        LoggingManager._initialized = self._original_initialized
    
    def test_add_file_handler_default_path(self):
        """Test file handler with default path when none specified."""
        config = LoggingConfig(
            level=logging.INFO,
            format_type="console"
        )
        # Don't set file_path to test default
        
        with patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('logging.handlers.RotatingFileHandler') as mock_handler:
            
            mock_handler_instance = Mock()
            mock_handler.return_value = mock_handler_instance
            
            self.manager._add_file_handler(config)
            
            # Should use default path
            assert config.file_path == Path("logs/vortex.log")
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            mock_handler.assert_called_once_with(
                config.file_path,
                maxBytes=config.max_file_size,
                backupCount=config.backup_count
            )
    
    def test_add_file_handler_json_format(self):
        """Test file handler with JSON format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            config = LoggingConfig(
                level=logging.INFO,
                format_type="json",
                file_path=log_file,
                service_name="test-service",
                version="1.0.0"
            )
            
            with patch('vortex.logging.manager.StructuredFormatter') as mock_formatter:
                self.manager._add_file_handler(config)
                
                mock_formatter.assert_called_once_with("test-service", "1.0.0")
                assert len(self.manager.handlers) == 1
    
    def test_add_file_handler_console_format(self):
        """Test file handler with console format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            
            config = LoggingConfig(
                level=logging.INFO,
                format_type="console",
                file_path=log_file
            )
            
            with patch('vortex.logging.manager.create_console_formatter') as mock_formatter, \
                 patch('logging.handlers.RotatingFileHandler') as mock_handler_class:
                
                mock_formatter_instance = Mock()
                mock_formatter.return_value = mock_formatter_instance
                
                mock_handler_instance = Mock()
                mock_handler_class.return_value = mock_handler_instance
                
                self.manager._add_file_handler(config)
                
                mock_formatter.assert_called_once()
                assert len(self.manager.handlers) == 1
                mock_handler_instance.setFormatter.assert_called_once_with(mock_formatter_instance)


@pytest.mark.unit
class TestLoggingManagerLoggerCreation:
    """Test logger creation methods."""
    
    def setup_method(self):
        """Set up fresh LoggingManager for each test."""
        # Save original state
        self._original_instance = LoggingManager._instance
        self._original_initialized = LoggingManager._initialized
        self._original_root_handlers = logging.getLogger().handlers[:]
        self._original_root_level = logging.getLogger().level
        
        # Reset for test
        LoggingManager._instance = None
        LoggingManager._initialized = False
        self.manager = LoggingManager()
    
    def teardown_method(self):
        """Restore original state after each test."""
        # Clear all handlers from root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Restore original handlers and level
        root_logger.handlers.extend(self._original_root_handlers)
        root_logger.setLevel(self._original_root_level)
        
        # Restore singleton state
        LoggingManager._instance = self._original_instance
        LoggingManager._initialized = self._original_initialized
    
    def test_get_logger(self):
        """Test getting a VortexLogger instance."""
        logger = self.manager.get_logger("test.module")
        
        from vortex.logging.loggers import VortexLogger
        assert isinstance(logger, VortexLogger)
        assert logger.logger.name == "test.module"
    
    def test_get_logger_with_correlation_id(self):
        """Test getting a VortexLogger with correlation ID."""
        logger = self.manager.get_logger("test.module", "test-correlation-123")
        
        from vortex.logging.loggers import VortexLogger
        assert isinstance(logger, VortexLogger)
        assert logger.correlation_id == "test-correlation-123"
    
    def test_get_performance_logger(self):
        """Test getting a PerformanceLogger instance."""
        perf_logger = self.manager.get_performance_logger("test.module")
        
        from vortex.logging.performance import PerformanceLogger
        assert isinstance(perf_logger, PerformanceLogger)
        assert perf_logger.logger.logger.name == "test.module.performance"
    
    def test_get_performance_logger_with_correlation_id(self):
        """Test getting a PerformanceLogger with correlation ID."""
        perf_logger = self.manager.get_performance_logger("test.module", "test-correlation-123")
        
        from vortex.logging.performance import PerformanceLogger
        assert isinstance(perf_logger, PerformanceLogger)
        assert perf_logger.logger.correlation_id == "test-correlation-123"


@pytest.mark.unit
class TestGlobalLoggingManager:
    """Test global logging manager instance and configuration function."""
    
    def test_global_logging_manager_instance(self):
        """Test that global logging_manager is a LoggingManager instance."""
        assert isinstance(logging_manager, LoggingManager)
    
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


@pytest.mark.unit
class TestLoggingManagerRichIntegration:
    """Test rich logging integration scenarios."""
    
    def setup_method(self):
        """Set up fresh LoggingManager for each test."""
        # Save original state
        self._original_instance = LoggingManager._instance
        self._original_initialized = LoggingManager._initialized
        self._original_root_handlers = logging.getLogger().handlers[:]
        self._original_root_level = logging.getLogger().level
        
        # Reset for test
        LoggingManager._instance = None
        LoggingManager._initialized = False
        self.manager = LoggingManager()
    
    def teardown_method(self):
        """Restore original state after each test."""
        # Clear all handlers from root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        # Restore original handlers and level
        root_logger.handlers.extend(self._original_root_handlers)
        root_logger.setLevel(self._original_root_level)
        
        # Restore singleton state
        LoggingManager._instance = self._original_instance
        LoggingManager._initialized = self._original_initialized
    
    @patch('vortex.logging.manager.rich_available', True)
    @patch('vortex.logging.manager.create_rich_handler')
    def test_rich_handler_when_available(self, mock_create_rich):
        """Test rich handler creation when rich is available."""
        mock_handler = Mock()
        mock_handler.setFormatter = Mock()
        mock_create_rich.return_value = mock_handler
        
        config = LoggingConfig(
            level=logging.INFO,
            format_type="rich"
        )
        
        self.manager._add_console_handler(config)
        
        mock_create_rich.assert_called_once()
        mock_handler.setFormatter.assert_called_once()
        assert mock_handler in self.manager.handlers
    
    @patch('vortex.logging.manager.rich_available', False)
    def test_fallback_when_rich_unavailable(self):
        """Test fallback to console handler when rich is not available."""
        config = LoggingConfig(
            level=logging.INFO,
            format_type="rich"  # This should fallback to console
        )
        
        self.manager._add_console_handler(config)
        
        assert len(self.manager.handlers) == 1
        handler = self.manager.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr