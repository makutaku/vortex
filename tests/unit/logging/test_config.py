"""
Tests for logging configuration module.

Tests LoggingConfig class and configuration creation utilities.
"""

import pytest
import logging
from pathlib import Path

from vortex.logging.config import LoggingConfig, create_default_config


class TestLoggingConfig:
    """Test LoggingConfig class."""
    
    def test_logging_config_default_initialization(self):
        """Test LoggingConfig with default parameters."""
        config = LoggingConfig()
        
        assert config.level == logging.INFO
        assert config.format_type == "console"
        assert config.output == ["console"]
        assert config.file_path is None
        assert config.max_file_size == 10 * 1024 * 1024  # 10MB
        assert config.backup_count == 5
        assert config.service_name == "vortex"
        assert config.version == "unknown"
    
    def test_logging_config_custom_level_string(self):
        """Test LoggingConfig with custom level as string."""
        config = LoggingConfig(level="DEBUG")
        
        assert config.level == logging.DEBUG
    
    def test_logging_config_custom_level_int(self):
        """Test LoggingConfig with custom level as int."""
        config = LoggingConfig(level=logging.WARNING)
        
        assert config.level == logging.WARNING
    
    def test_logging_config_single_output(self):
        """Test LoggingConfig with single output string."""
        config = LoggingConfig(output="file")
        
        assert config.output == ["file"]
    
    def test_logging_config_multiple_outputs(self):
        """Test LoggingConfig with multiple outputs."""
        config = LoggingConfig(output=["console", "file"])
        
        assert config.output == ["console", "file"]
    
    def test_logging_config_custom_file_path(self):
        """Test LoggingConfig with custom file path."""
        file_path = Path("/tmp/test.log")
        config = LoggingConfig(file_path=file_path)
        
        assert config.file_path == file_path
    
    def test_logging_config_all_parameters(self):
        """Test LoggingConfig with all parameters customized."""
        config = LoggingConfig(
            level="ERROR",
            format_type="json",
            output=["console", "file"],
            file_path=Path("/tmp/app.log"),
            max_file_size=50 * 1024 * 1024,  # 50MB
            backup_count=10,
            service_name="test-service",
            version="1.0.0"
        )
        
        assert config.level == logging.ERROR
        assert config.format_type == "json"
        assert config.output == ["console", "file"]
        assert config.file_path == Path("/tmp/app.log")
        assert config.max_file_size == 50 * 1024 * 1024
        assert config.backup_count == 10
        assert config.service_name == "test-service"
        assert config.version == "1.0.0"


class TestCreateDefaultConfig:
    """Test create_default_config function."""
    
    def test_create_default_config(self):
        """Test create_default_config returns proper default configuration."""
        config = create_default_config()
        
        assert isinstance(config, LoggingConfig)
        assert config.level == logging.INFO
        assert config.format_type == "console"
        assert config.output == ["console"]
        assert config.service_name == "vortex"
        assert config.version == "unknown"
    
    def test_create_default_config_independence(self):
        """Test that multiple calls to create_default_config return independent objects."""
        config1 = create_default_config()
        config2 = create_default_config()
        
        assert config1 is not config2
        assert config1.service_name == config2.service_name
        
        # Modify one to ensure they're independent
        config1.service_name = "modified"
        assert config1.service_name != config2.service_name