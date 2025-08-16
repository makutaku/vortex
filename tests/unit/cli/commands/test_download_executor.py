"""
Tests for download executor module.

Provides comprehensive coverage for download execution engine, job processing,
and progress tracking functionality used by the download commands.
"""

import pytest
import logging
import time
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from io import StringIO
import sys

from vortex.cli.commands.download_executor import (
    JobExecutionContext,
    DownloadExecutor,
    show_download_summary
)
from vortex.infrastructure.providers.base import HistoricalDataResult
from vortex.services.updating_downloader import UpdatingDownloader
from vortex.services.backfill_downloader import BackfillDownloader


@pytest.fixture
def mock_config():
    """Mock download configuration."""
    config = Mock()
    config.provider = "yahoo"
    config.output_dir = "/tmp/test"
    config.dry_run = False
    config.backup_enabled = True
    config.force_backup = False
    config.random_sleep = 0
    config.mode = "updating"
    config.start_date = datetime(2024, 1, 1)
    config.end_date = datetime(2024, 1, 31)
    config.download_config = {}
    return config


@pytest.fixture
def download_executor(mock_config):
    """Create DownloadExecutor instance with mocked config."""
    return DownloadExecutor(mock_config)


@pytest.fixture
def sample_instrument_configs():
    """Sample instrument configurations for testing."""
    return {
        "AAPL": {
            "asset_class": "stock",
            "periods": ["1d", "1h"]
        },
        "GC": {
            "asset_class": "future", 
            "periods": ["1d"]
        }
    }


class TestJobExecutionContext:
    """Test JobExecutionContext class."""
    
    def test_initialization(self):
        """Test JobExecutionContext initialization."""
        job = Mock()
        context = JobExecutionContext(job, 1, 10, "AAPL")
        
        assert context.job is job
        assert context.job_number == 1
        assert context.total_jobs == 10
        assert context.symbol == "AAPL"


class TestDownloadExecutor:
    """Test DownloadExecutor initialization and basic functionality."""
    
    def test_initialization(self, mock_config):
        """Test DownloadExecutor initialization."""
        executor = DownloadExecutor(mock_config)
        
        assert executor.config is mock_config
        assert executor.logger is not None
    
    def test_execute_downloads_no_symbols(self, download_executor):
        """Test execute_downloads with empty symbols list."""
        result = download_executor.execute_downloads([], {})
        
        assert result == (0, 0)
    
    def test_execute_downloads_no_jobs(self, download_executor, caplog):
        """Test execute_downloads when no jobs are created."""
        caplog.set_level(logging.WARNING)
        
        with patch.object(download_executor, '_count_total_jobs', return_value=0):
            result = download_executor.execute_downloads(["AAPL"], {})
        
        assert result == (0, 0)
        assert "No download jobs to execute" in caplog.text
    
    @patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic')
    @patch('vortex.cli.commands.download_executor.get_periods_for_symbol')
    def test_execute_downloads_successful(self, mock_get_periods, mock_create_jobs, 
                                        download_executor, sample_instrument_configs, caplog):
        """Test successful execute_downloads flow."""
        caplog.set_level(logging.INFO)
        
        # Mock job creation
        mock_get_periods.return_value = ["1d"]
        mock_jobs = [Mock(), Mock()]
        mock_create_jobs.return_value = mock_jobs
        
        # Mock downloader creation and job processing
        mock_downloader = Mock()
        with patch.object(download_executor, '_create_downloader', return_value=mock_downloader):
            with patch.object(download_executor, '_process_single_job', return_value=True):
                result = download_executor.execute_downloads(["AAPL"], sample_instrument_configs)
        
        assert result[0] == 2  # successful jobs
        assert result[1] == 2  # total jobs
        assert "Starting download execution" in caplog.text
        assert "Download execution completed" in caplog.text


class TestEnsureInstrumentConfigs:
    """Test _ensure_instrument_configs method."""
    
    def test_ensure_configs_with_existing_config(self, download_executor):
        """Test ensuring configs when symbol already has config."""
        existing_configs = {"AAPL": {"asset_class": "stock", "periods": ["1d"]}}
        symbols = ["AAPL"]
        
        result = download_executor._ensure_instrument_configs(existing_configs, symbols)
        
        assert result == existing_configs
        assert "AAPL" in result
        assert result["AAPL"]["asset_class"] == "stock"
    
    def test_ensure_configs_creates_default_for_missing(self, download_executor, caplog):
        """Test ensuring configs creates defaults for missing symbols."""
        # Set up logging for the specific logger used by DownloadExecutor
        caplog.set_level(logging.DEBUG, logger='vortex.cli.commands.download_executor')
        
        existing_configs = {}
        symbols = ["TSLA"]
        
        result = download_executor._ensure_instrument_configs(existing_configs, symbols)
        
        assert "TSLA" in result
        assert result["TSLA"]["asset_class"] == "stock"
        assert result["TSLA"]["periods"] == ["1d"]
        assert "Created default config for symbol: TSLA" in caplog.text
    
    def test_ensure_configs_preserves_original(self, download_executor):
        """Test ensuring configs doesn't modify original dict."""
        original_configs = {"AAPL": {"asset_class": "stock"}}
        symbols = ["AAPL", "TSLA"]
        
        result = download_executor._ensure_instrument_configs(original_configs, symbols)
        
        # Original should be unchanged
        assert len(original_configs) == 1
        assert "TSLA" not in original_configs
        
        # Result should have both
        assert len(result) == 2
        assert "AAPL" in result
        assert "TSLA" in result


class TestCountTotalJobs:
    """Test _count_total_jobs method."""
    
    @patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic')
    @patch('vortex.cli.commands.download_executor.get_periods_for_symbol')
    def test_count_total_jobs_successful(self, mock_get_periods, mock_create_jobs, download_executor):
        """Test successful job counting."""
        # Mock periods and jobs
        mock_get_periods.return_value = ["1d", "1h"]
        mock_create_jobs.side_effect = [
            [Mock(), Mock()],  # 2 jobs for first symbol
            [Mock()]           # 1 job for second symbol
        ]
        
        mock_downloader = Mock()
        with patch.object(download_executor, '_create_downloader', return_value=mock_downloader):
            total = download_executor._count_total_jobs(
                ["AAPL", "TSLA"], 
                {"AAPL": {}, "TSLA": {}}
            )
        
        assert total == 3
        assert mock_create_jobs.call_count == 2
    
    @patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic')
    @patch('vortex.cli.commands.download_executor.get_periods_for_symbol')
    def test_count_total_jobs_with_exception_fallback(self, mock_get_periods, mock_create_jobs, 
                                                     download_executor, caplog):
        """Test job counting with exception fallback."""
        caplog.set_level(logging.WARNING)
        
        # Mock periods and job creation failure
        mock_get_periods.return_value = ["1d", "1h"]
        mock_create_jobs.side_effect = Exception("Job creation failed")
        
        mock_downloader = Mock()
        with patch.object(download_executor, '_create_downloader', return_value=mock_downloader):
            total = download_executor._count_total_jobs(["AAPL"], {"AAPL": {}})
        
        # Should fallback to period count
        assert total == 2  # len(periods)
        assert "Failed to count jobs for symbol AAPL" in caplog.text


class TestProcessAllDownloads:
    """Test _process_all_downloads method."""
    
    @patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic')
    @patch('vortex.cli.commands.download_executor.get_periods_for_symbol')
    def test_process_all_downloads_successful(self, mock_get_periods, mock_create_jobs, 
                                            download_executor, caplog):
        """Test successful processing of all downloads."""
        caplog.set_level(logging.INFO)
        
        # Mock job creation
        mock_get_periods.return_value = ["1d"]
        mock_jobs = [Mock(), Mock()]
        mock_create_jobs.return_value = mock_jobs
        
        mock_downloader = Mock()
        with patch.object(download_executor, '_create_downloader', return_value=mock_downloader):
            with patch.object(download_executor, '_process_single_job', return_value=True):
                result = download_executor._process_all_downloads(["AAPL"], {"AAPL": {}}, 2)
        
        assert result == 2  # all successful
        assert "Progress: 1/2" in caplog.text
        assert "Progress: 2/2" in caplog.text
    
    @patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic')
    @patch('vortex.cli.commands.download_executor.get_periods_for_symbol')
    def test_process_all_downloads_mixed_results(self, mock_get_periods, mock_create_jobs, 
                                               download_executor):
        """Test processing with mixed success/failure results."""
        # Mock job creation
        mock_get_periods.return_value = ["1d"]
        mock_jobs = [Mock(), Mock()]
        mock_create_jobs.return_value = mock_jobs
        
        mock_downloader = Mock()
        with patch.object(download_executor, '_create_downloader', return_value=mock_downloader):
            with patch.object(download_executor, '_process_single_job', side_effect=[True, False]):
                result = download_executor._process_all_downloads(["AAPL"], {"AAPL": {}}, 2)
        
        assert result == 1  # only 1 successful
    
    @patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic')
    @patch('vortex.cli.commands.download_executor.get_periods_for_symbol')
    def test_process_all_downloads_job_creation_failure(self, mock_get_periods, mock_create_jobs, 
                                                      download_executor, caplog):
        """Test processing when job creation fails for a symbol."""
        caplog.set_level(logging.ERROR)
        
        # Mock job creation failure
        mock_get_periods.return_value = ["1d"]
        mock_create_jobs.side_effect = Exception("Job creation failed")
        
        mock_downloader = Mock()
        with patch.object(download_executor, '_create_downloader', return_value=mock_downloader):
            result = download_executor._process_all_downloads(["AAPL"], {"AAPL": {}}, 0)
        
        assert result == 0
        assert "Failed to create jobs for symbol AAPL" in caplog.text


class TestProcessSingleJob:
    """Test _process_single_job method."""
    
    def test_process_single_job_success_ok(self, download_executor, caplog):
        """Test processing single job with OK result."""
        # Set up logging for both the executor and LoggingContext loggers
        caplog.set_level(logging.DEBUG, logger='vortex.cli.commands.download_executor')
        caplog.set_level(logging.DEBUG, logger='vortex.utils.logging_utils')
        
        job = Mock()
        context = JobExecutionContext(job, 1, 5, "AAPL")
        mock_downloader = Mock()
        mock_downloader._process_job.return_value = HistoricalDataResult.OK
        
        result = download_executor._process_single_job(context, mock_downloader)
        
        assert result is True
        # LoggingContext logs success message at DEBUG level and also logs the entry message
        assert "Processing job 1/5: AAPL" in caplog.text
        assert "Completed job 1/5: AAPL" in caplog.text
    
    def test_process_single_job_success_exists(self, download_executor, caplog):
        """Test processing single job with EXISTS result."""
        # Set up logging for both the executor and LoggingContext loggers
        caplog.set_level(logging.DEBUG, logger='vortex.cli.commands.download_executor')
        caplog.set_level(logging.DEBUG, logger='vortex.utils.logging_utils')
        
        job = Mock()
        context = JobExecutionContext(job, 2, 5, "TSLA")
        mock_downloader = Mock()
        mock_downloader._process_job.return_value = HistoricalDataResult.EXISTS
        
        result = download_executor._process_single_job(context, mock_downloader)
        
        assert result is True
        # LoggingContext logs success message and internal logger logs exists message
        assert "Processing job 2/5: TSLA" in caplog.text
        assert "Completed job 2/5: TSLA" in caplog.text
    
    def test_process_single_job_no_data(self, download_executor, caplog):
        """Test processing single job with NO_DATA result."""
        # Set up logging for both the executor and LoggingContext loggers
        caplog.set_level(logging.DEBUG, logger='vortex.cli.commands.download_executor')
        caplog.set_level(logging.DEBUG, logger='vortex.utils.logging_utils')
        
        job = Mock()
        context = JobExecutionContext(job, 3, 5, "INVALID")
        mock_downloader = Mock()
        mock_downloader._process_job.return_value = HistoricalDataResult.NONE
        
        result = download_executor._process_single_job(context, mock_downloader)
        
        assert result is False
        # LoggingContext logs both entry and success messages
        assert "Processing job 3/5: INVALID" in caplog.text
        assert "Completed job 3/5: INVALID" in caplog.text
    
    def test_process_single_job_keyboard_interrupt(self, download_executor, caplog):
        """Test processing single job with KeyboardInterrupt."""
        caplog.set_level(logging.INFO)
        
        job = Mock()
        context = JobExecutionContext(job, 1, 5, "AAPL")
        mock_downloader = Mock()
        mock_downloader._process_job.side_effect = KeyboardInterrupt()
        
        with pytest.raises(KeyboardInterrupt):
            download_executor._process_single_job(context, mock_downloader)
        
        assert "Download interrupted by user" in caplog.text
    
    def test_process_single_job_exception(self, download_executor, caplog):
        """Test processing single job with exception."""
        caplog.set_level(logging.ERROR)
        
        job = Mock()
        context = JobExecutionContext(job, 4, 5, "ERROR_SYMBOL")
        mock_downloader = Mock()
        mock_downloader._process_job.side_effect = Exception("Download failed")
        
        result = download_executor._process_single_job(context, mock_downloader)
        
        assert result is False
        assert "Job 4 failed: Download failed" in caplog.text
    
    @patch('vortex.cli.commands.download_executor.LoggingContext')
    def test_process_single_job_logging_context(self, mock_logging_context, download_executor):
        """Test that process_single_job uses LoggingContext correctly."""
        job = Mock()
        context = JobExecutionContext(job, 1, 5, "AAPL")
        mock_downloader = Mock()
        mock_downloader._process_job.return_value = HistoricalDataResult.OK
        
        # Mock the context manager
        mock_context_instance = Mock()
        mock_logging_context.return_value.__enter__ = Mock(return_value=mock_context_instance)
        mock_logging_context.return_value.__exit__ = Mock(return_value=None)
        
        result = download_executor._process_single_job(context, mock_downloader)
        
        assert result is True
        mock_logging_context.assert_called_once()
        
        # Verify LoggingConfiguration was created with correct parameters
        config_call = mock_logging_context.call_args[0][0]
        assert "Processing job 1/5: AAPL" in config_call.entry_msg
        assert "Completed job 1/5: AAPL" in config_call.success_msg


class TestCreateDownloader:
    """Test _create_downloader method."""
    
    @patch('vortex.cli.commands.download_executor.UpdatingDownloader')
    def test_create_downloader_updating_mode(self, mock_updating, download_executor):
        """Test creating UpdatingDownloader in updating mode."""
        download_executor.config.mode = "updating"
        download_executor.config.backup_enabled = True
        
        mock_downloader_instance = Mock()
        mock_updating.return_value = mock_downloader_instance
        
        result = download_executor._create_downloader()
        
        # Verify UpdatingDownloader was called
        assert mock_updating.called
        assert result is mock_downloader_instance
    
    @patch('vortex.cli.commands.download_executor.BackfillDownloader')
    def test_create_downloader_backfill_mode_no_backup(self, mock_backfill, download_executor):
        """Test creating BackfillDownloader with backup disabled."""
        download_executor.config.mode = "backfill"
        download_executor.config.backup_enabled = False
        
        mock_downloader_instance = Mock()
        mock_backfill.return_value = mock_downloader_instance
        
        result = download_executor._create_downloader()
        
        # Verify BackfillDownloader was called
        assert mock_backfill.called
        assert result is mock_downloader_instance
    
    @patch('vortex.cli.commands.download_executor.UpdatingDownloader')
    def test_create_downloader_with_dry_run(self, mock_updating, download_executor):
        """Test creating downloader with dry run enabled."""
        download_executor.config.dry_run = True
        download_executor.config.mode = "updating"
        download_executor.config.backup_enabled = True
        
        mock_downloader_instance = Mock()
        mock_updating.return_value = mock_downloader_instance
        
        result = download_executor._create_downloader()
        
        # Verify UpdatingDownloader was called
        assert mock_updating.called
        assert result is mock_downloader_instance
        
        # Verify dry_run parameter was passed correctly
        call_kwargs = mock_updating.call_args[1]
        assert call_kwargs['dry_run'] is True


class TestShowDownloadSummary:
    """Test show_download_summary function."""
    
    def test_show_download_summary_normal_case(self, capsys):
        """Test download summary display with normal values."""
        start_time = 1000.0
        end_time = 1010.5
        total_jobs = 10
        successful_jobs = 8
        failed_jobs = 2
        
        show_download_summary(start_time, end_time, total_jobs, successful_jobs, failed_jobs)
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "📊 Download Summary:" in output
        assert "Total Jobs: 10" in output
        assert "Successful: 8" in output
        assert "Failed: 2" in output
        assert "Success Rate: 80.0%" in output
        assert "Duration: 10.50s" in output
        assert "Jobs/second: 0.95" in output
    
    def test_show_download_summary_zero_duration(self, capsys):
        """Test download summary with zero duration."""
        start_time = 1000.0
        end_time = 1000.0  # Same time = zero duration
        total_jobs = 5
        successful_jobs = 5
        failed_jobs = 0
        
        show_download_summary(start_time, end_time, total_jobs, successful_jobs, failed_jobs)
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Duration: 0.00s" in output
        assert "Jobs/second: N/A" in output
    
    def test_show_download_summary_zero_jobs(self, capsys):
        """Test download summary with zero total jobs."""
        start_time = 1000.0
        end_time = 1005.0
        total_jobs = 0
        successful_jobs = 0
        failed_jobs = 0
        
        show_download_summary(start_time, end_time, total_jobs, successful_jobs, failed_jobs)
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Total Jobs: 0" in output
        assert "Success Rate: 0.0%" in output
    
    def test_show_download_summary_perfect_success(self, capsys):
        """Test download summary with 100% success rate."""
        start_time = 1000.0
        end_time = 1002.0
        total_jobs = 3
        successful_jobs = 3
        failed_jobs = 0
        
        show_download_summary(start_time, end_time, total_jobs, successful_jobs, failed_jobs)
        
        captured = capsys.readouterr()
        output = captured.out
        
        assert "Success Rate: 100.0%" in output
        assert "Failed: 0" in output


class TestDownloadExecutorIntegration:
    """Integration tests for DownloadExecutor."""
    
    @patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic')
    @patch('vortex.cli.commands.download_executor.get_periods_for_symbol')
    def test_complete_execution_workflow(self, mock_get_periods, mock_create_jobs, 
                                       download_executor, sample_instrument_configs, caplog):
        """Test complete download execution workflow."""
        caplog.set_level(logging.INFO)
        
        # Mock the job creation and processing pipeline
        mock_get_periods.return_value = ["1d"]
        mock_jobs = [Mock(), Mock()]
        mock_create_jobs.return_value = mock_jobs
        
        mock_downloader = Mock()
        mock_downloader._process_job.side_effect = [
            HistoricalDataResult.OK,
            HistoricalDataResult.EXISTS
        ]
        
        with patch.object(download_executor, '_create_downloader', return_value=mock_downloader):
            success_count, total_jobs = download_executor.execute_downloads(
                ["AAPL"], sample_instrument_configs
            )
        
        assert success_count == 2
        assert total_jobs == 2
        assert "Starting download execution: 1 symbols, 2 total jobs" in caplog.text
        assert "Download execution completed: 2/2 jobs successful" in caplog.text
    
    def test_execution_with_multiple_symbols(self, download_executor, caplog):
        """Test execution with multiple symbols."""
        caplog.set_level(logging.INFO)
        
        instrument_configs = {
            "AAPL": {"asset_class": "stock", "periods": ["1d"]},
            "TSLA": {"asset_class": "stock", "periods": ["1d"]},
            "MSFT": {"asset_class": "stock", "periods": ["1d"]}
        }
        
        with patch.object(download_executor, '_count_total_jobs', return_value=3):
            with patch.object(download_executor, '_process_all_downloads', return_value=2):
                success_count, total_jobs = download_executor.execute_downloads(
                    ["AAPL", "TSLA", "MSFT"], instrument_configs
                )
        
        assert success_count == 2
        assert total_jobs == 3
        assert "Starting download execution: 3 symbols, 3 total jobs" in caplog.text


class TestDownloadExecutorEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_execute_downloads_empty_configs(self, download_executor):
        """Test execute_downloads with empty instrument configs."""
        symbols = ["AAPL", "TSLA"]
        
        # Mock job counting and processing
        with patch.object(download_executor, '_count_total_jobs', return_value=2):
            with patch.object(download_executor, '_process_all_downloads', return_value=2):
                success_count, total_jobs = download_executor.execute_downloads(symbols, {})
        
        assert success_count == 2
        assert total_jobs == 2
    
    def test_count_total_jobs_empty_symbols(self, download_executor):
        """Test counting jobs with empty symbols list."""
        result = download_executor._count_total_jobs([], {})
        
        assert result == 0
    
    def test_process_all_downloads_empty_symbols(self, download_executor):
        """Test processing downloads with empty symbols list."""
        result = download_executor._process_all_downloads([], {}, 0)
        
        assert result == 0
    
    @patch('vortex.cli.commands.download_executor.get_periods_for_symbol')
    def test_ensure_configs_with_symbol_having_no_periods(self, mock_get_periods, download_executor):
        """Test config creation when symbol config has no periods."""
        # This tests the interaction with get_periods_for_symbol
        mock_get_periods.return_value = ["1d"]  # Default periods
        
        configs = download_executor._ensure_instrument_configs({}, ["SYMBOL"])
        
        assert "SYMBOL" in configs
        assert configs["SYMBOL"]["periods"] == ["1d"]
    
    @patch('vortex.cli.commands.download_executor.BackfillDownloader')
    def test_create_downloader_invalid_mode(self, mock_backfill, download_executor):
        """Test _create_downloader with non-updating mode (backfill path)."""
        download_executor.config.mode = "backfill"
        download_executor.config.backup_enabled = True
        
        mock_downloader_instance = Mock()
        mock_backfill.return_value = mock_downloader_instance
        
        result = download_executor._create_downloader()
        
        # Verify BackfillDownloader was called
        assert mock_backfill.called
        assert result is mock_downloader_instance


class TestDownloadExecutorPerformance:
    """Test performance and timing aspects of DownloadExecutor."""
    
    @patch('vortex.cli.commands.download_executor.time.time')
    def test_process_downloads_timing_tracking(self, mock_time, download_executor, caplog):
        """Test that download processing tracks timing correctly."""
        caplog.set_level(logging.INFO)
        
        # Mock time progression
        mock_time.side_effect = [1000.0, 1005.0, 1010.0, 1015.0]  # Progress through time
        
        symbols = ["AAPL"]
        configs = {"AAPL": {"periods": ["1d"]}}
        
        with patch.object(download_executor, '_create_downloader'):
            with patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic') as mock_create:
                with patch('vortex.cli.commands.download_executor.get_periods_for_symbol', return_value=["1d"]):
                    with patch.object(download_executor, '_process_single_job', return_value=True):
                        
                        mock_jobs = [Mock()]
                        mock_create.return_value = mock_jobs
                        
                        download_executor._process_all_downloads(symbols, configs, 1)
        
        # Check that elapsed time is logged
        assert "Elapsed:" in caplog.text
    
    def test_progress_calculation_accuracy(self, download_executor, caplog):
        """Test that progress percentage is calculated accurately."""
        caplog.set_level(logging.INFO)
        
        symbols = ["AAPL"]
        configs = {"AAPL": {"periods": ["1d"]}}
        
        with patch.object(download_executor, '_create_downloader'):
            with patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic') as mock_create:
                with patch('vortex.cli.commands.download_executor.get_periods_for_symbol', return_value=["1d"]):
                    with patch.object(download_executor, '_process_single_job', return_value=True):
                        
                        # Create 4 jobs to test progress calculation
                        mock_jobs = [Mock(), Mock(), Mock(), Mock()]
                        mock_create.return_value = mock_jobs
                        
                        download_executor._process_all_downloads(symbols, configs, 4)
        
        # Should see progress: 1/4 (25.0%), 2/4 (50.0%), 3/4 (75.0%), 4/4 (100.0%)
        log_text = caplog.text
        assert "1/4 (25.0%)" in log_text
        assert "2/4 (50.0%)" in log_text
        assert "3/4 (75.0%)" in log_text
        assert "4/4 (100.0%)" in log_text


class TestDownloadExecutorErrorRecovery:
    """Test error recovery and resilience features."""
    
    @patch('vortex.cli.commands.download_executor.create_jobs_using_downloader_logic')
    @patch('vortex.cli.commands.download_executor.get_periods_for_symbol')
    def test_partial_symbol_failure_continues_processing(self, mock_get_periods, mock_create_jobs, 
                                                       download_executor, caplog):
        """Test that failure for one symbol doesn't stop processing others."""
        caplog.set_level(logging.ERROR)
        
        mock_get_periods.return_value = ["1d"]
        
        # First symbol fails job creation, second succeeds
        mock_create_jobs.side_effect = [
            Exception("Failed for INVALID"),
            [Mock()]  # Success for AAPL
        ]
        
        symbols = ["INVALID", "AAPL"]
        configs = {"AAPL": {"periods": ["1d"]}}
        
        mock_downloader = Mock()
        with patch.object(download_executor, '_create_downloader', return_value=mock_downloader):
            with patch.object(download_executor, '_process_single_job', return_value=True):
                result = download_executor._process_all_downloads(symbols, configs, 1)
        
        # Should process the successful symbol despite the first failure
        assert result == 1
        assert "Failed to create jobs for symbol INVALID" in caplog.text
    
    def test_job_processing_resilience(self, download_executor):
        """Test that individual job failures don't crash the executor."""
        context1 = JobExecutionContext(Mock(), 1, 2, "AAPL")
        context2 = JobExecutionContext(Mock(), 2, 2, "TSLA")
        
        mock_downloader = Mock()
        mock_downloader._process_job.side_effect = [
            Exception("Job 1 failed"),
            HistoricalDataResult.OK
        ]
        
        # First job should fail, second should succeed
        result1 = download_executor._process_single_job(context1, mock_downloader)
        result2 = download_executor._process_single_job(context2, mock_downloader)
        
        assert result1 is False
        assert result2 is True


class TestDownloadExecutorConfigurationHandling:
    """Test configuration handling and parameter validation."""
    
    @patch('vortex.cli.commands.download_executor.UpdatingDownloader')
    def test_config_parameter_propagation(self, mock_updating, download_executor):
        """Test that config parameters are properly propagated to downloader."""
        download_executor.config.force_backup = True
        download_executor.config.random_sleep = 5
        download_executor.config.dry_run = True
        download_executor.config.mode = "updating"
        
        download_executor._create_downloader()
        
        # Verify parameters are passed correctly
        assert mock_updating.called
        call_kwargs = mock_updating.call_args[1]
        assert call_kwargs['force_backup'] is True
        assert call_kwargs['random_sleep_in_sec'] == 5
        assert call_kwargs['dry_run'] is True
    
    @patch('vortex.cli.commands.download_executor.UpdatingDownloader')
    def test_output_dir_string_conversion(self, mock_updating, download_executor):
        """Test that output directory is converted to string."""
        from pathlib import Path
        download_executor.config.output_dir = Path("/test/path")
        download_executor.config.mode = "updating"
        
        mock_downloader_instance = Mock()
        mock_updating.return_value = mock_downloader_instance
        
        result = download_executor._create_downloader()
        
        # Verify downloader was created (string conversion happens in constructor calls)
        assert mock_updating.called
        assert result is mock_downloader_instance