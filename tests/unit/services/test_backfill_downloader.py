"""Tests for the BackfillDownloader class."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from vortex.services.backfill_downloader import BackfillDownloader
from vortex.services.download_job import DownloadJob
from vortex.infrastructure.providers.base import HistoricalDataResult


class TestBackfillDownloader:
    """Test the BackfillDownloader class."""
    
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
        """Create BackfillDownloader instance."""
        return BackfillDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider
        )
    
    @pytest.fixture
    def downloader_with_backup(self, mock_storage, mock_provider, mock_backup_storage):
        """Create BackfillDownloader with backup storage."""
        return BackfillDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            backup_data_storage=mock_backup_storage,
            force_backup=True
        )
    
    def test_downloader_initialization_basic(self, mock_storage, mock_provider):
        """Test basic BackfillDownloader initialization."""
        downloader = BackfillDownloader(mock_storage, mock_provider)
        
        assert downloader.data_storage == mock_storage
        assert downloader.data_provider == mock_provider
        assert downloader.backup_data_storage is None
        assert downloader.force_backup is False
    
    def test_downloader_initialization_with_backup(self, mock_storage, mock_provider, mock_backup_storage):
        """Test BackfillDownloader initialization with backup storage."""
        downloader = BackfillDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            backup_data_storage=mock_backup_storage,
            force_backup=True
        )
        
        assert downloader.data_storage == mock_storage
        assert downloader.data_provider == mock_provider
        assert downloader.backup_data_storage == mock_backup_storage
        assert downloader.force_backup is True
    
    def test_process_job_successful_fetch(self, downloader):
        """Test processing job with successful data fetch."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.__str__ = Mock(return_value="Test Job")
        
        # Mock successful fetch
        mock_data = Mock()
        mock_data.df.shape = (100, 5)
        mock_job.fetch.return_value = mock_data
        mock_job.persist = Mock()
        
        # Process the job
        result = downloader._process_job(mock_job)
        
        # Verify results
        assert result == HistoricalDataResult.OK
        mock_job.fetch.assert_called_once()
        mock_job.persist.assert_called_once_with(mock_data)
    
    def test_process_job_no_data_returned(self, downloader):
        """Test processing job when fetch returns no data."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.__str__ = Mock(return_value="Test Job")
        
        # Mock fetch returning None/empty data
        mock_job.fetch.return_value = None
        mock_job.persist = Mock()
        
        # Process the job
        result = downloader._process_job(mock_job)
        
        # Verify results
        assert result == HistoricalDataResult.NONE
        mock_job.fetch.assert_called_once()
        mock_job.persist.assert_not_called()
    
    def test_process_job_fetch_returns_false(self, downloader):
        """Test processing job when fetch returns False."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.__str__ = Mock(return_value="Test Job")
        
        # Mock fetch returning False
        mock_job.fetch.return_value = False
        mock_job.persist = Mock()
        
        # Process the job
        result = downloader._process_job(mock_job)
        
        # Verify results
        assert result == HistoricalDataResult.NONE
        mock_job.fetch.assert_called_once()
        mock_job.persist.assert_not_called()
    
    def test_process_job_fetch_returns_empty_string(self, downloader):
        """Test processing job when fetch returns empty string."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.__str__ = Mock(return_value="Test Job")
        
        # Mock fetch returning empty string
        mock_job.fetch.return_value = ""
        mock_job.persist = Mock()
        
        # Process the job
        result = downloader._process_job(mock_job)
        
        # Verify results
        assert result == HistoricalDataResult.NONE
        mock_job.fetch.assert_called_once()
        mock_job.persist.assert_not_called()
    
    def test_inheritance_from_base_downloader(self, downloader):
        """Test that BackfillDownloader inherits from BaseDownloader."""
        from vortex.services.base_downloader import BaseDownloader
        assert isinstance(downloader, BaseDownloader)
        
        # Should have inherited methods
        assert hasattr(downloader, '_create_jobs')
        assert hasattr(downloader, '_schedule_jobs') 
        assert hasattr(downloader, '_process_jobs')
    
    def test_process_job_with_backup_storage(self, downloader_with_backup):
        """Test that backup storage configuration is preserved."""
        # Just verify the configuration is set correctly
        assert downloader_with_backup.backup_data_storage is not None
        assert downloader_with_backup.force_backup is True
    
    def test_backfill_vs_updating_difference(self, mock_storage, mock_provider):
        """Test that BackfillDownloader behaves differently from UpdatingDownloader."""
        from vortex.services.updating_downloader import UpdatingDownloader
        
        backfill = BackfillDownloader(mock_storage, mock_provider)
        updating = UpdatingDownloader(mock_storage, mock_provider)
        
        # They should be different classes
        assert type(backfill) != type(updating)
        
        # Both should inherit from BaseDownloader
        from vortex.services.base_downloader import BaseDownloader
        assert isinstance(backfill, BaseDownloader)
        assert isinstance(updating, BaseDownloader)


class TestBackfillDownloaderIntegration:
    """Integration tests for BackfillDownloader."""
    
    def test_multiple_job_processing_sequence(self):
        """Test processing multiple jobs in sequence."""
        mock_storage = Mock()
        mock_provider = Mock()
        downloader = BackfillDownloader(mock_storage, mock_provider)
        
        # Create multiple mock jobs
        jobs = []
        for i in range(3):
            mock_job = Mock(spec=DownloadJob)
            mock_job.__str__ = Mock(return_value=f"Job {i}")
            
            # Mock successful fetch for each job
            mock_data = Mock()
            mock_data.df.shape = (50 + i * 10, 5)
            mock_job.fetch.return_value = mock_data
            mock_job.persist = Mock()
            
            jobs.append(mock_job)
        
        # Process each job
        results = []
        for job in jobs:
            result = downloader._process_job(job)
            results.append(result)
        
        # Verify all jobs were processed successfully
        assert all(result == HistoricalDataResult.OK for result in results)
        
        # Verify all jobs had fetch and persist called
        for job in jobs:
            job.fetch.assert_called_once()
            job.persist.assert_called_once()
    
    def test_mixed_success_failure_jobs(self):
        """Test processing jobs with mixed success/failure outcomes."""
        mock_storage = Mock()
        mock_provider = Mock()
        downloader = BackfillDownloader(mock_storage, mock_provider)
        
        # Create jobs with different outcomes
        job_configs = [
            ("Success Job", Mock()),  # Returns data
            ("Failure Job", None),    # Returns None
            ("Empty Job", ""),        # Returns empty string
            ("False Job", False),     # Returns False
            ("Success Job 2", Mock()) # Returns data
        ]
        
        results = []
        for job_name, return_value in job_configs:
            mock_job = Mock(spec=DownloadJob)
            mock_job.__str__ = Mock(return_value=job_name)
            mock_job.fetch.return_value = return_value
            mock_job.persist = Mock()
            
            result = downloader._process_job(mock_job)
            results.append(result)
        
        # Verify expected results
        expected_results = [
            HistoricalDataResult.OK,    # Success Job
            HistoricalDataResult.NONE,  # Failure Job 
            HistoricalDataResult.NONE,  # Empty Job
            HistoricalDataResult.NONE,  # False Job
            HistoricalDataResult.OK,    # Success Job 2
        ]
        
        assert results == expected_results