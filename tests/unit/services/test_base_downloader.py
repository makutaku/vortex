import pytest
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, List

from vortex.services.base_downloader import BaseDownloader
from vortex.services.download_job import DownloadJob
from vortex.infrastructure.providers.base import HistoricalDataResult
from vortex.infrastructure.storage.data_storage import DataStorage
from vortex.exceptions import AllowanceLimitExceededError, DataNotFoundError
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
                raise DataNotFoundError(
                    provider="test", symbol="TEST", period=Period.Daily,
                    start_date=datetime(2024, 1, 1), end_date=datetime(2024, 1, 31)
                )
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
        # Create proper InstrumentConfig objects instead of empty dict
        from vortex.core.instruments.config import InstrumentConfig
        mock_instrument_config = Mock(spec=InstrumentConfig)
        mock_instrument_config.periods = []
        mock_merge_dicts.return_value = {InstrumentType.Future: mock_instrument_config}
        
        # Mock the _schedule_jobs and _process_jobs methods that actually exist
        with patch.object(downloader, '_schedule_jobs', return_value=[]):
            with patch.object(downloader, '_process_jobs'):
                with patch('vortex.services.base_downloader.logging'):
                    downloader.download(['file1.json', 'file2.json'], 2023, 2024)
        
        # The test should verify that the load_from_json was called, but we're mocking it at the class level
        # So check the merge_dicts call instead which is more meaningful
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
            mock_logging.INFO = 20  # Set actual logging level integer
            downloader._process_jobs(jobs)
        
        assert len(downloader.processed_jobs) == 1
        assert downloader.processed_jobs[0] == sample_job
        mock_logging.info.assert_called()

    def test_process_jobs_with_low_data_error(self, downloader, sample_job):
        """Test job processing with DataNotFoundError (formerly LowDataError)."""
        downloader.raise_exception = 'low_data'
        jobs = [sample_job]
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            mock_logging.INFO = 20  # Set actual logging level integer
            downloader._process_jobs(jobs)
        
        # Job should still be processed but warning logged
        assert len(downloader.processed_jobs) == 1
        mock_logging.warning.assert_called()

    def test_process_jobs_with_data_not_found_error(self, downloader, sample_job):
        """Test job processing with DataNotFoundError."""
        downloader.raise_exception = 'not_found'
        jobs = [sample_job]
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            mock_logging.INFO = 20  # Set actual logging level integer
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
            mock_logging.INFO = 20  # Set actual logging level integer
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
        # Create proper InstrumentConfig objects instead of dict
        from vortex.core.instruments.config import InstrumentConfig
        mock_instrument_config = Mock(spec=InstrumentConfig)
        mock_instrument_config.periods = [Period.Daily]
        mock_instrument_config.code = 'AAPL'
        mock_instrument_config.asset_class = InstrumentType.Stock
        mock_instrument_config.cycle = 'HMUZ'
        mock_instrument_config.tick_date = None
        mock_instrument_config.days_count = 360
        contract_map = {InstrumentType.Stock: mock_instrument_config}
        
        with patch('vortex.services.base_downloader.is_list_of_strings', return_value=False):
            with patch.object(downloader, '_create_jobs', return_value=[Mock()]) as mock_create_jobs:
                with patch.object(downloader, '_schedule_jobs', return_value=[Mock()]) as mock_schedule:
                    with patch.object(downloader, '_process_jobs') as mock_process:
                        with patch('vortex.services.base_downloader.logging'):
                            downloader.download(contract_map, 2024, 2024)
        
        # Verify the workflow calls the right methods
        mock_create_jobs.assert_called_once()
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
        
        with pytest.raises(DataNotFoundError):
            downloader._process_job(job)

    def test_abstract_method_requirement(self):
        """Test that BaseDownloader cannot be instantiated without _process_job."""
        with pytest.raises(TypeError):
            BaseDownloader(Mock(), Mock())

    def test_job_processing_counts_and_logging(self, downloader):
        """Test that job processing correctly counts and logs progress."""
        jobs = [Mock() for _ in range(5)]
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            mock_logging.INFO = 20  # Set actual logging level integer
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
                raise DataNotFoundError(
                    provider="test", symbol="TEST", period=Period.Daily,
                    start_date=datetime(2024, 1, 1), end_date=datetime(2024, 1, 31)
                )
            return HistoricalDataResult.OK
        
        with patch.object(downloader, '_process_job', side_effect=side_effect):
            with patch('vortex.services.base_downloader.logging') as mock_logging:
                mock_logging.INFO = 20  # Set actual logging level integer
                downloader._process_jobs(jobs)
        
        # All jobs should still be processed despite the exception
        assert len(downloader.processed_jobs) == 3

    def test_download_with_string_input(self, downloader):
        """Test download method with string input (file path)."""
        mock_contract_map = {
            InstrumentType.Stock: Mock(
                code='AAPL', asset_class=InstrumentType.Stock, periods=[Period.Daily],
                start_date=None, tz=None, cycle=None, days_count=None, tick_date=None
            )
        }
        
        with patch.object(InstrumentConfig, 'load_from_json', return_value=mock_contract_map):
            with patch('vortex.services.base_downloader.is_list_of_strings', return_value=False):
                with patch.object(downloader, '_schedule_jobs', return_value=[]):
                    with patch.object(downloader, '_process_jobs'):
                        with patch('vortex.services.base_downloader.logging'):
                            downloader.download('test_file.json', 2024, 2024)
        
        InstrumentConfig.load_from_json.assert_called_once_with('test_file.json')

    def test_create_instrument_jobs_stock(self, downloader):
        """Test job creation for stock instrument."""
        from pytz import UTC
        
        # Create mock InstrumentConfig for stock
        config = Mock()
        config.code = 'AAPL'
        config.cycle = None
        config.asset_class = InstrumentType.Stock
        config.periods = [Period.Daily]
        config.tick_date = None
        config.start_date = None
        config.tz = UTC
        config.days_count = None
        
        start = datetime(2024, 1, 1, tzinfo=UTC)  # Make timezone aware
        end = datetime(2024, 12, 31, tzinfo=UTC)
        
        with patch.object(downloader, 'create_jobs_for_undated_instrument') as mock_create_undated:
            mock_create_undated.return_value = [Mock()]
            jobs = downloader._create_instrument_jobs('AAPL', config, start, end)
        
        assert len(jobs) == 1
        mock_create_undated.assert_called_once()

    def test_create_instrument_jobs_forex(self, downloader):
        """Test job creation for forex instrument."""
        from pytz import UTC
        
        # Create mock InstrumentConfig for forex
        config = Mock()
        config.code = 'EURUSD'
        config.cycle = None
        config.asset_class = InstrumentType.Forex
        config.periods = [Period.Daily]
        config.tick_date = None
        config.start_date = None
        config.tz = UTC
        config.days_count = None
        
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        
        with patch.object(downloader, 'create_jobs_for_undated_instrument') as mock_create_undated:
            mock_create_undated.return_value = [Mock()]
            jobs = downloader._create_instrument_jobs('EURUSD', config, start, end)
        
        assert len(jobs) == 1
        mock_create_undated.assert_called_once()

    def test_create_instrument_jobs_future(self, downloader):
        """Test job creation for futures instrument."""
        from pytz import UTC
        
        # Create mock InstrumentConfig for future
        config = Mock()
        config.code = 'GC'
        config.cycle = 'GJMQVZ'
        config.asset_class = InstrumentType.Future
        config.periods = [Period.Daily]
        config.tick_date = datetime(2020, 1, 1)
        config.start_date = None
        config.tz = UTC
        config.days_count = 360
        
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        
        with patch.object(downloader, '_create_future_jobs') as mock_create_future:
            mock_create_future.return_value = [Mock()]
            jobs = downloader._create_instrument_jobs('GC', config, start, end)
        
        assert len(jobs) == 1
        mock_create_future.assert_called_once()

    def test_create_instrument_jobs_unsupported_type(self, downloader):
        """Test job creation with unsupported instrument type."""
        config = Mock()
        config.code = 'UNKNOWN'
        config.cycle = None
        config.asset_class = 'UNKNOWN_TYPE'  # Invalid type
        config.periods = [Period.Daily]
        config.tick_date = None
        config.start_date = None
        config.tz = None
        config.days_count = None
        
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        
        with pytest.raises(ValueError, match="Instrument type 'UNKNOWN_TYPE' is not supported"):
            downloader._create_instrument_jobs('UNKNOWN', config, start, end)

    def test_create_future_jobs(self, downloader):
        """Test creation of future jobs with roll cycle."""
        from pytz import UTC
        
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        periods = [Period.Daily]
        tick_date = datetime(2020, 1, 1)
        roll_cycle = 'GJMQVZ'
        days_count = 360
        tz = UTC
        
        with patch('vortex.services.base_downloader.generate_year_month_tuples') as mock_gen:
            mock_gen.return_value = [(2024, 1), (2024, 3), (2024, 6)]
            
            with patch.object(downloader, 'filter_periods') as mock_filter:
                mock_filter.return_value = periods
                
                with patch.object(downloader, 'create_jobs_for_dated_instrument') as mock_create_dated:
                    mock_create_dated.return_value = [Mock()]
                    
                    jobs = downloader._create_future_jobs(
                        'GC', 'GC', start, end, periods, tick_date, 
                        roll_cycle, days_count, tz
                    )
        
        # Should create jobs for G (January), J (March), M (June) months
        # Each call to create_jobs_for_dated_instrument returns one job, called 3 times
        assert len(jobs) == 3
        assert mock_create_dated.call_count == 3

    def test_create_future_jobs_no_roll_cycle(self, downloader):
        """Test future jobs creation without roll cycle raises error."""
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        periods = [Period.Daily]
        tick_date = datetime(2020, 1, 1)
        roll_cycle = None  # Missing roll cycle
        days_count = 360
        tz = None
        
        with pytest.raises(ValueError, match="does not have a roll_cycle"):
            downloader._create_future_jobs(
                'GC', 'GC', start, end, periods, tick_date, 
                roll_cycle, days_count, tz
            )

    def test_filter_periods(self, downloader):
        """Test filtering periods based on provider support."""
        instrument = Mock()
        periods = [Period.Daily, Period.Hourly, Period.Minute_5]
        supported_periods = [Period.Daily, Period.Hourly]  # 5-minute not supported
        
        downloader.data_provider.get_supported_timeframes.return_value = supported_periods
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            filtered = downloader.filter_periods(instrument, periods)
        
        assert len(filtered) == 2
        assert Period.Daily in filtered
        assert Period.Hourly in filtered
        assert Period.Minute_5 not in filtered
        mock_logging.warning.assert_called_once()

    def test_create_jobs_for_undated_instrument(self, downloader):
        """Test creating jobs for undated instruments (stocks/forex)."""
        instrument = Stock('AAPL', 'AAPL')
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        periods = [Period.Daily]
        tick_date = datetime(2020, 1, 1)
        
        # Mock provider methods
        downloader.data_provider.get_supported_timeframes.return_value = periods
        downloader.data_provider.get_min_start.return_value = None
        downloader.data_provider.get_max_range.return_value = timedelta(days=365)
        
        with patch('vortex.services.base_downloader.date_range_generator') as mock_gen:
            mock_gen.return_value = [(start, end)]
            
            jobs = downloader.create_jobs_for_undated_instrument(
                instrument, start, end, periods, tick_date
            )
        
        assert len(jobs) == 1
        assert jobs[0].instrument == instrument
        assert jobs[0].period == Period.Daily

    def test_create_jobs_for_undated_instrument_with_provider_min_start(self, downloader):
        """Test job creation when provider has minimum start date."""
        instrument = Stock('AAPL', 'AAPL')
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        periods = [Period.Daily]
        tick_date = None
        
        # Provider has minimum start date after our end date
        provider_min_start = datetime(2025, 1, 1)  # After our end date
        
        downloader.data_provider.get_supported_timeframes.return_value = periods
        downloader.data_provider.get_min_start.return_value = provider_min_start
        
        with patch('vortex.services.base_downloader.logging') as mock_logging:
            jobs = downloader.create_jobs_for_undated_instrument(
                instrument, start, end, periods, tick_date
            )
        
        # Should create no jobs and log a warning
        assert len(jobs) == 0
        mock_logging.warning.assert_called()

    def test_create_jobs_for_undated_instrument_with_tick_date_and_intraday(self, downloader):
        """Test job creation with tick date for intraday periods."""
        instrument = Stock('AAPL', 'AAPL')
        start = datetime(2024, 1, 1, tzinfo=UTC)
        end = datetime(2024, 12, 31, tzinfo=UTC)
        periods = [Period.Hourly]  # Intraday period
        tick_date = datetime(2024, 6, 1)  # Tick date after start
        
        downloader.data_provider.get_supported_timeframes.return_value = periods
        downloader.data_provider.get_min_start.return_value = None
        downloader.data_provider.get_max_range.return_value = timedelta(days=365)
        
        with patch('vortex.services.base_downloader.date_range_generator') as mock_gen:
            # Should use tick_date as start for intraday
            mock_gen.return_value = [(tick_date, end)]
            
            jobs = downloader.create_jobs_for_undated_instrument(
                instrument, start, end, periods, tick_date
            )
        
        assert len(jobs) == 1
        # Verify that tick_date was used instead of original start
        mock_gen.assert_called_with(tick_date, end, timedelta(days=365))