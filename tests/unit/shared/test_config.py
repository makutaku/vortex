"""
Unit tests for the Vortex configuration system.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from vortex.config import (
    ConfigManager, VortexConfig, VortexSettings,
    BarchartConfig, YahooConfig, IBKRConfig,
    GeneralConfig, ProvidersConfig, DateRangeConfig,
    LogLevel, Provider
)
from vortex.shared.exceptions import (
    ConfigurationError, InvalidConfigurationError, 
    ConfigurationValidationError
)


@pytest.mark.unit
class TestVortexConfig:
    """Test the main VortexConfig model."""
    
    def test_default_config(self):
        """Test that default configuration is valid."""
        config = VortexConfig()
        
        assert config.general.output_directory == Path("./data")
        assert config.general.log_level == LogLevel.INFO
        assert config.general.backup_enabled is False
        assert config.providers.barchart.daily_limit == 150
        assert config.providers.yahoo.enabled is True
        assert config.providers.ibkr.host == "localhost"
        assert config.providers.ibkr.port == 7497
    
    def test_config_with_data(self, sample_config_data):
        """Test configuration with sample data."""
        config = VortexConfig(**sample_config_data)
        
        assert str(config.general.output_directory) == "./test_data"
        assert config.general.log_level == LogLevel.DEBUG
        assert config.providers.barchart.username == "test@example.com"
        assert config.providers.barchart.daily_limit == 100
        assert config.providers.ibkr.timeout == 30
    
    def test_config_validation_errors(self):
        """Test configuration validation catches errors."""
        # Invalid log level
        with pytest.raises(ValueError):
            VortexConfig(general={"log_level": "INVALID"})
        
        # Invalid daily limit
        with pytest.raises(ValueError):
            VortexConfig(providers={"barchart": {"daily_limit": -1}})
        
        # Invalid port range
        with pytest.raises(ValueError):
            VortexConfig(providers={"ibkr": {"port": 99999}})
    
    def test_path_expansion(self):
        """Test that paths are properly expanded."""
        config = VortexConfig(general={"output_directory": "~/test_data"})
        assert config.general.output_directory.is_absolute()
        assert str(config.general.output_directory).startswith("/")


@pytest.mark.unit 
class TestBarchartConfig:
    """Test Barchart provider configuration."""
    
    def test_valid_config(self):
        """Test valid Barchart configuration."""
        config = BarchartConfig(
            username="test@example.com",
            password="password123",
            daily_limit=200
        )
        
        assert config.username == "test@example.com"
        assert config.password == "password123"
        assert config.daily_limit == 200
    
    def test_credentials_validation(self):
        """Test credential validation logic."""
        # Both username and password required together
        with pytest.raises(ValueError, match="Both username and password"):
            BarchartConfig(username="test@example.com")
        
        with pytest.raises(ValueError, match="Both username and password"):
            BarchartConfig(password="password123")
        
        # Empty strings should be treated as None
        config = BarchartConfig(username="", password="")
        assert config.username is None
        assert config.password is None
    
    def test_daily_limit_bounds(self):
        """Test daily limit validation."""
        # Valid range
        config = BarchartConfig(daily_limit=1)
        assert config.daily_limit == 1
        
        config = BarchartConfig(daily_limit=1000)
        assert config.daily_limit == 1000
        
        # Invalid bounds
        with pytest.raises(ValueError):
            BarchartConfig(daily_limit=0)
        
        with pytest.raises(ValueError):
            BarchartConfig(daily_limit=1001)


@pytest.mark.unit
class TestConfigManager:
    """Test the ConfigManager class."""
    
    def test_default_config_path(self):
        """Test default configuration path creation."""
        manager = ConfigManager()
        
        expected_path = Path.home() / ".config" / "vortex" / "config.toml"
        assert manager.config_file == expected_path
        assert manager.config_directory == expected_path.parent
    
    def test_custom_config_path(self, temp_dir):
        """Test custom configuration path."""
        custom_path = temp_dir / "custom_config.toml"
        manager = ConfigManager(custom_path)
        
        assert manager.config_file == custom_path
    
    def test_load_default_config(self, config_manager):
        """Test loading default configuration when no file exists."""
        config = config_manager.load_config()
        
        assert isinstance(config, VortexConfig)
        assert config.general.log_level == LogLevel.INFO
        assert config.providers.barchart.daily_limit == 150
    
    def test_save_and_load_config(self, config_manager, vortex_config):
        """Test saving and loading configuration."""
        # Save config
        config_manager.save_config(vortex_config)
        assert config_manager.config_file.exists()
        
        # Create new manager and load
        new_manager = ConfigManager(config_manager.config_file)
        loaded_config = new_manager.load_config()
        
        assert loaded_config.general.log_level == LogLevel.DEBUG
        assert loaded_config.providers.barchart.username == "test@example.com"
        assert loaded_config.providers.barchart.daily_limit == 100
    
    def test_provider_config_methods(self, config_manager, vortex_config):
        """Test provider-specific configuration methods."""
        config_manager._config = vortex_config
        
        # Get provider config
        barchart_config = config_manager.get_provider_config("barchart")
        assert barchart_config["username"] == "test@example.com"
        assert barchart_config["daily_limit"] == 100
        
        yahoo_config = config_manager.get_provider_config("yahoo")
        assert yahoo_config["enabled"] is True
        
        ibkr_config = config_manager.get_provider_config("ibkr")
        assert ibkr_config["host"] == "localhost"
        assert ibkr_config["port"] == 7497
        
        # Invalid provider
        with pytest.raises(InvalidConfigurationError):
            config_manager.get_provider_config("invalid")
    
    def test_set_provider_config(self, config_manager):
        """Test setting provider configuration."""
        # Set Barchart config
        config_manager.set_provider_config("barchart", {
            "username": "new@example.com",
            "password": "newpass",
            "daily_limit": 300
        })
        
        config = config_manager.load_config()
        assert config.providers.barchart.username == "new@example.com"
        assert config.providers.barchart.daily_limit == 300
        
        # Set IBKR config
        config_manager.set_provider_config("ibkr", {
            "host": "remote.server.com",
            "port": 4001,
            "client_id": 5,
            "timeout": 60
        })
        
        config = config_manager.load_config()
        assert config.providers.ibkr.host == "remote.server.com"
        assert config.providers.ibkr.port == 4001
        assert config.providers.ibkr.client_id == 5
        assert config.providers.ibkr.timeout == 60
    
    def test_validate_provider_credentials(self, config_manager, vortex_config):
        """Test provider credential validation."""
        config_manager._config = vortex_config
        
        # Barchart has credentials
        assert config_manager.validate_provider_credentials("barchart") is True
        
        # Yahoo doesn't need credentials
        assert config_manager.validate_provider_credentials("yahoo") is True
        
        # IBKR doesn't need credentials (connection details sufficient)
        assert config_manager.validate_provider_credentials("ibkr") is True
        
        # Test missing credentials
        config_manager.set_provider_config("barchart", {"username": None, "password": None})
        assert config_manager.validate_provider_credentials("barchart") is False
    
    def test_get_missing_credentials(self, config_manager):
        """Test getting missing credential fields."""
        # No credentials set
        missing = config_manager.get_missing_credentials("barchart")
        assert "username" in missing
        assert "password" in missing
        
        # Only username set
        config_manager.set_provider_config("barchart", {"username": "test@example.com"})
        missing = config_manager.get_missing_credentials("barchart")
        assert "username" not in missing
        assert "password" in missing
        
        # Yahoo has no required credentials
        missing = config_manager.get_missing_credentials("yahoo")
        assert len(missing) == 0
    
    def test_import_export_config(self, config_manager, vortex_config, temp_dir):
        """Test configuration import and export."""
        export_file = temp_dir / "exported_config.toml"
        
        # Set up config and export
        config_manager._config = vortex_config
        config_manager.export_config(export_file)
        assert export_file.exists()
        
        # Import to new manager
        new_manager = ConfigManager(temp_dir / "new_config.toml")
        new_manager.import_config(export_file)
        
        imported_config = new_manager.load_config()
        assert imported_config.general.log_level == LogLevel.DEBUG
        assert imported_config.providers.barchart.username == "test@example.com"
    
    def test_reset_config(self, config_manager, vortex_config):
        """Test configuration reset."""
        # Set custom config
        config_manager._config = vortex_config
        config_manager.save_config()
        
        # Reset to defaults
        config_manager.reset_config()
        
        # Verify defaults
        config = config_manager.load_config()
        assert config.general.log_level == LogLevel.INFO
        assert config.providers.barchart.username is None
        assert config.providers.barchart.daily_limit == 150


@pytest.mark.unit
class TestEnvironmentVariables:
    """Test environment variable handling."""
    
    def test_modern_environment_variables(self, config_manager, clean_environment):
        """Test modern VORTEX_* environment variables."""
        with patch.dict(os.environ, {
            "VORTEX_OUTPUT_DIR": "/custom/output",
            "VORTEX_LOG_LEVEL": "ERROR",
            "VORTEX_BACKUP_ENABLED": "true",
            "VORTEX_DRY_RUN": "true",
            "VORTEX_BARCHART_USERNAME": "env@example.com",
            "VORTEX_BARCHART_PASSWORD": "envpass",
            "VORTEX_BARCHART_DAILY_LIMIT": "250",
            "VORTEX_IBKR_HOST": "envhost",
            "VORTEX_IBKR_PORT": "4001",
            "VORTEX_IBKR_CLIENT_ID": "10"
        }):
            config = config_manager.load_config()
            
            assert str(config.general.output_directory) == "/custom/output"
            assert config.general.log_level == LogLevel.ERROR
            assert config.general.backup_enabled is True
            assert config.general.dry_run is True
            assert config.providers.barchart.username == "env@example.com"
            assert config.providers.barchart.password == "envpass"
            assert config.providers.barchart.daily_limit == 250
            assert config.providers.ibkr.host == "envhost"
            assert config.providers.ibkr.port == 4001
            assert config.providers.ibkr.client_id == 10
    
    def test_default_provider_configuration(self, config_manager, clean_environment):
        """Test default provider configuration."""
        with patch.dict(os.environ, {
            "VORTEX_DEFAULT_PROVIDER": "barchart"
        }):
            config = config_manager.load_config()
            
            # Should use configured default provider
            assert config.general.default_provider.value == "barchart"
        
        # Test default when no environment variable is set
        config = config_manager.load_config()
        assert config.general.default_provider.value == "yahoo"  # Default is yahoo


@pytest.mark.unit
class TestConfigurationErrors:
    """Test configuration error handling."""
    
    def test_invalid_toml_file(self, config_manager, temp_dir):
        """Test handling of invalid TOML file."""
        # Create invalid TOML file
        config_file = temp_dir / "invalid.toml"
        config_file.write_text("invalid toml content [[[")
        
        manager = ConfigManager(config_file)
        with pytest.raises(InvalidConfigurationError):
            manager.load_config()
    
    def test_permission_errors(self, config_manager, temp_dir):
        """Test handling of permission errors."""
        # Create read-only directory (on systems that support it)
        if hasattr(os, 'chmod'):
            read_only_dir = temp_dir / "readonly"
            read_only_dir.mkdir()
            os.chmod(read_only_dir, 0o444)
            
            config_file = read_only_dir / "config.toml"
            manager = ConfigManager(config_file)
            
            with pytest.raises(ConfigurationError):
                manager.save_config()
    
    def test_validation_errors(self, config_manager):
        """Test configuration validation errors."""
        with pytest.raises(ConfigurationValidationError):
            config_manager.set_provider_config("barchart", {
                "username": "valid@example.com",
                "daily_limit": -999  # Invalid value
            })


@pytest.mark.unit
class TestDateRangeConfig:
    """Test date range configuration validation."""
    
    def test_valid_date_range(self):
        """Test valid date range configuration."""
        config = DateRangeConfig(start_year=2020, end_year=2025)
        assert config.start_year == 2020
        assert config.end_year == 2025
    
    def test_invalid_date_range(self):
        """Test invalid date range validation."""
        with pytest.raises(ValueError, match="start_year.*must be less than"):
            DateRangeConfig(start_year=2025, end_year=2020)