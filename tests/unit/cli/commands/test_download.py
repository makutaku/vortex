"""Tests for download command."""

import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from click.testing import CliRunner
import tempfile
import os

from vortex.cli.commands.download import (
    load_config_instruments, get_default_assets_file, download
)
from vortex.exceptions import CLIError, MissingArgumentError, ConfigurationError
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
        
        assert result == ['AAPL', 'GOOGL', 'MSFT']
        mock_load.assert_called_once_with('test.json')
    
    def test_load_config_instruments_file_error(self):
        """Test error handling when assets file loading fails."""
        with patch.object(InstrumentConfig, 'load_from_json') as mock_load:
            mock_load.side_effect = Exception("File not found")
            
            with pytest.raises(SystemExit):  # click.Abort() causes SystemExit
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
        """Test when no assets files exist."""
        with patch('vortex.cli.commands.download.Path.exists') as mock_exists:
            mock_exists.return_value = False
            
            with pytest.raises(SystemExit):  # click.Abort() causes SystemExit
                get_default_assets_file('nonexistent')


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
             patch('vortex.cli.commands.download.get_available_providers') as mock_providers:
            
            # Configure mocks
            mock_config_instance = Mock()
            mock_config_instance.get_output_directory.return_value = Path('/test/output')
            mock_config.return_value = mock_config_instance
            
            mock_registry_instance = Mock()
            mock_registry_instance.create_provider.return_value = Mock()
            mock_registry.return_value = mock_registry_instance
            
            mock_providers.return_value = ['yahoo', 'barchart']
            
            yield {
                'config': mock_config,
                'registry': mock_registry,
                'csv_storage': mock_csv,
                'parquet_storage': mock_parquet,
                'downloader': mock_downloader,
                'providers': mock_providers,
                'config_instance': mock_config_instance,
                'registry_instance': mock_registry_instance
            }
    
    def test_download_with_symbol(self, runner, mock_dependencies):
        """Test download with single symbol."""
        with patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = [Stock('AAPL', 'AAPL')]
            mock_dependencies['downloader'].return_value.download.return_value = []
            
            result = runner.invoke(download, ['--symbol', 'AAPL', '--yes'])
        
        assert result.exit_code == 0
        mock_validate.assert_called()
        mock_parse.assert_called()
    
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
                mock_dependencies['downloader'].return_value.download.return_value = []
                
                result = runner.invoke(download, ['--symbols-file', symbols_file, '--yes'])
            
            assert result.exit_code == 0
            mock_validate.assert_called()
            mock_parse.assert_called()
        finally:
            os.unlink(symbols_file)
    
    def test_download_with_assets_file(self, runner, mock_dependencies):
        """Test download with assets file."""
        with patch('vortex.cli.commands.download.load_config_instruments') as mock_load, \
             patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse:
            
            mock_load.return_value = ['GC', 'ES']
            mock_validate.return_value = ['GC', 'ES']  
            mock_parse.return_value = [Mock(), Mock()]
            mock_dependencies['downloader'].return_value.download.return_value = []
            
            result = runner.invoke(download, ['--assets', 'test.json', '--yes'])
        
        assert result.exit_code == 0
        mock_load.assert_called()
        mock_validate.assert_called()
    
    def test_download_no_symbols_provided(self, runner, mock_dependencies):
        """Test download when no symbols are provided."""
        with patch('vortex.cli.commands.download.get_default_assets_file') as mock_default, \
             patch('vortex.cli.commands.download.load_config_instruments') as mock_load, \
             patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse:
            
            mock_default.return_value = Path('default.json')
            mock_load.return_value = ['DEFAULT1', 'DEFAULT2']
            mock_validate.return_value = ['DEFAULT1', 'DEFAULT2']
            mock_parse.return_value = [Mock(), Mock()]
            mock_dependencies['downloader'].return_value.download.return_value = []
            
            result = runner.invoke(download, ['--yes'])
        
        assert result.exit_code == 0
        mock_default.assert_called()
        mock_load.assert_called()
    
    def test_download_custom_date_range(self, runner, mock_dependencies):
        """Test download with custom date range."""
        with patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = [Stock('AAPL', 'AAPL')]
            mock_dependencies['downloader'].return_value.download.return_value = []
            
            result = runner.invoke(download, [
                '--symbol', 'AAPL',
                '--start-date', '2023-01-01',
                '--end-date', '2023-12-31',
                '--yes'
            ])
        
        assert result.exit_code == 0
        # Verify downloader was called with custom dates
        downloader_call = mock_dependencies['downloader'].return_value.download.call_args
        assert downloader_call is not None
    
    def test_download_invalid_provider(self, runner, mock_dependencies):
        """Test download with invalid provider."""
        mock_dependencies['providers'].return_value = ['yahoo', 'barchart']  # Valid providers
        
        result = runner.invoke(download, [
            '--provider', 'invalid_provider',
            '--symbol', 'AAPL',
            '--yes'
        ])
        
        # Should fail with invalid provider
        assert result.exit_code != 0
        assert 'invalid_provider' in result.output
    
    def test_download_configuration_error(self, runner, mock_dependencies):
        """Test download with configuration error."""
        mock_dependencies['config'].side_effect = ConfigurationError("Config error")
        
        result = runner.invoke(download, ['--symbol', 'AAPL', '--yes'])
        
        assert result.exit_code != 0
        assert 'Config error' in result.output or 'error' in result.output.lower()
    
    def test_download_with_output_dir(self, runner, mock_dependencies):
        """Test download with custom output directory."""
        with patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = [Stock('AAPL', 'AAPL')]
            mock_dependencies['downloader'].return_value.download.return_value = []
            
            result = runner.invoke(download, [
                '--symbol', 'AAPL',
                '--output-dir', '/custom/output',
                '--yes'
            ])
        
        assert result.exit_code == 0
        # Verify CSV storage was created with custom output dir
        mock_dependencies['csv_storage'].assert_called()
        csv_call_args = mock_dependencies['csv_storage'].call_args[1]
        assert str(csv_call_args['output_directory']) == '/custom/output'
    
    def test_download_progress_display(self, runner, mock_dependencies):
        """Test that progress is displayed during download."""
        with patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse, \
             patch('vortex.cli.commands.download.Progress') as mock_progress:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = [Stock('AAPL', 'AAPL')]
            mock_dependencies['downloader'].return_value.download.return_value = []
            
            # Mock progress context manager
            mock_progress_instance = Mock()
            mock_progress.return_value.__enter__.return_value = mock_progress_instance
            
            result = runner.invoke(download, ['--symbol', 'AAPL', '--yes'])
        
        assert result.exit_code == 0
        mock_progress.assert_called()
        mock_progress_instance.add_task.assert_called()
    
    def test_download_multiple_symbols_validation(self, runner, mock_dependencies):
        """Test validation of multiple symbols."""
        with patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse:
            
            # Test that multiple symbols are validated
            mock_validate.return_value = ['AAPL', 'GOOGL', 'MSFT']
            mock_parse.return_value = [Stock('AAPL', 'AAPL'), Stock('GOOGL', 'GOOGL'), Stock('MSFT', 'MSFT')]
            mock_dependencies['downloader'].return_value.download.return_value = []
            
            result = runner.invoke(download, [
                '--symbol', 'AAPL', 'GOOGL', 'MSFT',
                '--yes'
            ])
        
        assert result.exit_code == 0
        mock_validate.assert_called_with(['AAPL', 'GOOGL', 'MSFT'])
        assert len(mock_parse.call_args[0][0]) == 3  # Three symbols parsed

    def test_download_enhanced_error_handling(self, runner, mock_dependencies):
        """Test enhanced error handling during download."""
        with patch('vortex.cli.commands.download.validate_symbols') as mock_validate, \
             patch('vortex.cli.commands.download.parse_instruments') as mock_parse, \
             patch('vortex.cli.commands.download.enhanced_error_handler') as mock_handler:
            
            mock_validate.return_value = ['AAPL']
            mock_parse.return_value = [Stock('AAPL', 'AAPL')]
            
            # Simulate download error
            download_error = Exception("Download failed")
            mock_dependencies['downloader'].return_value.download.side_effect = download_error
            
            result = runner.invoke(download, ['--symbol', 'AAPL', '--yes'])
        
        # Should handle error gracefully
        assert result.exit_code != 0
        mock_handler.assert_called_with(download_error)