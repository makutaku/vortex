import pytest
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, List

from vortex.services.base_downloader import BaseDownloader
from vortex.services.download_job import DownloadJob
from vortex.infrastructure.providers.base import HistoricalDataResult
from vortex.infrastructure.storage.data_storage import DataStorage
from vortex.exceptions import LowDataError, AllowanceLimitExceededError, DataNotFoundError
from vortex.core.instruments import InstrumentConfig, InstrumentType
from vortex.models.forex import Forex
from vortex.models.future import Future
from vortex.models.stock import Stock
from vortex.models.period import Period


class ConcreteDownloader(BaseDownloader):
    """Concrete implementation for testing."""
    
    def __init__(self, data_storage, data_provider, backup_data_storage=None, force_backup=False):
        super().__init__(data_storage, data_provider, backup_data_storage, force_backup)
        self.processed_jobs = []
        self.process_result = HistoricalDataResult.OK
    
    def _process_job(self, job):
        """Mock implementation of abstract method."""
        self.processed_jobs.append(job)
        if hasattr(self, 'raise_exception') and self.raise_exception:
            if self.raise_exception == 'low_data':
                raise LowDataError("Low data")
            elif self.raise_exception == 'not_found':
                raise DataNotFoundError(
                    provider="test", symbol="TEST", period=Period.Daily,
                    start_date=datetime(2024, 1, 1), end_date=datetime(2024, 1, 31)
                )
        return self.process_result


class TestBaseDownloader:
    @pytest.fixture
    def mock_data_storage(self):
        """Create mock data storage."""
        return Mock(spec=DataStorage)

    @pytest.fixture
    def mock_data_provider(self):
        """Create mock data provider."""
        provider = Mock()
        provider.login = Mock()
        provider.logout = Mock()
        provider.get_min_start = Mock(return_value=datetime(2020, 1, 1))
        provider.get_max_range = Mock(return_value=timedelta(days=30))
        return provider

    @pytest.fixture
    def downloader(self, mock_data_storage, mock_data_provider):
        """Create concrete downloader instance."""
        return ConcreteDownloader(mock_data_storage, mock_data_provider)

    @pytest.fixture
    def sample_job(self):
        """Create sample download job."""
        return DownloadJob(
            data_provider=Mock(),
            data_storage=Mock(),
            instrument=Stock(id='AAPL', symbol='AAPL'),
            period=Period.Daily,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 31)
        )

    def test_downloader_initialization(self, mock_data_storage, mock_data_provider):
        """Test basic downloader initialization."""
        downloader = ConcreteDownloader(mock_data_storage, mock_data_provider)
        
        assert downloader.data_storage == mock_data_storage
        assert downloader.data_provider == mock_data_provider
        assert downloader.backup_data_storage is None
        assert downloader.force_backup is False

    def test_downloader_initialization_with_backup(self, mock_data_storage, mock_data_provider):
        """Test downloader initialization with backup storage."""
        mock_backup = Mock(spec=DataStorage)
        downloader = ConcreteDownloader(
            mock_data_storage, mock_data_provider,
            backup_data_storage=mock_backup, force_backup=True
        )
        
        assert downloader.backup_data_storage == mock_backup
        assert downloader.force_backup is True

    def test_login(self, downloader):
        """Test login delegates to data provider."""
        downloader.login()
        downloader.data_provider.login.assert_called_once()

    def test_logout(self, downloader):
        """Test logout delegates to data provider."""
        downloader.logout()
        downloader.data_provider.logout.assert_called_once()

    @patch('vortex.services.base_downloader.is_list_of_strings')
    @patch('vortex.services.base_downloader.merge_dicts')
    @patch.object(InstrumentConfig, 'load_from_json')
    def test_download_with_list_of_files(self, mock_load_json, mock_merge_dicts, mock_is_list_strings, downloader):
        """Test download with list of metadata files."""
        mock_is_list_strings.return_value = True
        mock_load_json.side_effect = [{'futures': {}}, {'stocks': {}}]
        mock_merge_dicts.return_value = {InstrumentType.Future: {}}
        
        # Mock the _schedule_jobs and _process_jobs methods that actually exist
        with patch.object(downloader, '_schedule_jobs', return_value=[]):
            with patch.object(downloader, '_process_jobs'):
                with patch('vortex.services.base_downloader.logging'):
                    downloader.download(['file1.json', 'file2.json'], 2023, 2024)
        
        mock_load_json.assert_has_calls([call('file1.json'), call('file2.json')])
        mock_merge_dicts.assert_called_once()

    def test_download_invalid_input_type(self, downloader):
        """Test download with invalid input type raises TypeError."""
        with pytest.raises(TypeError):
            downloader.download(123, 2023, 2024)

    @patch('vortex.services.base_downloader.logging')
    def test_download_logs_info(self, mock_logging, downloader):
        """Test download logs start information."""
        with patch.object(downloader, '_schedule_jobs', return_value=[]):
            with patch.object(downloader, '_process_jobs'):
                downloader.download({}, 2023, 2024)
        
        mock_logging.info.assert_any_call("Download from 2023 to 2024 ...")

    def test_process_jobs_successful(self, downloader, sample_job):
        """Test successful job processing."""
        jobs = [sample_job]
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            downloader._process_jobs(jobs)
        
        assert len(downloader.processed_jobs) == 1
        assert downloader.processed_jobs[0] == sample_job
        mock_logging.info.assert_called()

    def test_process_jobs_with_low_data_error(self, downloader, sample_job):
        """Test job processing with LowDataError."""
        downloader.raise_exception = 'low_data'
        jobs = [sample_job]
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            downloader._process_jobs(jobs)
        
        # Job should still be processed but warning logged
        assert len(downloader.processed_jobs) == 1
        mock_logging.warning.assert_called()

    def test_process_jobs_with_data_not_found_error(self, downloader, sample_job):
        """Test job processing with DataNotFoundError."""
        downloader.raise_exception = 'not_found'
        jobs = [sample_job]
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            downloader._process_jobs(jobs)
        
        # Job should still be processed but warning logged
        assert len(downloader.processed_jobs) == 1
        mock_logging.warning.assert_called()

    def test_process_jobs_multiple_jobs(self, downloader):
        """Test processing multiple jobs."""
        jobs = [
            DownloadJob(Mock(), Mock(), Stock(id='AAPL', symbol='AAPL'), 
                       Period.Daily, datetime(2024, 1, 1), datetime(2024, 1, 31)),
            DownloadJob(Mock(), Mock(), Stock(id='GOOGL', symbol='GOOGL'), 
                       Period.Daily, datetime(2024, 1, 1), datetime(2024, 1, 31))
        ]
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            downloader._process_jobs(jobs)
        
        assert len(downloader.processed_jobs) == 2
        mock_logging.info.assert_called()

    @patch('vortex.services.base_downloader.total_elements_in_dict_of_lists')
    def test_schedule_jobs(self, mock_total_elements, downloader):
        """Test job scheduling logic."""
        mock_total_elements.return_value = 2
        
        contract_map = {
            'AAPL': Mock(cycle='HMUZ'),  # Long cycle
            'GOOGL': Mock(cycle='HM')    # Short cycle  
        }
        
        job1 = Mock()
        job2 = Mock()
        jobs_per_instrument = {
            'AAPL': [job1],
            'GOOGL': [job2]
        }
        
        with patch('vortex.services.base_downloader.logging'):
            scheduled = downloader._schedule_jobs(contract_map, jobs_per_instrument)
        
        assert len(scheduled) == 2
        assert job1 in scheduled
        assert job2 in scheduled

    def test_schedule_jobs_with_different_cycle_lengths(self, downloader):
        """Test scheduling with different roll cycle lengths."""
        contract_map = {
            'SHORT': Mock(cycle='HM'),      # Short cycle (2 chars) -> max_count = 1
            'MEDIUM': Mock(cycle='HMUZ'),   # Medium cycle (4 chars) -> max_count = 1
            'LONG': Mock(cycle='FGHJKMNQUVXZ'),  # Long cycle (12 chars) -> max_count = 3
        }
        
        # Create enough jobs for each instrument
        jobs_per_instrument = {
            'SHORT': [Mock() for _ in range(3)],
            'MEDIUM': [Mock() for _ in range(3)],
            'LONG': [Mock() for _ in range(3)]
        }
        
        total_jobs = sum(len(jobs) for jobs in jobs_per_instrument.values())
        
        with patch('vortex.services.base_downloader.total_elements_in_dict_of_lists', return_value=total_jobs):
            with patch('vortex.services.base_downloader.logging'):
                scheduled = downloader._schedule_jobs(contract_map, jobs_per_instrument)
        
        # The scheduling should distribute jobs based on cycle length rules
        assert len(scheduled) == total_jobs

    def test_schedule_jobs_no_cycle(self, downloader):
        """Test scheduling when instrument has no cycle."""
        contract_map = {
            'NOCYCLE': Mock(cycle=None)
        }
        
        jobs_per_instrument = {
            'NOCYCLE': [Mock(), Mock()]
        }
        
        with patch('vortex.services.base_downloader.total_elements_in_dict_of_lists', return_value=2):
            with patch('vortex.services.base_downloader.logging'):
                scheduled = downloader._schedule_jobs(contract_map, jobs_per_instrument)
        
        # Should schedule jobs even without cycle
        assert len(scheduled) == 2

    def test_schedule_jobs_empty_instrument_list(self, downloader):
        """Test scheduling with missing instrument in jobs dict."""
        contract_map = {
            'MISSING': Mock(cycle='H'),
            'PRESENT': Mock(cycle='H')
        }
        
        jobs_per_instrument = {
            'PRESENT': [Mock()]  # MISSING is not in jobs dict
        }
        
        with patch('vortex.services.base_downloader.total_elements_in_dict_of_lists', return_value=1):
            with patch('vortex.services.base_downloader.logging'):
                scheduled = downloader._schedule_jobs(contract_map, jobs_per_instrument)
        
        assert len(scheduled) == 1

    def test_backup_storage_integration(self, mock_data_storage, mock_data_provider):
        """Test downloader with backup storage configuration."""
        backup_storage = Mock(spec=DataStorage)
        downloader = ConcreteDownloader(
            mock_data_storage, mock_data_provider,
            backup_data_storage=backup_storage, force_backup=True
        )
        
        # Test that backup storage is properly configured
        assert downloader.backup_data_storage is backup_storage
        assert downloader.force_backup is True

    def test_comprehensive_download_workflow(self, downloader):
        """Test complete download workflow."""
        contract_map = {InstrumentType.Stock: {'AAPL': {'symbol': 'AAPL', 'periods': [Period.Daily]}}}
        
        with patch('vortex.services.base_downloader.is_list_of_strings', return_value=False):
            with patch.object(downloader, '_schedule_jobs', return_value=[Mock()]) as mock_schedule:
                with patch.object(downloader, '_process_jobs') as mock_process:
                    with patch('vortex.services.base_downloader.logging'):
                        downloader.download(contract_map, 2024, 2024)
        
        # Verify the workflow calls the right methods
        mock_schedule.assert_called_once()
        mock_process.assert_called_once()

    def test_error_handling_in_process_job(self, downloader):
        """Test error handling within _process_job implementation."""
        job = DownloadJob(
            Mock(), Mock(), Stock(id='TEST', symbol='TEST'),
            Period.Daily, datetime(2024, 1, 1), datetime(2024, 1, 31)
        )
        
        # Test successful processing
        result = downloader._process_job(job)
        assert result == HistoricalDataResult.OK
        assert job in downloader.processed_jobs
        
        # Test with exception
        downloader.raise_exception = 'low_data'
        downloader.processed_jobs.clear()
        
        with pytest.raises(LowDataError):
            downloader._process_job(job)

    def test_abstract_method_requirement(self):
        """Test that BaseDownloader cannot be instantiated without _process_job."""
        with pytest.raises(TypeError):
            BaseDownloader(Mock(), Mock())

    def test_job_processing_counts_and_logging(self, downloader):
        """Test that job processing correctly counts and logs progress."""
        jobs = [Mock() for _ in range(5)]
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            downloader._process_jobs(jobs)
        
        # Should process all jobs
        assert len(downloader.processed_jobs) == 5
        
        # Should log progress for each job
        info_calls = [call for call in mock_logging.info.call_args_list 
                     if '/5 jobs processed' in str(call)]
        assert len(info_calls) == 5  # One progress log per job

    def test_exception_handling_continues_processing(self, downloader):
        """Test that exceptions in one job don't stop processing of others."""
        jobs = [Mock() for _ in range(3)]
        
        # Mock _process_job to fail on second job
        call_count = 0
        def side_effect(job):
            nonlocal call_count
            call_count += 1
            downloader.processed_jobs.append(job)
            if call_count == 2:
                raise LowDataError("Test error")
            return HistoricalDataResult.OK
        
        with patch.object(downloader, '_process_job', side_effect=side_effect):
            with patch('vortex.services.base_downloader.logging'):
                downloader._process_jobs(jobs)
        
        # All jobs should still be processed despite the exception
        assert len(downloader.processed_jobs) == 3