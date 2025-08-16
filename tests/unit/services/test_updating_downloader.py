"""Tests for the UpdatingDownloader class."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from vortex.services.updating_downloader import UpdatingDownloader
from vortex.services.download_job import DownloadJob
from vortex.infrastructure.providers.base import HistoricalDataResult
from vortex.models.price_series import PriceSeries


class TestUpdatingDownloader:
    """Test the UpdatingDownloader class."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create mock data storage."""
        return Mock()
    
    @pytest.fixture
    def mock_provider(self):
        """Create mock data provider."""
        return Mock()
    
    @pytest.fixture
    def mock_backup_storage(self):
        """Create mock backup storage."""
        return Mock()
    
    @pytest.fixture
    def downloader(self, mock_storage, mock_provider):
        """Create UpdatingDownloader instance."""
        return UpdatingDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider
        )
    
    @pytest.fixture
    def downloader_with_backup(self, mock_storage, mock_provider, mock_backup_storage):
        """Create UpdatingDownloader with backup storage."""
        return UpdatingDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            backup_data_storage=mock_backup_storage,
            force_backup=True
        )
    
    def test_downloader_initialization_basic(self, mock_storage, mock_provider):
        """Test basic UpdatingDownloader initialization."""
        downloader = UpdatingDownloader(mock_storage, mock_provider)
        
        assert downloader.data_storage == mock_storage
        assert downloader.data_provider == mock_provider
        assert downloader.backup_data_storage is None
        assert downloader.force_backup is False
        assert downloader.dry_run is False
        assert downloader.random_sleep_in_sec is None
    
    def test_downloader_initialization_with_options(self, mock_storage, mock_provider, mock_backup_storage):
        """Test UpdatingDownloader initialization with all options."""
        downloader = UpdatingDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            backup_data_storage=mock_backup_storage,
            force_backup=True,
            random_sleep_in_sec=5,
            dry_run=True
        )
        
        assert downloader.data_storage == mock_storage
        assert downloader.data_provider == mock_provider
        assert downloader.backup_data_storage == mock_backup_storage
        assert downloader.force_backup is True
        assert downloader.dry_run is True
        assert downloader.random_sleep_in_sec == 5
    
    def test_downloader_initialization_zero_sleep(self, mock_storage, mock_provider):
        """Test that zero sleep value gets set to None."""
        downloader = UpdatingDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            random_sleep_in_sec=0
        )
        
        assert downloader.random_sleep_in_sec is None
    
    def test_downloader_initialization_negative_sleep(self, mock_storage, mock_provider):
        """Test that negative sleep value gets set to None."""
        downloader = UpdatingDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            random_sleep_in_sec=-5
        )
        
        assert downloader.random_sleep_in_sec is None
    
    def test_process_job_existing_data_acceptable(self, downloader):
        """Test processing job when existing data is acceptable."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.start_date = datetime(2023, 1, 1)
        mock_job.end_date = datetime(2023, 12, 31)
        mock_job.__str__ = Mock(return_value="Test Job")
        
        # Create mock existing download
        mock_existing = Mock()
        mock_existing.is_data_coverage_acceptable.return_value = True
        mock_existing.df.shape = (100, 5)
        mock_job.load.return_value = mock_existing
        
        # Process the job
        result = downloader._process_job(mock_job)
        
        # Verify results
        assert result == HistoricalDataResult.EXISTS
        mock_job.load.assert_called_once()
        mock_existing.is_data_coverage_acceptable.assert_called_once_with(
            datetime(2023, 1, 1), datetime(2023, 12, 31)
        )
    
    @patch('vortex.services.updating_downloader.random_sleep')
    def test_pretend_not_a_bot_with_sleep(self, mock_sleep, downloader):
        """Test pretend_not_a_bot with random sleep enabled."""
        downloader.random_sleep_in_sec = 10
        
        downloader.pretend_not_a_bot()
        
        mock_sleep.assert_called_once_with(10)
    
    def test_pretend_not_a_bot_without_sleep(self, downloader):
        """Test pretend_not_a_bot without random sleep."""
        downloader.random_sleep_in_sec = None
        
        # Should not raise an exception
        downloader.pretend_not_a_bot()
    
    def test_process_job_existing_data_force_backup(self, downloader_with_backup):
        """Test processing job with existing data and force backup."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.start_date = datetime(2023, 1, 1)
        mock_job.end_date = datetime(2023, 12, 31)
        mock_job.__str__ = Mock(return_value="Test Job")
        
        # Create mock existing download
        mock_existing = Mock()
        mock_existing.is_data_coverage_acceptable.return_value = True
        mock_existing.df.shape = (100, 5)
        mock_job.load.return_value = mock_existing
        
        # Process the job
        result = downloader_with_backup._process_job(mock_job)
        
        # Verify backup was persisted
        assert result == HistoricalDataResult.EXISTS
        mock_job.persist.assert_called_once_with(mock_existing)
    
    def test_dry_run_flag(self, mock_storage, mock_provider):
        """Test dry run flag is properly set."""
        downloader = UpdatingDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            dry_run=True
        )
        
        assert downloader.dry_run is True
    
    def test_process_job_no_existing_data(self, downloader):
        """Test processing job when no existing data is found."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.start_date = datetime(2023, 1, 1)
        mock_job.end_date = datetime(2023, 12, 31)
        mock_job.__str__ = Mock(return_value="Test Job")
        mock_job.instrument = Mock()
        mock_job.instrument.symbol = "TEST"
        
        # Mock load to raise FileNotFoundError (no existing data)
        mock_job.load.side_effect = FileNotFoundError("No existing data")
        
        # Mock fetch to return new data
        mock_new_data = Mock()
        mock_df = Mock()
        mock_df.shape = (100, 5)
        mock_df.__len__ = Mock(return_value=100)
        mock_new_data.df = mock_df
        mock_new_data.merge.return_value = mock_new_data
        mock_job.fetch.return_value = mock_new_data
        mock_job.persist = Mock()
        
        # Mock pretend_not_a_bot
        with patch.object(downloader, 'pretend_not_a_bot'):
            result = downloader._process_job(mock_job)
        
        # Verify new data was fetched and persisted
        mock_job.fetch.assert_called_once()
        mock_job.persist.assert_called_once()
        assert result == HistoricalDataResult.OK
    
    def test_inheritance_from_base_downloader(self, downloader):
        """Test that UpdatingDownloader inherits from BaseDownloader."""
        from vortex.services.base_downloader import BaseDownloader
        assert isinstance(downloader, BaseDownloader)
        
        # Should have inherited methods
        assert hasattr(downloader, '_create_jobs')
        assert hasattr(downloader, '_schedule_jobs')
        assert hasattr(downloader, '_process_jobs')


class TestUpdatingDownloaderEdgeCases:
    """Test edge cases for UpdatingDownloader."""
    
    @pytest.fixture
    def mock_storage(self):
        """Create mock data storage."""
        return Mock()
    
    @pytest.fixture
    def mock_provider(self):
        """Create mock data provider."""
        return Mock()
    
    @pytest.fixture
    def downloader(self, mock_storage, mock_provider):
        """Create UpdatingDownloader instance."""
        return UpdatingDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider
        )
    
    def test_random_sleep_configuration_edge_cases(self):
        """Test various edge cases for random sleep configuration."""
        mock_storage = Mock()
        mock_provider = Mock()
        
        # Test None value
        downloader = UpdatingDownloader(mock_storage, mock_provider, random_sleep_in_sec=None)
        assert downloader.random_sleep_in_sec is None
        
        # Test valid positive value
        downloader = UpdatingDownloader(mock_storage, mock_provider, random_sleep_in_sec=15)
        assert downloader.random_sleep_in_sec == 15
        
        # Test that zero becomes None
        downloader = UpdatingDownloader(mock_storage, mock_provider, random_sleep_in_sec=0)
        assert downloader.random_sleep_in_sec is None
    
    def test_process_job_existing_data_needs_more_coverage(self, downloader):
        """Test processing job when existing data needs more coverage."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.start_date = datetime(2023, 1, 1)
        mock_job.end_date = datetime(2023, 12, 31)
        mock_job.__str__ = Mock(return_value="Test Job")
        mock_job.instrument = Mock()
        mock_job.instrument.symbol = "TEST"
        
        # Create mock existing download that needs more data
        mock_existing = Mock()
        mock_existing.is_data_coverage_acceptable.return_value = False
        mock_existing.df.shape = (50, 5)
        mock_existing.metadata.last_row_date = datetime(2023, 6, 1)
        mock_existing.metadata.start_date = datetime(2023, 1, 15)
        mock_job.load.return_value = mock_existing
        
        # Mock fetch to return new data
        mock_new_data = Mock()
        mock_df = Mock()
        mock_df.__len__ = Mock(return_value=75)
        mock_new_data.df = mock_df
        mock_merged_data = Mock()
        mock_new_data.merge.return_value = mock_merged_data
        mock_job.fetch.return_value = mock_new_data
        mock_job.persist = Mock()
        
        # Mock pretend_not_a_bot
        with patch.object(downloader, 'pretend_not_a_bot'):
            result = downloader._process_job(mock_job)
        
        # Verify that job dates were adjusted (lines 43-55)
        # Should adjust start date based on existing data
        # And fetch new data to merge
        mock_job.fetch.assert_called_once()
        mock_new_data.merge.assert_called_once_with(mock_existing)
        mock_job.persist.assert_called_once_with(mock_merged_data)
        assert result == HistoricalDataResult.OK
    
    def test_process_job_existing_data_gap_before_start(self, downloader):
        """Test processing job when there's a gap before existing data start."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.start_date = datetime(2022, 1, 1)
        mock_job.end_date = datetime(2022, 12, 31)
        mock_job.__str__ = Mock(return_value="Test Job")
        mock_job.instrument = Mock()
        mock_job.instrument.symbol = "TEST"
        
        # Create mock existing download with later start date
        mock_existing = Mock()
        mock_existing.is_data_coverage_acceptable.return_value = False
        mock_existing.df.shape = (50, 5)
        mock_existing.metadata.last_row_date = datetime(2023, 6, 1)
        mock_existing.metadata.start_date = datetime(2023, 1, 15)  # Later than job.end_date
        mock_job.load.return_value = mock_existing
        
        # Mock fetch to return new data
        mock_new_data = Mock()
        mock_df = Mock()
        mock_df.__len__ = Mock(return_value=75)
        mock_new_data.df = mock_df
        mock_merged_data = Mock()
        mock_new_data.merge.return_value = mock_merged_data
        mock_job.fetch.return_value = mock_new_data
        mock_job.persist = Mock()
        
        # Mock pretend_not_a_bot
        with patch.object(downloader, 'pretend_not_a_bot'):
            result = downloader._process_job(mock_job)
        
        # Should adjust end date to avoid holes (line 54-55)
        mock_job.fetch.assert_called_once()
        mock_job.persist.assert_called_once_with(mock_merged_data)
        assert result == HistoricalDataResult.OK
    
    def test_process_job_fetch_returns_none(self, downloader):
        """Test processing job when fetch returns None."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.start_date = datetime(2023, 1, 1) 
        mock_job.end_date = datetime(2023, 12, 31)
        mock_job.__str__ = Mock(return_value="Test Job")
        mock_job.instrument = Mock()
        mock_job.instrument.symbol = "TEST"
        
        # Mock load to raise FileNotFoundError
        mock_job.load.side_effect = FileNotFoundError("No existing data")
        
        # Mock fetch to return None (line 63-64)
        mock_job.fetch.return_value = None
        
        # Mock pretend_not_a_bot
        with patch.object(downloader, 'pretend_not_a_bot'):
            result = downloader._process_job(mock_job)
        
        # Should return NONE when fetch returns None
        assert result == HistoricalDataResult.NONE
        mock_job.fetch.assert_called_once()
        # Should not call persist when no data
        mock_job.persist.assert_not_called() if hasattr(mock_job, 'persist') else None