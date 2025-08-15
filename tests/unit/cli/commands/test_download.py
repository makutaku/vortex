"""Simplified tests for refactored download command."""

import pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
import tempfile
import click

from vortex.cli.commands.download import download
from vortex.cli.commands.symbol_resolver import load_config_instruments
from vortex.cli.commands.download_executor import show_download_summary
from vortex.exceptions import CLIError


class TestLoadConfigInstruments:
    """Test load_config_instruments function."""
    
    def test_load_config_instruments_success(self):
        """Test successful loading of config instruments."""
        # Test the function can load from a valid JSON structure
        test_data = {
            "stock": {
                "AAPL": {"code": "AAPL", "periods": "1d"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            import json
            json.dump(test_data, f)
            f.flush()
            
            result = load_config_instruments(Path(f.name))
            
        assert 'AAPL' in result
        assert result['AAPL']['asset_class'] == 'stock'
        assert result['AAPL']['code'] == 'AAPL'
    
    def test_load_config_instruments_file_not_found(self):
        """Test error handling when file doesn't exist."""
        with pytest.raises(CLIError, match="Assets file not found"):
            load_config_instruments(Path('nonexistent.json'))


class TestDownloadCommand:
    """Test the main download command."""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all major dependencies."""
        with patch('vortex.cli.commands.download.get_or_create_config_manager') as mock_config, \
             patch('vortex.cli.commands.download.ensure_provider_configured') as mock_ensure, \
             patch('vortex.cli.commands.download.get_default_date_range') as mock_dates, \
             patch('vortex.cli.commands.download.resolve_symbols_and_configs') as mock_resolve, \
             patch('vortex.cli.commands.download.DownloadExecutor') as mock_executor:
            
            # Configure mocks
            mock_config.return_value.get_default_provider.return_value = 'yahoo'
            mock_config.return_value.get_provider_config.return_value = {}
            mock_dates.return_value = (datetime.now() - timedelta(days=30), datetime.now())
            mock_resolve.return_value = (['AAPL'], {'AAPL': {'asset_class': 'stock'}})
            mock_executor.return_value.execute_downloads.return_value = (1, 1)  # (successful_jobs, total_jobs)
            
            yield {
                'config': mock_config,
                'ensure': mock_ensure,
                'dates': mock_dates,
                'resolve': mock_resolve,
                'executor': mock_executor
            }
    
    def test_download_with_symbol_success(self, runner, mock_dependencies):
        """Test successful download with symbol."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the CLI context
            with patch('vortex.cli.commands.download.click.get_current_context') as mock_ctx:
                mock_ctx.return_value.obj = {}
                
                result = runner.invoke(download, [
                    '--symbol', 'AAPL',
                    '--output-dir', temp_dir,
                    '--yes'
                ], obj={})
        
        assert result.exit_code == 0
        assert 'Download completed' in result.output
    
    def test_download_no_symbols_error(self, runner, mock_dependencies):
        """Test download fails when no symbols resolved."""
        # Configure mock to return empty symbols
        mock_dependencies['resolve'].return_value = ([], {})
        
        result = runner.invoke(download, ['--yes'], obj={})
        
        assert result.exit_code == 1
        assert 'No symbols to download' in result.output
    
    def test_download_with_provider(self, runner, mock_dependencies):
        """Test download with specific provider."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = runner.invoke(download, [
                '--provider', 'yahoo',
                '--symbol', 'AAPL',
                '--output-dir', temp_dir,
                '--yes'
            ], obj={})
        
        assert result.exit_code == 0
        mock_dependencies['ensure'].assert_called_once()


class TestShowDownloadSummary:
    """Test show_download_summary function."""
    
    def test_show_download_summary(self, capsys):
        """Test summary display."""
        show_download_summary(0.0, 1.0, 10, 8, 2)
        
        captured = capsys.readouterr()
        assert 'Download Summary' in captured.out
        assert 'Total Jobs: 10' in captured.out
        assert 'Successful: 8' in captured.out
        assert 'Failed: 2' in captured.out
        assert 'Success Rate: 80.0%' in captured.out