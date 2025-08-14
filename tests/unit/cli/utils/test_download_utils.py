"""
Tests for CLI download utility functions.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock, MagicMock
import pytest

from vortex.cli.utils.download_utils import (
    load_assets_from_file,
    get_default_assets_file,
    create_downloader_components,
    create_downloader,
    parse_date_range,
    parse_symbols_list,
    validate_periods,
    count_download_jobs,
    format_download_summary
)
from vortex.exceptions import CLIError, DataProviderError
from vortex.models.period import Period


class TestLoadAssetsFromFile:
    """Test asset file loading functionality."""
    
    def test_load_assets_from_file_success(self):
        """Test successful loading of assets file."""
        assets_data = {
            "stock": {
                "AAPL": {"code": "AAPL", "periods": "1d"},
                "GOOGL": {"code": "GOOGL", "periods": "1d"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(assets_data, f)
            f.flush()
            
            try:
                result = load_assets_from_file(Path(f.name))
                assert result == assets_data
            finally:
                Path(f.name).unlink()
    
    def test_load_assets_from_file_not_found(self):
        """Test loading non-existent assets file."""
        non_existent = Path("/tmp/non_existent_assets.json")
        
        with pytest.raises(CLIError, match="Assets file not found"):
            load_assets_from_file(non_existent)
    
    def test_load_assets_from_file_invalid_json(self):
        """Test loading assets file with invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"invalid": json data}')  # Invalid JSON
            f.flush()
            
            try:
                with pytest.raises(CLIError, match="Invalid JSON in assets file"):
                    load_assets_from_file(Path(f.name))
            finally:
                Path(f.name).unlink()
    
    def test_load_assets_from_file_permission_error(self):
        """Test loading assets file with permission error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"test": "data"}, f)
            f.flush()
            
            try:
                with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                    with pytest.raises(CLIError, match="Error loading assets file"):
                        load_assets_from_file(Path(f.name))
            finally:
                Path(f.name).unlink()


class TestGetDefaultAssetsFile:
    """Test default assets file discovery."""
    
    @patch('pathlib.Path.exists')
    def test_get_default_assets_file_provider_specific(self, mock_exists):
        """Test getting provider-specific default assets file."""
        def path_exists(path):
            return str(path) == "config/assets/yahoo.json"
        
        mock_exists.side_effect = lambda self: path_exists(str(self))
        
        result = get_default_assets_file("yahoo")
        
        assert result == Path("config/assets/yahoo.json")
    
    @patch('pathlib.Path.exists')
    def test_get_default_assets_file_fallback_to_default(self, mock_exists):
        """Test fallback to general default assets file."""
        def path_exists(path):
            return str(path) == "config/assets/default.json"
        
        mock_exists.side_effect = lambda self: path_exists(str(self))
        
        result = get_default_assets_file("nonexistent")
        
        assert result == Path("config/assets/default.json")
    
    @patch('pathlib.Path.exists')
    def test_get_default_assets_file_none_found(self, mock_exists):
        """Test when no default assets file is found."""
        mock_exists.return_value = False
        
        result = get_default_assets_file("nonexistent")
        
        assert result is None
    
    @patch('pathlib.Path.exists')
    def test_get_default_assets_file_check_order(self, mock_exists):
        """Test that provider-specific file is checked before default."""
        mock_exists.return_value = True  # Both files exist
        
        result = get_default_assets_file("barchart")
        
        # Should return provider-specific file
        assert result == Path("config/assets/barchart.json")


class TestCreateDownloaderComponents:
    """Test downloader component creation."""
    
    @patch('vortex.cli.utils.download_utils.get_provider_registry')
    @patch('vortex.cli.utils.download_utils.get_provider_config_with_defaults')
    def test_create_downloader_components_success(self, mock_get_config, mock_get_registry):
        """Test successful downloader components creation."""
        # Mock configuration
        mock_config_manager = Mock()
        provider_config = {"username": "test", "password": "pass"}
        mock_get_config.return_value = provider_config
        
        # Mock registry and provider
        mock_registry = Mock()
        mock_data_provider = Mock()
        mock_registry.create_provider.return_value = mock_data_provider
        mock_get_registry.return_value = mock_registry
        
        output_dir = Path("/tmp/test_output")
        
        # Test with backup enabled
        data_provider, csv_storage, parquet_storage = create_downloader_components(
            mock_config_manager, "yahoo", output_dir, backup_enabled=True
        )
        
        # Verify results
        assert data_provider == mock_data_provider
        assert csv_storage is not None
        assert parquet_storage is not None
        
        # Verify function calls
        mock_get_config.assert_called_once_with(mock_config_manager, "yahoo")
        mock_registry.create_provider.assert_called_once_with("yahoo", provider_config)
    
    @patch('vortex.cli.utils.download_utils.get_provider_registry')
    @patch('vortex.cli.utils.download_utils.get_provider_config_with_defaults')
    def test_create_downloader_components_no_backup(self, mock_get_config, mock_get_registry):
        """Test downloader components creation without backup."""
        # Mock configuration
        mock_config_manager = Mock()
        provider_config = {"host": "localhost"}
        mock_get_config.return_value = provider_config
        
        # Mock registry and provider
        mock_registry = Mock()
        mock_data_provider = Mock()
        mock_registry.create_provider.return_value = mock_data_provider
        mock_get_registry.return_value = mock_registry
        
        output_dir = Path("/tmp/test_output")
        
        # Test with backup disabled
        data_provider, csv_storage, parquet_storage = create_downloader_components(
            mock_config_manager, "ibkr", output_dir, backup_enabled=False
        )
        
        # Verify results
        assert data_provider == mock_data_provider
        assert csv_storage is not None
        assert parquet_storage is None
    
    @patch('vortex.cli.utils.download_utils.get_provider_registry')
    @patch('vortex.cli.utils.download_utils.get_provider_config_with_defaults')
    def test_create_downloader_components_provider_error(self, mock_get_config, mock_get_registry):
        """Test handling of provider creation errors."""
        # Mock configuration
        mock_config_manager = Mock()
        mock_get_config.return_value = {}
        
        # Mock registry to raise error
        mock_registry = Mock()
        mock_registry.create_provider.side_effect = ValueError("Provider not found")
        mock_get_registry.return_value = mock_registry
        
        output_dir = Path("/tmp/test_output")
        
        with pytest.raises(DataProviderError, match="Failed to create provider"):
            create_downloader_components(
                mock_config_manager, "invalid", output_dir, backup_enabled=False
            )


class TestCreateDownloader:
    """Test downloader creation."""
    
    def test_create_downloader_with_parquet(self):
        """Test creating downloader with Parquet backup."""
        mock_data_provider = Mock()
        mock_csv_storage = Mock()
        mock_parquet_storage = Mock()
        
        with patch('vortex.cli.utils.download_utils.UpdatingDownloader') as mock_downloader_class:
            mock_downloader = Mock()
            mock_downloader_class.return_value = mock_downloader
            
            result = create_downloader(mock_data_provider, mock_csv_storage, mock_parquet_storage)
            
            assert result == mock_downloader
            mock_downloader_class.assert_called_once_with(
                mock_data_provider, mock_csv_storage, mock_parquet_storage
            )
    
    def test_create_downloader_without_parquet(self):
        """Test creating downloader without Parquet backup."""
        mock_data_provider = Mock()
        mock_csv_storage = Mock()
        
        with patch('vortex.cli.utils.download_utils.UpdatingDownloader') as mock_downloader_class:
            mock_downloader = Mock()
            mock_downloader_class.return_value = mock_downloader
            
            result = create_downloader(mock_data_provider, mock_csv_storage, None)
            
            assert result == mock_downloader
            mock_downloader_class.assert_called_once_with(mock_data_provider, mock_csv_storage)


class TestParseDateRange:
    """Test date range parsing."""
    
    @patch('vortex.cli.utils.download_utils.get_default_date_range')
    def test_parse_date_range_success(self, mock_get_default):
        """Test successful date range parsing."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        mock_get_default.return_value = (start_date, end_date)
        
        result_start, result_end = parse_date_range("2024-01-01", "2024-12-31", "yahoo")
        
        assert result_start == start_date
        assert result_end == end_date
        mock_get_default.assert_called_once_with("yahoo", start_date, end_date)
    
    @patch('vortex.cli.utils.download_utils.get_default_date_range')
    def test_parse_date_range_with_none_dates(self, mock_get_default):
        """Test date range parsing with None dates (use defaults)."""
        default_start = datetime(2024, 1, 1)
        default_end = datetime(2024, 12, 31)
        mock_get_default.return_value = (default_start, default_end)
        
        result_start, result_end = parse_date_range(None, None, "yahoo")
        
        assert result_start == default_start
        assert result_end == default_end
        mock_get_default.assert_called_once_with("yahoo", None, None)
    
    @patch('vortex.cli.utils.download_utils.get_default_date_range')
    def test_parse_date_range_mixed_none(self, mock_get_default):
        """Test date range parsing with one None date."""
        start_date = datetime(2024, 6, 1)
        default_end = datetime(2024, 12, 31)
        mock_get_default.return_value = (start_date, default_end)
        
        result_start, result_end = parse_date_range("2024-06-01", None, "yahoo")
        
        assert result_start == start_date
        assert result_end == default_end
        mock_get_default.assert_called_once_with("yahoo", start_date, None)
    
    def test_parse_date_range_invalid_format(self):
        """Test date range parsing with invalid date format."""
        with pytest.raises(CLIError, match="Invalid date format"):
            parse_date_range("2024/01/01", "2024/12/31", "yahoo")
        
        with pytest.raises(CLIError, match="Invalid date format"):
            parse_date_range("not-a-date", "2024-12-31", "yahoo")
    
    @patch('vortex.cli.utils.download_utils.get_default_date_range')
    def test_parse_date_range_start_after_end(self, mock_get_default):
        """Test date range parsing where start date is after end date."""
        # Mock default range where start > end
        mock_get_default.return_value = (datetime(2024, 12, 31), datetime(2024, 1, 1))
        
        with pytest.raises(CLIError, match="Start date must be before end date"):
            parse_date_range("2024-12-31", "2024-01-01", "yahoo")
    
    @patch('vortex.cli.utils.download_utils.get_default_date_range')
    def test_parse_date_range_same_dates(self, mock_get_default):
        """Test date range parsing where start and end dates are the same."""
        same_date = datetime(2024, 6, 15)
        mock_get_default.return_value = (same_date, same_date)
        
        with pytest.raises(CLIError, match="Start date must be before end date"):
            parse_date_range("2024-06-15", "2024-06-15", "yahoo")


class TestParseSymbolsList:
    """Test symbols list parsing."""
    
    def test_parse_symbols_list_command_line_only(self):
        """Test parsing symbols from command line only."""
        symbols = ("AAPL", "GOOGL", "MSFT")
        
        result = parse_symbols_list(symbols, None)
        
        assert result == ["AAPL", "GOOGL", "MSFT"]
    
    def test_parse_symbols_list_file_only(self):
        """Test parsing symbols from file only."""
        symbols_content = "AAPL\nGOOGL\nMSFT\n# This is a comment\nTSLA\n"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(symbols_content)
            f.flush()
            
            try:
                result = parse_symbols_list((), Path(f.name))
                assert result == ["AAPL", "GOOGL", "MSFT", "TSLA"]
            finally:
                Path(f.name).unlink()
    
    def test_parse_symbols_list_combined(self):
        """Test parsing symbols from both command line and file."""
        symbols_content = "NVDA\nAMD\n"
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(symbols_content)
            f.flush()
            
            try:
                result = parse_symbols_list(("AAPL", "GOOGL"), Path(f.name))
                assert result == ["AAPL", "GOOGL", "NVDA", "AMD"]
            finally:
                Path(f.name).unlink()
    
    def test_parse_symbols_list_duplicates_removed(self):
        """Test that duplicate symbols are removed while preserving order."""
        symbols_content = "AAPL\nGOOGL\nAAPL\n"  # AAPL appears twice
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(symbols_content)
            f.flush()
            
            try:
                result = parse_symbols_list(("AAPL", "MSFT"), Path(f.name))
                assert result == ["AAPL", "MSFT", "GOOGL"]  # AAPL only appears once
            finally:
                Path(f.name).unlink()
    
    def test_parse_symbols_list_empty_lines_and_comments(self):
        """Test parsing file with empty lines and comments."""
        symbols_content = """
# Portfolio symbols
AAPL

GOOGL
# Technology stocks
MSFT

# Empty lines above and below should be ignored

TSLA
"""
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(symbols_content)
            f.flush()
            
            try:
                result = parse_symbols_list((), Path(f.name))
                assert result == ["AAPL", "GOOGL", "MSFT", "TSLA"]
            finally:
                Path(f.name).unlink()
    
    def test_parse_symbols_list_file_not_found(self):
        """Test parsing symbols from non-existent file."""
        non_existent = Path("/tmp/non_existent_symbols.txt")
        
        with pytest.raises(CLIError, match="Symbols file not found"):
            parse_symbols_list(("AAPL",), non_existent)
    
    def test_parse_symbols_list_file_permission_error(self):
        """Test parsing symbols file with permission error."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("AAPL\nGOOGL\n")
            f.flush()
            
            try:
                with patch('builtins.open', side_effect=PermissionError("Permission denied")):
                    with pytest.raises(CLIError, match="Error reading symbols file"):
                        parse_symbols_list((), Path(f.name))
            finally:
                Path(f.name).unlink()


class TestValidatePeriods:
    """Test period validation."""
    
    def test_validate_periods_single_period(self):
        """Test validating single period."""
        result = validate_periods("1d")
        
        assert len(result) == 1
        assert result[0] == Period.DAILY
    
    def test_validate_periods_multiple_periods(self):
        """Test validating multiple periods."""
        result = validate_periods("1d,1h,5m")
        
        assert len(result) == 3
        assert Period.DAILY in result
        assert Period.HOURLY in result
        assert Period.FIVE_MINUTE in result
    
    def test_validate_periods_with_spaces(self):
        """Test validating periods with spaces."""
        result = validate_periods("1d, 1h, 5m")
        
        assert len(result) == 3
        assert Period.DAILY in result
        assert Period.HOURLY in result
        assert Period.FIVE_MINUTE in result
    
    def test_validate_periods_invalid_period(self):
        """Test validating invalid period."""
        with pytest.raises(CLIError, match="Invalid period: invalid"):
            validate_periods("1d,invalid,1h")
    
    def test_validate_periods_empty_period(self):
        """Test validating with empty period string."""
        with pytest.raises(CLIError, match="Invalid period: "):
            validate_periods("1d,,1h")
    
    def test_validate_periods_all_valid_types(self):
        """Test validating all supported period types."""
        periods_str = "1m,5m,15m,30m,1h,1d,1W,1M"
        result = validate_periods(periods_str)
        
        assert len(result) == 8
        # Verify all periods were parsed successfully
        period_values = [p.value for p in result]
        assert "1m" in period_values
        assert "1d" in period_values
        assert "1W" in period_values
        assert "1M" in period_values


class TestCountDownloadJobs:
    """Test download job counting."""
    
    def test_count_download_jobs_basic(self):
        """Test counting download jobs with basic symbols."""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        instrument_configs = {
            "AAPL": Mock(periods="1d"),
            "GOOGL": Mock(periods="1d,1h"), 
            "MSFT": None  # No config
        }
        
        result = count_download_jobs(symbols, instrument_configs)
        
        # AAPL: 1 period, GOOGL: 2 periods, MSFT: 1 default
        assert result == 4
    
    def test_count_download_jobs_no_periods_attribute(self):
        """Test counting jobs when config has no periods attribute."""
        symbols = ["AAPL", "GOOGL"]
        instrument_configs = {
            "AAPL": Mock(spec=[]),  # Mock without periods attribute
            "GOOGL": Mock(code="GOOGL")  # Mock with different attribute
        }
        # Remove periods attribute from mocks
        for config in instrument_configs.values():
            if hasattr(config, 'periods'):
                delattr(config, 'periods')
        
        result = count_download_jobs(symbols, instrument_configs)
        
        # Both should default to 1 job each
        assert result == 2
    
    def test_count_download_jobs_no_configs(self):
        """Test counting jobs when no configs are provided."""
        symbols = ["AAPL", "GOOGL", "MSFT"]
        instrument_configs = {}
        
        result = count_download_jobs(symbols, instrument_configs)
        
        # All symbols default to 1 job each
        assert result == 3
    
    def test_count_download_jobs_mixed_periods(self):
        """Test counting jobs with mixed period configurations."""
        symbols = ["AAPL", "GOOGL", "TSLA"]
        instrument_configs = {
            "AAPL": Mock(periods="1d,1h,5m"),  # 3 periods
            "GOOGL": Mock(periods="1d"),       # 1 period
            "TSLA": Mock(periods=[])           # Empty periods (non-string)
        }
        
        result = count_download_jobs(symbols, instrument_configs)
        
        # AAPL: 3, GOOGL: 1, TSLA: 1 (default for non-string)
        assert result == 5
    
    def test_count_download_jobs_empty_symbols(self):
        """Test counting jobs with empty symbols list."""
        result = count_download_jobs([], {})
        
        assert result == 0


class TestFormatDownloadSummary:
    """Test download summary formatting."""
    
    def test_format_download_summary_basic(self):
        """Test basic download summary formatting."""
        provider = "yahoo"
        symbols = ["AAPL", "GOOGL", "MSFT"]
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        output_dir = Path("/tmp/downloads")
        total_jobs = 5
        
        result = format_download_summary(
            provider, symbols, start_date, end_date, output_dir, total_jobs
        )
        
        expected = {
            'provider': 'YAHOO',
            'symbols_count': 3,
            'symbols_preview': 'AAPL, GOOGL, MSFT',
            'date_range': '2024-01-01 to 2024-12-31',
            'output_directory': '/tmp/downloads',
            'total_jobs': 5
        }
        
        assert result == expected
    
    def test_format_download_summary_many_symbols(self):
        """Test download summary formatting with many symbols."""
        provider = "barchart"
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA", "AMD", "INTC"]  # 7 symbols
        start_date = datetime(2024, 6, 1)
        end_date = datetime(2024, 6, 30)
        output_dir = Path("/data/stocks")
        total_jobs = 14
        
        result = format_download_summary(
            provider, symbols, start_date, end_date, output_dir, total_jobs
        )
        
        # Should show first 5 symbols plus "..."
        assert result['provider'] == 'BARCHART'
        assert result['symbols_count'] == 7
        assert result['symbols_preview'] == 'AAPL, GOOGL, MSFT, TSLA, NVDA...'
        assert result['date_range'] == '2024-06-01 to 2024-06-30'
        assert result['output_directory'] == '/data/stocks'
        assert result['total_jobs'] == 14
    
    def test_format_download_summary_exactly_five_symbols(self):
        """Test download summary formatting with exactly 5 symbols."""
        provider = "ibkr"
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "NVDA"]  # Exactly 5
        start_date = datetime(2024, 3, 15)
        end_date = datetime(2024, 3, 20)
        output_dir = Path("/home/user/data")
        total_jobs = 10
        
        result = format_download_summary(
            provider, symbols, start_date, end_date, output_dir, total_jobs
        )
        
        # Should show all 5 symbols without "..."
        assert result['symbols_preview'] == 'AAPL, GOOGL, MSFT, TSLA, NVDA'
        assert '...' not in result['symbols_preview']
    
    def test_format_download_summary_single_symbol(self):
        """Test download summary formatting with single symbol."""
        provider = "yahoo"
        symbols = ["AAPL"]
        start_date = datetime(2024, 8, 1)
        end_date = datetime(2024, 8, 31)
        output_dir = Path("./output")
        total_jobs = 1
        
        result = format_download_summary(
            provider, symbols, start_date, end_date, output_dir, total_jobs
        )
        
        assert result['symbols_count'] == 1
        assert result['symbols_preview'] == 'AAPL'
        assert result['date_range'] == '2024-08-01 to 2024-08-31'
        assert result['output_directory'] == './output'
        assert result['total_jobs'] == 1
    
    def test_format_download_summary_provider_case(self):
        """Test that provider names are properly uppercased."""
        test_cases = [
            ("yahoo", "YAHOO"),
            ("barchart", "BARCHART"),
            ("ibkr", "IBKR"),
            ("mixed_Case", "MIXED_CASE")
        ]
        
        for provider_input, expected_output in test_cases:
            result = format_download_summary(
                provider_input, ["AAPL"], datetime(2024, 1, 1), 
                datetime(2024, 1, 2), Path("/tmp"), 1
            )
            assert result['provider'] == expected_output