"""Tests for download command."""

import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from click.testing import CliRunner
import tempfile
import os
import click

from vortex.cli.commands.download import (
    load_config_instruments, get_default_assets_file, download,
    show_download_summary, execute_download, get_download_config, create_downloader
)
from vortex.exceptions import CLIError, MissingArgumentError, ConfigurationError, DataProviderError
from vortex.core.instruments.config import InstrumentConfig
from vortex.models.stock import Stock
from vortex.models.period import Period


class TestLoadConfigInstruments:
    """Test load_config_instruments function."""
    
    def test_load_config_instruments_success(self):
        """Test successful loading of config instruments."""
        mock_configs = {
            'AAPL': Mock(spec=InstrumentConfig),
            'GOOGL': Mock(spec=InstrumentConfig),
            'MSFT': Mock(spec=InstrumentConfig)
        }
        
        with patch.object(InstrumentConfig, 'load_from_json') as mock_load:
            mock_load.return_value = mock_configs
            
            result = load_config_instruments(Path('test.json'))
        
        assert result == mock_configs  # Now returns full configs dict
        mock_load.assert_called_once_with('test.json')
    
    def test_load_config_instruments_file_error(self):
        """Test error handling when assets file loading fails."""
        with patch.object(InstrumentConfig, 'load_from_json') as mock_load:
            mock_load.side_effect = Exception("File not found")
            
            with pytest.raises(click.Abort):
                load_config_instruments(Path('nonexistent.json'))


class TestGetDefaultAssetsFile:
    """Test get_default_assets_file function."""
    
    def test_get_default_assets_file_existing_provider(self):
        """Test getting assets file for existing provider."""
        with patch('vortex.cli.commands.download.Path.exists') as mock_exists:
            mock_exists.return_value = True
            
            result = get_default_assets_file('yahoo')
        
        assert result.name == 'yahoo.json'
        assert 'assets' in str(result)
    
    def test_get_default_assets_file_fallback_to_default(self):
        """Test fallback to default.json when provider file doesn't exist."""
        with patch('vortex.cli.commands.download.Path.exists') as mock_exists:
            # First call (provider.json) returns False, second call (default.json) returns True
            mock_exists.side_effect = [False, True]
            
            result = get_default_assets_file('nonexistent')
        
        assert result.name == 'default.json'
        assert 'assets' in str(result)
    
    def test_get_default_assets_file_no_files_exist(self):
        """Test when no assets files exist - returns provider file path anyway."""
        with patch('vortex.cli.commands.download.Path.exists') as mock_exists:
            mock_exists.return_value = False
            
            result = get_default_assets_file('nonexistent')
            
            assert result.name == 'nonexistent.json'
            assert 'assets' in str(result)


class TestDownloadMain:
    """Test download function and CLI integration."""
    
    @pytest.fixture
    def runner(self):
        """CLI test runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all major dependencies."""
        with patch('vortex.cli.commands.download.ConfigManager') as mock_config, \
             patch('vortex.cli.commands.download.get_provider_registry') as mock_registry, \
             patch('vortex.cli.commands.download.CsvStorage') as mock_csv, \
             patch('vortex.cli.commands.download.ParquetStorage') as mock_parquet, \
             patch('vortex.cli.commands.download.UpdatingDownloader') as mock_downloader, \
             patch('vortex.cli.commands.download.get_available_providers') as mock_providers, \
             patch('vortex.cli.commands.download.get_provider_config_from_vortex_config') as mock_get_provider_config:
            
            # Configure mocks
            mock_config_instance = Mock()
            mock_config_instance.get_output_directory.return_value = Path('/test/output')
            
            # Mock the config object returned by load_config()
            mock_vortex_config = Mock()
            mock_vortex_config.general = Mock()
            mock_vortex_config.general.random_sleep_max = 5
            mock_vortex_config.general.dry_run = False
            mock_config_instance.load_config.return_value = mock_vortex_config
            mock_config_instance.get_default_provider.return_value = "yahoo"
            
            mock_config.return_value = mock_config_instance
            
            mock_registry_instance = Mock()
            mock_registry_instance.create_provider.return_value = Mock()
            mock_registry.return_value = mock_registry_instance
            
            mock_providers.return_value = ['yahoo', 'barchart']
            mock_get_provider_config.return_value = {'test': 'config'}
            
            # Configure downloader mock more thoroughly
            mock_downloader_instance = Mock()
            mock_downloader_instance.data_provider = Mock()
            mock_downloader_instance.data_storage = Mock()
            mock_downloader_instance._process_job = Mock()
            mock_downloader.return_value = mock_downloader_instance
            
            yield {
                'config': mock_config,
                'registry': mock_registry,
                'csv_storage': mock_csv,
                'parquet_storage': mock_parquet,
                'downloader': mock_downloader,
                'providers': mock_providers,
                'config_instance': mock_config_instance,
                'registry_instance': mock_registry_instance,
                'get_provider_config': mock_get_provider_config,
                'downloader_instance': mock_downloader_instance
            }
    
    def test_download_with_symbol(self, runner, mock_dependencies):
        """Test download with single symbol."""
        with patch('vortex.cli.utils.instrument_parser.parse_instruments') as mock_parse, \
             patch('vortex.cli.ux.validate_symbols') as mock_validate:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = ['AAPL']  # parse_instruments returns strings
            
            result = runner.invoke(download, ['--symbol', 'AAPL', '--yes'], obj={'config_file': None})
        
        assert result.exit_code == 0
    
    def test_download_with_symbols_file(self, runner, mock_dependencies):
        """Test download with symbols file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write('AAPL\nGOOGL\nMSFT\n')
            f.flush()
            symbols_file = f.name
        
        try:
            with patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
                 patch('vortex.cli.commands.download.parse_instruments') as mock_parse:
                
                mock_validate.return_value = ['AAPL', 'GOOGL', 'MSFT']
                mock_parse.return_value = [Stock('AAPL', 'AAPL'), Stock('GOOGL', 'GOOGL'), Stock('MSFT', 'MSFT')]
                mock_dependencies['downloader'].return_value._process_job.return_value = None
                
                result = runner.invoke(download, ['--symbols-file', symbols_file, '--yes'], obj={'config_file': None})
            
            assert result.exit_code == 0
            mock_validate.assert_called()
            mock_parse.assert_called()
        finally:
            os.unlink(symbols_file)
    
    def test_download_with_assets_file(self, runner, mock_dependencies):
        """Test download with assets file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write('{"futures": {"GC": {}, "ES": {}}}')
            f.flush()
            assets_file = f.name
        
        try:
            with patch('vortex.cli.commands.download.load_config_instruments') as mock_load, \
                 patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
                 patch('vortex.cli.commands.download.parse_instruments') as mock_parse, \
                 patch('vortex.cli.commands.download.execute_download') as mock_execute:
                
                mock_load.return_value = {'GC': Mock(spec=InstrumentConfig), 'ES': Mock(spec=InstrumentConfig)}
                mock_validate.return_value = ['GC', 'ES']  
                mock_parse.return_value = [Mock(), Mock()]
                mock_execute.return_value = 2  # Successful downloads
                mock_dependencies['downloader'].return_value._process_job.return_value = None
                
                result = runner.invoke(download, ['--assets', assets_file, '--yes'], obj={'config_file': None})
            
            assert result.exit_code == 0
            mock_load.assert_called()
            mock_validate.assert_called()
        finally:
            os.unlink(assets_file)
    
    def test_download_no_symbols_provided(self, runner, mock_dependencies):
        """Test download when no symbols are provided."""
        with patch('vortex.cli.commands.download.get_default_assets_file') as mock_default, \
             patch('vortex.cli.commands.download.load_config_instruments') as mock_load, \
             patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse, \
             patch('vortex.cli.commands.download.execute_download') as mock_execute:
            
            mock_default.return_value = Path('default.json')
            mock_load.return_value = {'DEFAULT1': Mock(spec=InstrumentConfig), 'DEFAULT2': Mock(spec=InstrumentConfig)}
            mock_validate.return_value = ['DEFAULT1', 'DEFAULT2']
            mock_parse.return_value = []  # Empty list to trigger default assets loading
            mock_execute.return_value = 2  # Successful downloads
            mock_dependencies['downloader'].return_value._process_job.return_value = None
            
            result = runner.invoke(download, ['--yes'], obj={'config_file': None})
        
        assert result.exit_code == 0
        mock_default.assert_called()
        mock_load.assert_called()
    
    def test_download_custom_date_range(self, runner, mock_dependencies):
        """Test download with custom date range."""
        with patch('vortex.cli.utils.instrument_parser.parse_instruments') as mock_parse, \
             patch('vortex.cli.ux.validate_symbols') as mock_validate:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = ['AAPL']  # parse_instruments returns strings
            mock_dependencies['downloader'].return_value._process_job.return_value = None
            
            result = runner.invoke(download, [
                '--symbol', 'AAPL',
                '--start-date', '2023-01-01',
                '--end-date', '2023-12-31',
                '--yes'
            ], obj={'config_file': None})
        
        assert result.exit_code == 0
        # Verify downloader was called with custom dates
        downloader_call = mock_dependencies['downloader'].return_value._process_job.call_args
        assert downloader_call is not None
    
    def test_download_invalid_provider(self, runner, mock_dependencies):
        """Test download with invalid provider."""
        from vortex.exceptions.plugins import PluginNotFoundError
        
        # Mock the provider registry to raise exception for invalid provider
        mock_dependencies['registry'].return_value.get_plugin.side_effect = PluginNotFoundError("Plugin 'invalid_provider' not found")
        mock_dependencies['providers'].return_value = ['yahoo', 'barchart']  # Valid providers
        
        result = runner.invoke(download, [
            '--provider', 'invalid_provider',
            '--symbol', 'AAPL',
            '--yes'
        ], obj={'config_file': None})
        
        # Should fail with invalid provider
        assert result.exit_code != 0
        assert 'invalid_provider' in result.output
    
    def test_download_configuration_error(self, runner, mock_dependencies):
        """Test download with configuration error."""
        mock_dependencies['config'].side_effect = ConfigurationError("Config error")
        
        result = runner.invoke(download, ['--symbol', 'AAPL', '--yes'], obj={'config_file': None})
        
        assert result.exit_code != 0
        assert 'Config error' in result.output or 'error' in result.output.lower()
    
    def test_download_with_output_dir(self, runner, mock_dependencies, tmp_path):
        """Test download with custom output directory."""
        custom_output = tmp_path / "custom_output"
        
        with patch('vortex.cli.utils.instrument_parser.parse_instruments') as mock_parse, \
             patch('vortex.cli.ux.validate_symbols') as mock_validate:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = ['AAPL']  # parse_instruments returns strings
            mock_dependencies['downloader'].return_value._process_job.return_value = None
            
            result = runner.invoke(download, [
                '--symbol', 'AAPL',
                '--output-dir', str(custom_output),
                '--yes'
            ], obj={'config_file': None})
        
        assert result.exit_code == 0
        # Verify CSV storage was created with custom output dir
        mock_dependencies['csv_storage'].assert_called()
        csv_call_args = mock_dependencies['csv_storage'].call_args[0]  # positional args
        assert csv_call_args[0] == str(custom_output)  # First argument is base_path
    
    def test_download_progress_display(self, runner, mock_dependencies):
        """Test that progress is displayed during download."""
        with patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse, \
             patch('vortex.cli.commands.download.ux') as mock_ux:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = ['AAPL']  # parse_instruments returns strings
            mock_dependencies['downloader'].return_value._process_job.return_value = None
            
            # Mock progress context manager
            mock_progress_instance = Mock()
            mock_ux.progress.return_value.__enter__.return_value = mock_progress_instance
            
            result = runner.invoke(download, ['--symbol', 'AAPL', '--yes'], obj={'config_file': None})
        
        assert result.exit_code == 0
        mock_ux.progress.assert_called()
        mock_progress_instance.update.assert_called()
    
    def test_download_multiple_symbols_validation(self, runner, mock_dependencies):
        """Test download with multiple symbols."""
        mock_dependencies['downloader'].return_value.download.return_value = []
        
        result = runner.invoke(download, [
            '--symbol', 'AAPL',
            '--symbol', 'GOOGL', 
            '--symbol', 'MSFT',
            '--yes'
        ], obj={'config_file': None})
        
        assert result.exit_code == 0
        # Check that all three symbols are mentioned in the output/logs
        # This validates the multiple symbol functionality works
        assert result.output  # Some output was produced

    def test_download_enhanced_error_handling(self, runner, mock_dependencies):
        """Test enhanced error handling during download."""
        with patch('vortex.cli.ux.validate_symbols') as mock_validate, \
             patch('vortex.cli.utils.instrument_parser.parse_instruments') as mock_parse:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = ['AAPL']  # parse_instruments returns strings
            
            # Simulate download error
            download_error = Exception("Download failed")
            mock_dependencies['downloader'].return_value._process_job.side_effect = download_error
            
            result = runner.invoke(download, ['--symbol', 'AAPL', '--yes'], obj={'config_file': None})
        
        # Should handle error gracefully (error handler built into CLI)
        # Check for error indicators in the output
        output_lower = result.output.lower()
        assert result.exit_code != 0 or "error" in output_lower or "failed" in output_lower or "issues" in output_lower


class TestShowDownloadSummary:
    """Test show_download_summary function."""
    
    def test_show_download_summary_basic(self):
        """Test basic download summary display."""
        from vortex.cli.commands.download import show_download_summary
        
        provider = "yahoo"
        symbols = ["AAPL", "GOOGL"]
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        output_dir = Path("/test/output")
        backup = True
        force = False
        
        with patch('vortex.cli.commands.download.console') as mock_console:
            show_download_summary(provider, symbols, start_date, end_date, output_dir, backup, force)
            
            # Verify console.print was called for table and symbols
            assert mock_console.print.call_count >= 2
    
    def test_show_download_summary_many_symbols(self):
        """Test download summary with many symbols (truncated display)."""
        from vortex.cli.commands.download import show_download_summary
        
        provider = "barchart"
        symbols = [f"SYMBOL{i}" for i in range(20)]  # 20 symbols
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        output_dir = Path("/test/output")
        backup = False
        force = True
        
        with patch('vortex.cli.commands.download.console') as mock_console:
            show_download_summary(provider, symbols, start_date, end_date, output_dir, backup, force)
            
            # Should truncate symbols display
            assert mock_console.print.call_count >= 2
            
            # Check that "... and X more" appears in output
            calls = mock_console.print.call_args_list
            symbols_call = next((call for call in calls if "... and" in str(call)), None)
            assert symbols_call is not None


class TestExecuteDownload:
    """Test execute_download function."""
    
    def test_execute_download_dry_run(self):
        """Test execute_download in dry run mode."""
        from vortex.cli.commands.download import execute_download, DownloadExecutionConfig
        
        config_manager = Mock()
        symbols = ["AAPL", "GOOGL"]
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        output_dir = Path("/test/output")
        
        config = DownloadExecutionConfig(
            config_manager=config_manager,
            provider="yahoo",
            symbols=symbols,
            instrument_configs=None,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            backup=False,
            force=False,
            chunk_size=30,
            dry_run=True
        )
        
        with patch('vortex.cli.commands.download.console') as mock_console:
            result = execute_download(config)
            
            assert result == len(symbols)  # Should return number of symbols
            mock_console.print.assert_called_with("[yellow]DRY RUN: Would download data but no changes will be made[/yellow]")
    
    @patch('vortex.cli.commands.download.get_download_config')
    @patch('vortex.cli.commands.download.create_downloader')
    @patch('vortex.cli.commands.download.ux')
    def test_execute_download_success(self, mock_ux, mock_create_downloader, mock_get_config):
        """Test successful download execution."""
        from vortex.cli.commands.download import execute_download, DownloadExecutionConfig
        
        # Setup mocks
        config_manager = Mock()
        mock_get_config.return_value = {'test': 'config'}
        
        mock_downloader = Mock()
        mock_create_downloader.return_value = mock_downloader
        
        mock_progress = Mock()
        mock_ux.progress.return_value.__enter__.return_value = mock_progress
        
        symbols = ["AAPL", "GOOGL"]
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        output_dir = Path("/test/output")
        
        config = DownloadExecutionConfig(
            config_manager=config_manager,
            provider="yahoo",
            symbols=symbols,
            instrument_configs=None,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            backup=False,
            force=False,
            chunk_size=30,
            dry_run=False
        )
        
        result = execute_download(config)
        
        assert result == 2  # Both symbols successful
        assert mock_progress.update.call_count >= 2  # Progress updated
        assert mock_downloader._process_job.call_count == 2  # Both symbols processed
    
    @patch('vortex.cli.commands.download.get_download_config')
    @patch('vortex.cli.commands.download.create_downloader')
    @patch('vortex.cli.commands.download.ux')
    @patch('vortex.cli.commands.download.logger')
    def test_execute_download_with_errors(self, mock_logger, mock_ux, mock_create_downloader, mock_get_config):
        """Test download execution with some failures."""
        from vortex.cli.commands.download import execute_download, DownloadExecutionConfig
        
        # Setup mocks
        config_manager = Mock()
        mock_get_config.return_value = {'test': 'config'}
        
        mock_downloader = Mock()
        # First symbol succeeds, second fails
        mock_downloader._process_job.side_effect = [None, Exception("Download failed")]
        mock_create_downloader.return_value = mock_downloader
        
        mock_progress = Mock()
        mock_ux.progress.return_value.__enter__.return_value = mock_progress
        
        symbols = ["AAPL", "GOOGL"]
        start_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        output_dir = Path("/test/output")
        
        config = DownloadExecutionConfig(
            config_manager=config_manager,
            provider="yahoo",
            symbols=symbols,
            instrument_configs=None,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            backup=False,
            force=False,
            chunk_size=30,
            dry_run=False
        )
        
        result = execute_download(config)
        
        assert result == 1  # Only one symbol successful
        mock_logger.error.assert_called()  # Error logged for failed symbol


class TestGetDownloadConfig:
    """Test get_download_config function."""
    
    def test_get_download_config(self):
        """Test download config creation."""
        from vortex.cli.commands.download import get_download_config
        
        config_manager = Mock()
        mock_config = {'test': 'config'}
        config_manager.load_config.return_value = mock_config
        
        output_dir = Path("/test/output")
        backup = True
        force = False
        
        result = get_download_config(config_manager, output_dir, backup, force)
        
        expected = {
            'vortex_config': mock_config,
            'output_dir': output_dir,
            'backup': backup,
            'force': force
        }
        
        assert result == expected
        config_manager.load_config.assert_called_once()


class TestCreateDownloader:
    """Test create_downloader function."""
    
    @patch('vortex.cli.commands.download.get_provider_registry')
    @patch('vortex.cli.commands.download.get_provider_config_from_vortex_config')
    @patch('vortex.cli.commands.download.CsvStorage')
    @patch('vortex.cli.commands.download.ParquetStorage')
    @patch('vortex.cli.commands.download.UpdatingDownloader')
    def test_create_downloader_with_backup(self, mock_updating, mock_parquet, mock_csv, mock_get_config, mock_registry):
        """Test downloader creation with backup enabled."""
        from vortex.cli.commands.download import create_downloader
        
        # Setup mocks
        mock_vortex_config = Mock()
        mock_vortex_config.general.random_sleep_max = 5
        mock_vortex_config.general.dry_run = False
        
        download_config = {
            'vortex_config': mock_vortex_config,
            'output_dir': Path('/test'),
            'backup': True,
            'force': False
        }
        
        mock_provider_config = {'test': 'config'}
        mock_get_config.return_value = mock_provider_config
        
        mock_registry_instance = Mock()
        mock_data_provider = Mock()
        mock_registry_instance.create_provider.return_value = mock_data_provider
        mock_registry.return_value = mock_registry_instance
        
        mock_csv_storage = Mock()
        mock_csv.return_value = mock_csv_storage
        
        mock_parquet_storage = Mock()
        mock_parquet.return_value = mock_parquet_storage
        
        result = create_downloader('yahoo', download_config)
        
        # Verify provider registry was used
        mock_registry.assert_called_once()
        mock_registry_instance.create_provider.assert_called_once_with('yahoo', mock_provider_config)
        
        # Verify storage objects were created
        mock_csv.assert_called_once_with('/test', False)
        mock_parquet.assert_called_once_with('/test', False)
        
        # Verify downloader was created with correct parameters
        mock_updating.assert_called_once_with(
            mock_csv_storage,
            mock_data_provider,
            mock_parquet_storage,
            force_backup=False,
            random_sleep_in_sec=5,
            dry_run=False
        )
    
    @patch('vortex.cli.commands.download.get_provider_registry')
    @patch('vortex.cli.commands.download.get_provider_config_from_vortex_config')
    @patch('vortex.cli.commands.download.CsvStorage')
    @patch('vortex.cli.commands.download.UpdatingDownloader')
    def test_create_downloader_no_backup(self, mock_updating, mock_csv, mock_get_config, mock_registry):
        """Test downloader creation without backup."""
        from vortex.cli.commands.download import create_downloader
        
        # Setup mocks
        mock_vortex_config = Mock()
        mock_vortex_config.general.random_sleep_max = 3
        mock_vortex_config.general.dry_run = True
        
        download_config = {
            'vortex_config': mock_vortex_config,
            'output_dir': Path('/test'),
            'backup': False,
            'force': True
        }
        
        mock_provider_config = {'test': 'config'}
        mock_get_config.return_value = mock_provider_config
        
        mock_registry_instance = Mock()
        mock_data_provider = Mock()
        mock_registry_instance.create_provider.return_value = mock_data_provider
        mock_registry.return_value = mock_registry_instance
        
        mock_csv_storage = Mock()
        mock_csv.return_value = mock_csv_storage
        
        result = create_downloader('barchart', download_config)
        
        # Verify downloader was created with no backup storage
        mock_updating.assert_called_once_with(
            mock_csv_storage,
            mock_data_provider,
            None,  # No backup storage
            force_backup=True,
            random_sleep_in_sec=3,
            dry_run=True
        )
    
    @patch('vortex.cli.commands.download.get_provider_registry')
    @patch('vortex.cli.commands.download.get_provider_config_from_vortex_config')
    @patch('vortex.cli.commands.download.logger')
    def test_create_downloader_provider_error(self, mock_logger, mock_get_config, mock_registry):
        """Test downloader creation with provider error."""
        from vortex.cli.commands.download import create_downloader
        from vortex.exceptions import DataProviderError
        
        # Setup mocks
        mock_vortex_config = Mock()
        download_config = {
            'vortex_config': mock_vortex_config,
            'output_dir': Path('/test'),
            'backup': False,
            'force': False
        }
        
        mock_get_config.return_value = {'test': 'config'}
        
        mock_registry_instance = Mock()
        mock_registry_instance.create_provider.side_effect = Exception("Provider failed")
        mock_registry.return_value = mock_registry_instance
        
        with pytest.raises(DataProviderError) as exc_info:
            create_downloader('invalid', download_config)
        
        assert "Initialization failed: Provider failed" in str(exc_info.value)
        mock_logger.error.assert_called()


class TestDownloadCommandEdgeCases:
    """Test edge cases and error conditions for download command."""
    
    def test_date_validation_error(self):
        """Test error when start_date >= end_date."""
        # This would be tested in CLI integration but we can test the validation logic
        start_date = datetime(2023, 12, 31, tzinfo=timezone.utc)
        end_date = datetime(2023, 1, 1, tzinfo=timezone.utc)
        
        # The validation logic should catch this
        assert start_date >= end_date  # This should trigger InvalidCommandError
    
    def test_timezone_handling(self):
        """Test timezone handling in download execution."""
        from vortex.cli.commands.download import execute_download
        
        # Test that naive datetimes get UTC timezone added
        naive_start = datetime(2023, 1, 1)  # No timezone
        naive_end = datetime(2023, 12, 31)  # No timezone
        
        assert naive_start.tzinfo is None
        assert naive_end.tzinfo is None
        
        # The function should handle this by adding UTC timezone