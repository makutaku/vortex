"""
Tests for CLI commands and functionality.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Import Click testing utilities conditionally  
try:
    from click.testing import CliRunner
    click_available = True
except ImportError:
    click_available = False

from vortex.config import ConfigManager
from vortex.shared.exceptions import ConfigurationError, MissingArgumentError


# Skip all CLI tests if Click is not available
pytestmark = pytest.mark.skipif(not click_available, reason="Click not available")


@pytest.fixture
def cli_runner():
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture  
def isolated_config(temp_dir):
    """Create isolated configuration for CLI tests."""
    config_dir = temp_dir / ".config" / "vortex"
    config_dir.mkdir(parents=True)
    return config_dir / "config.toml"


@pytest.mark.unit
class TestConfigCommand:
    """Test the config CLI command."""
    
    def test_config_show_command(self, cli_runner, isolated_config):
        """Test the config --show command."""
        from vortex.application.cli.commands.config import config
        
        with patch('vortex.cli.commands.config.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.config_file = isolated_config
            
            # Mock config object
            mock_config = Mock()
            mock_config.general.output_directory = Path("./data")
            mock_config.general.backup_enabled = False
            mock_config.general.log_level.value = "INFO"
            mock_config.providers.barchart.daily_limit = 150
            mock_config.providers.ibkr.host = "localhost"
            mock_config.providers.ibkr.port = 7497
            mock_manager.load_config.return_value = mock_config
            mock_manager.validate_provider_credentials.return_value = False
            
            # Create mock context
            ctx = Mock()
            ctx.obj = {'config_file': isolated_config}
            
            result = cli_runner.invoke(config, ['--show'], obj=ctx.obj)
            
            assert result.exit_code == 0
            assert "Vortex Configuration" in result.output
            assert "Provider Status" in result.output
    
    def test_config_set_credentials_barchart(self, cli_runner, isolated_config):
        """Test setting Barchart credentials."""
        from vortex.application.cli.commands.config import config
        
        with patch('vortex.cli.commands.config.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            with patch('vortex.cli.commands.config.Prompt') as mock_prompt:
                mock_prompt.ask.side_effect = ["test@example.com", "testpass", "100"]
                
                ctx = Mock()
                ctx.obj = {'config_file': isolated_config}
                
                result = cli_runner.invoke(
                    config, 
                    ['--provider', 'barchart', '--set-credentials'], 
                    obj=ctx.obj
                )
                
                assert result.exit_code == 0
                mock_manager.set_provider_config.assert_called_once_with(
                    "barchart", 
                    {
                        "username": "test@example.com",
                        "password": "testpass", 
                        "daily_limit": 100
                    }
                )
    
    def test_config_set_credentials_yahoo(self, cli_runner, isolated_config):
        """Test setting Yahoo credentials (should be automatic)."""
        from vortex.application.cli.commands.config import config
        
        with patch('vortex.cli.commands.config.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            ctx = Mock()
            ctx.obj = {'config_file': isolated_config}
            
            result = cli_runner.invoke(
                config,
                ['--provider', 'yahoo', '--set-credentials'],
                obj=ctx.obj
            )
            
            assert result.exit_code == 0
            assert "doesn't require credentials" in result.output
            mock_manager.set_provider_config.assert_called_once_with(
                "yahoo", 
                {"enabled": True}
            )
    
    def test_config_export_import(self, cli_runner, isolated_config, temp_dir):
        """Test config export and import."""
        from vortex.application.cli.commands.config import config
        
        export_file = temp_dir / "exported.toml"
        
        with patch('vortex.cli.commands.config.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            ctx = Mock()
            ctx.obj = {'config_file': isolated_config}
            
            # Test export
            result = cli_runner.invoke(
                config,
                ['--export', str(export_file)],
                obj=ctx.obj
            )
            
            assert result.exit_code == 0
            mock_manager.export_config.assert_called_once_with(export_file)
            
            # Test import
            result = cli_runner.invoke(
                config,
                ['--import', str(export_file)],
                obj=ctx.obj
            )
            
            assert result.exit_code == 0
            mock_manager.import_config.assert_called_once_with(export_file)
    
    def test_config_reset(self, cli_runner, isolated_config):
        """Test config reset."""
        from vortex.application.cli.commands.config import config
        
        with patch('vortex.cli.commands.config.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            with patch('vortex.cli.commands.config.Confirm') as mock_confirm:
                mock_confirm.ask.return_value = True
                
                ctx = Mock()
                ctx.obj = {'config_file': isolated_config}
                
                result = cli_runner.invoke(
                    config,
                    ['--reset'],
                    obj=ctx.obj
                )
                
                assert result.exit_code == 0
                mock_manager.reset_config.assert_called_once()
    
    def test_config_missing_provider_error(self, cli_runner, isolated_config):
        """Test error when provider is missing for set-credentials."""
        from vortex.application.cli.commands.config import config
        
        ctx = Mock()
        ctx.obj = {'config_file': isolated_config}
        
        result = cli_runner.invoke(
            config,
            ['--set-credentials'],
            obj=ctx.obj
        )
        
        assert result.exit_code != 0
        assert isinstance(result.exception, MissingArgumentError)


@pytest.mark.unit
class TestDownloadCommand:
    """Test the download CLI command."""
    
    def test_download_with_symbols(self, cli_runner, isolated_config, temp_dir):
        """Test download command with explicit symbols."""
        from vortex.application.cli.commands.download import download
        
        with patch('vortex.cli.commands.download.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Mock configuration
            mock_config = Mock()
            mock_config.general.output_directory = temp_dir
            mock_config.general.dry_run = True
            mock_config.general.random_sleep_max = 1
            mock_manager.load_config.return_value = mock_config
            
            with patch('vortex.cli.commands.download.create_downloader') as mock_create_downloader:
                mock_downloader = Mock()
                mock_create_downloader.return_value = mock_downloader
                
                with patch('vortex.cli.commands.download.Stock') as mock_stock:
                    mock_instrument = Mock()
                    mock_stock.return_value = mock_instrument
                    
                    ctx = Mock()
                    ctx.obj = {'config_file': isolated_config, 'dry_run': True}
                    
                    result = cli_runner.invoke(
                        download,
                        ['-p', 'yahoo', '-s', 'AAPL', '-s', 'GOOGL', '--yes'],
                        obj=ctx.obj
                    )
                    
                    assert result.exit_code == 0
                    assert "Download completed" in result.output
    
    def test_download_missing_provider(self, cli_runner, isolated_config):
        """Test download command with missing provider."""
        from vortex.application.cli.commands.download import download
        
        ctx = Mock()
        ctx.obj = {'config_file': isolated_config}
        
        result = cli_runner.invoke(
            download,
            ['-s', 'AAPL'],
            obj=ctx.obj
        )
        
        assert result.exit_code != 0
        assert "Missing option" in result.output
    
    def test_download_missing_symbols(self, cli_runner, isolated_config):
        """Test download command with no symbols or assets file."""
        from vortex.application.cli.commands.download import download
        
        with patch('vortex.cli.commands.download.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            with patch('vortex.cli.commands.download.get_default_assets_file') as mock_get_assets:
                mock_get_assets.side_effect = FileNotFoundError("No assets file")
                
                ctx = Mock()
                ctx.obj = {'config_file': isolated_config}
                
                result = cli_runner.invoke(
                    download,
                    ['-p', 'yahoo'],
                    obj=ctx.obj
                )
                
                assert result.exit_code != 0
                assert isinstance(result.exception, MissingArgumentError)
    
    def test_download_invalid_date_range(self, cli_runner, isolated_config):
        """Test download command with invalid date range.""" 
        from vortex.application.cli.commands.download import download
        
        ctx = Mock()
        ctx.obj = {'config_file': isolated_config}
        
        result = cli_runner.invoke(
            download,
            ['-p', 'yahoo', '-s', 'AAPL', '--start-date', '2024-12-01', '--end-date', '2024-01-01'],
            obj=ctx.obj
        )
        
        assert result.exit_code != 0
        # Should raise InvalidCommandError due to start > end date
    
    def test_download_with_assets_file(self, cli_runner, isolated_config, assets_file, temp_dir):
        """Test download command with assets file."""
        from vortex.application.cli.commands.download import download
        
        with patch('vortex.cli.commands.download.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            # Mock configuration
            mock_config = Mock()
            mock_config.general.output_directory = temp_dir
            mock_config.general.dry_run = True
            mock_config.general.random_sleep_max = 1
            mock_manager.load_config.return_value = mock_config
            
            with patch('vortex.cli.commands.download.create_downloader') as mock_create_downloader:
                mock_downloader = Mock()
                mock_create_downloader.return_value = mock_downloader
                
                with patch('vortex.cli.commands.download.Stock') as mock_stock:
                    mock_instrument = Mock()
                    mock_stock.return_value = mock_instrument
                    
                    ctx = Mock()
                    ctx.obj = {'config_file': isolated_config, 'dry_run': True}
                    
                    result = cli_runner.invoke(
                        download,
                        ['-p', 'yahoo', '--assets', str(assets_file), '--yes'],
                        obj=ctx.obj
                    )
                    
                    assert result.exit_code == 0
                    assert "Loaded" in result.output
                    assert "instruments from" in result.output


@pytest.mark.unit
class TestCLIIntegration:
    """Test CLI integration and error handling."""
    
    def test_cli_exception_handling(self, cli_runner, isolated_config):
        """Test that CLI properly handles and displays exceptions."""
        from vortex.application.cli.commands.config import config
        
        with patch('vortex.cli.commands.config.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            mock_manager.load_config.side_effect = ConfigurationError(
                "Test configuration error",
                "Test help message"
            )
            
            ctx = Mock()
            ctx.obj = {'config_file': isolated_config}
            
            result = cli_runner.invoke(config, ['--show'], obj=ctx.obj)
            
            assert result.exit_code != 0
            # The exception should be properly caught and displayed
    
    def test_cli_dry_run_mode(self, cli_runner, isolated_config):
        """Test that CLI respects dry run mode."""
        from vortex.application.cli.commands.download import download
        
        with patch('vortex.cli.commands.download.ConfigManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            
            ctx = Mock()
            ctx.obj = {'config_file': isolated_config, 'dry_run': True}
            
            result = cli_runner.invoke(
                download,
                ['-p', 'yahoo', '-s', 'AAPL', '--yes'],
                obj=ctx.obj
            )
            
            # Should complete successfully in dry run mode
            assert "DRY RUN" in result.output


@pytest.mark.integration
class TestCLIEndToEnd:
    """End-to-end CLI tests."""
    
    @pytest.mark.slow
    def test_full_config_workflow(self, cli_runner, temp_dir):
        """Test complete configuration workflow."""
        from vortex.application.cli.commands.config import config
        
        config_file = temp_dir / "test_config.toml"
        
        # Set up real ConfigManager
        with patch.dict(os.environ, clear=True):
            ctx = {'config_file': config_file}
            
            # Show initial config (should be defaults)
            result = cli_runner.invoke(config, ['--show'], obj=ctx)
            assert result.exit_code == 0
            
            # Export config
            export_file = temp_dir / "exported.toml"
            result = cli_runner.invoke(config, ['--export', str(export_file)], obj=ctx)
            assert result.exit_code == 0
            assert export_file.exists()
            
            # Reset config
            with patch('vortex.cli.commands.config.Confirm.ask', return_value=True):
                result = cli_runner.invoke(config, ['--reset'], obj=ctx)
                assert result.exit_code == 0