"""
Integration tests for the Vortex configuration system.

These tests involve file I/O, environment variables, and system integration.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vortex.core.config import (
    ConfigManager, VortexConfig, 
    BarchartConfig, YahooConfig, IBKRConfig,
    GeneralConfig, ProvidersConfig, DateRangeConfig,
    LogLevel,
    ConfigurationError, ConfigurationValidationError
)


@pytest.mark.integration
class TestConfigManagerIntegration:
    """Integration tests for ConfigManager involving file operations."""
    
    def test_save_and_load_config(self, config_manager, vortex_config, clean_environment):
        """Test saving and loading configuration to/from files."""
        # Save config
        config_manager.save_config(vortex_config)
        assert config_manager.config_file.exists()
        
        # Create new manager and load
        new_manager = ConfigManager(config_manager.config_file)
        loaded_config = new_manager.load_config()
        
        assert loaded_config.general.logging.level == LogLevel.DEBUG
        assert loaded_config.providers.barchart.username == "test@example.com"
        assert loaded_config.providers.barchart.daily_limit == 100

    def test_set_provider_config(self, config_manager):
        """Test setting provider configuration with file persistence."""
        # Set barchart config
        config_manager.set_provider_config("barchart", {
            "username": "new_user@example.com",
            "password": "new_password",
            "daily_limit": 200
        })
        
        # Verify it's saved
        config = config_manager.load_config()
        assert config.providers.barchart.username == "new_user@example.com"
        assert config.providers.barchart.daily_limit == 200

    def test_validate_provider_credentials(self, config_manager, vortex_config):
        """Test provider credential validation."""
        config_manager._config = vortex_config
        
        # Valid credentials should pass
        assert config_manager.validate_provider_credentials("barchart") is True
        
        # IBKR with connection details should pass (IBKR only needs connection details)
        assert config_manager.validate_provider_credentials("ibkr") is True
        
        # Yahoo should always pass (no credentials required)
        assert config_manager.validate_provider_credentials("yahoo") is True

    def test_get_missing_credentials(self, temp_dir, clean_environment):
        """Test getting missing credential information."""
        # Create a config manager with no existing config (defaults only)
        empty_config_file = temp_dir / "empty_config.toml"
        config_manager = ConfigManager(empty_config_file)
        missing = config_manager.get_missing_credentials("barchart")
        
        assert "username" in missing
        assert "password" in missing

    def test_import_export_config(self, config_manager, vortex_config, temp_dir):
        """Test configuration import and export."""
        export_file = temp_dir / "exported_config.toml"
        
        # Set up config and export
        config_manager._config = vortex_config
        config_manager.export_config(export_file)
        assert export_file.exists()
        
        # Create new manager and import
        new_manager = ConfigManager()
        imported_config = new_manager.import_config(export_file)
        
        assert imported_config.providers.barchart.username == "test@example.com"

    def test_reset_config(self, config_manager, vortex_config):
        """Test configuration reset."""
        # Set custom config
        config_manager._config = vortex_config
        config_manager.save_config()
        
        # Reset to defaults
        config_manager.reset_config()
        
        # Should be back to defaults
        default_config = config_manager.load_config()
        assert default_config.general.logging.level == LogLevel.INFO
        assert default_config.providers.barchart.username is None


@pytest.mark.integration
class TestEnvironmentVariablesIntegration:
    """Integration tests for environment variable handling."""
    
    def test_modern_environment_variables(self, config_manager, clean_environment):
        """Test modern environment variable configuration."""
        os.environ["VORTEX_OUTPUT_DIR"] = "/custom/path"
        os.environ["VORTEX_LOGGING_LEVEL"] = "DEBUG"
        os.environ["VORTEX_BARCHART_USERNAME"] = "env_user@example.com"
        os.environ["VORTEX_BARCHART_PASSWORD"] = "env_password"
        
        config = config_manager.load_config()
        
        assert str(config.general.output_directory).endswith("custom/path")
        assert config.general.logging.level == LogLevel.DEBUG
        assert config.providers.barchart.username == "env_user@example.com"
        assert config.providers.barchart.password == "env_password"

    def test_default_provider_configuration(self, config_manager, clean_environment):
        """Test default provider configuration from environment."""
        os.environ["VORTEX_DEFAULT_PROVIDER"] = "barchart"
        
        config = config_manager.load_config()
        assert config.general.default_provider.value == "barchart"


@pytest.mark.integration 
class TestConfigurationErrorsIntegration:
    """Integration tests for configuration error handling."""
    
    def test_permission_errors(self, config_manager, temp_dir):
        """Test handling of file permission errors."""
        # Create a config file and make it readonly
        readonly_config = temp_dir / "readonly_config.toml"
        readonly_config.write_text("")  # Create the file
        readonly_config.chmod(0o444)  # Make it readonly
        
        # Try to write to readonly config
        manager = ConfigManager(readonly_config)
        
        with pytest.raises(ConfigurationError):
            manager.save_config()

    def test_validation_errors(self, config_manager):
        """Test configuration validation error handling."""
        # Try to set invalid provider config
        with pytest.raises(ConfigurationValidationError):
            config_manager.set_provider_config("invalid_provider", {})