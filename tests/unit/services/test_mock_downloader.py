"""Tests for the MockDownloader class."""

import pytest
from datetime import datetime
from unittest.mock import Mock

from vortex.services.mock_downloader import MockDownloader
from vortex.services.download_job import DownloadJob
from vortex.infrastructure.providers.base import HistoricalDataResult


class TestMockDownloader:
    """Test the MockDownloader class."""
    
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
        """Create MockDownloader instance."""
        return MockDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider
        )
    
    @pytest.fixture
    def downloader_with_backup(self, mock_storage, mock_provider, mock_backup_storage):
        """Create MockDownloader with backup storage."""
        return MockDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            backup_data_storage=mock_backup_storage,
            force_backup=True
        )
    
    def test_downloader_initialization_basic(self, mock_storage, mock_provider):
        """Test basic MockDownloader initialization."""
        downloader = MockDownloader(mock_storage, mock_provider)
        
        assert downloader.data_storage == mock_storage
        assert downloader.data_provider == mock_provider
        assert downloader.backup_data_storage is None
        assert downloader.force_backup is False
    
    def test_downloader_initialization_with_backup(self, mock_storage, mock_provider, mock_backup_storage):
        """Test MockDownloader initialization with backup storage."""
        downloader = MockDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            backup_data_storage=mock_backup_storage,
            force_backup=True
        )
        
        assert downloader.data_storage == mock_storage
        assert downloader.data_provider == mock_provider
        assert downloader.backup_data_storage == mock_backup_storage
        assert downloader.force_backup is True
    
    def test_process_job_always_returns_ok(self, downloader):
        """Test that MockDownloader always returns OK result."""
        # Create mock download job
        mock_job = Mock(spec=DownloadJob)
        mock_job.__str__ = Mock(return_value="Test Mock Job")
        
        # Process the job
        result = downloader._process_job(mock_job)
        
        # MockDownloader should always return OK without doing any real work
        assert result == HistoricalDataResult.OK
    
    def test_process_job_multiple_calls(self, downloader):
        """Test that MockDownloader consistently returns OK for multiple jobs."""
        results = []
        
        for i in range(5):
            mock_job = Mock(spec=DownloadJob)
            mock_job.__str__ = Mock(return_value=f"Mock Job {i}")
            
            result = downloader._process_job(mock_job)
            results.append(result)
        
        # All results should be OK
        assert all(result == HistoricalDataResult.OK for result in results)
        assert len(results) == 5
    
    def test_process_job_doesnt_call_provider(self, downloader):
        """Test that MockDownloader doesn't call data provider methods."""
        mock_job = Mock(spec=DownloadJob)
        mock_job.__str__ = Mock(return_value="Test Job")
        
        # Process the job
        result = downloader._process_job(mock_job)
        
        # Should not call any methods on the data provider since it's a mock
        assert result == HistoricalDataResult.OK
        # The provider shouldn't have any calls made to it
        downloader.data_provider.assert_not_called()
    
    def test_process_job_doesnt_call_storage(self, downloader):
        """Test that MockDownloader doesn't call storage methods."""
        mock_job = Mock(spec=DownloadJob)
        mock_job.__str__ = Mock(return_value="Test Job")
        
        # Process the job
        result = downloader._process_job(mock_job)
        
        # Should not call any methods on the storage since it's a mock
        assert result == HistoricalDataResult.OK
        # The storage shouldn't have any calls made to it
        downloader.data_storage.assert_not_called()
    
    def test_inheritance_from_base_downloader(self, downloader):
        """Test that MockDownloader inherits from BaseDownloader."""
        from vortex.services.base_downloader import BaseDownloader
        assert isinstance(downloader, BaseDownloader)
        
        # Should have inherited methods
        assert hasattr(downloader, '_create_jobs')
        assert hasattr(downloader, '_schedule_jobs')
        assert hasattr(downloader, '_process_jobs')
    
    def test_mock_downloader_vs_other_downloaders(self, mock_storage, mock_provider):
        """Test that MockDownloader is different from other downloader types."""
        from vortex.services.updating_downloader import UpdatingDownloader
        from vortex.services.backfill_downloader import BackfillDownloader
        
        mock_downloader = MockDownloader(mock_storage, mock_provider)
        updating_downloader = UpdatingDownloader(mock_storage, mock_provider)
        backfill_downloader = BackfillDownloader(mock_storage, mock_provider)
        
        # They should be different classes
        assert type(mock_downloader) != type(updating_downloader)
        assert type(mock_downloader) != type(backfill_downloader)
        
        # But all should inherit from BaseDownloader
        from vortex.services.base_downloader import BaseDownloader
        assert isinstance(mock_downloader, BaseDownloader)
        assert isinstance(updating_downloader, BaseDownloader)
        assert isinstance(backfill_downloader, BaseDownloader)
    
    def test_process_job_with_different_job_types(self, downloader):
        """Test MockDownloader with different job configurations."""
        # Different job scenarios should all return OK
        job_scenarios = [
            {"name": "Simple Job", "start": datetime(2023, 1, 1), "end": datetime(2023, 12, 31)},
            {"name": "Single Day Job", "start": datetime(2023, 6, 15), "end": datetime(2023, 6, 15)},
            {"name": "Year Span Job", "start": datetime(2020, 1, 1), "end": datetime(2023, 12, 31)},
        ]
        
        results = []
        for scenario in job_scenarios:
            mock_job = Mock(spec=DownloadJob)
            mock_job.__str__ = Mock(return_value=scenario["name"])
            mock_job.start_date = scenario["start"]
            mock_job.end_date = scenario["end"]
            
            result = downloader._process_job(mock_job)
            results.append(result)
        
        # All should return OK regardless of job configuration
        assert all(result == HistoricalDataResult.OK for result in results)
        assert len(results) == 3


class TestMockDownloaderIntegration:
    """Integration tests for MockDownloader."""
    
    def test_mock_downloader_in_test_workflows(self):
        """Test MockDownloader can be used in test workflows."""
        mock_storage = Mock()
        mock_provider = Mock()
        downloader = MockDownloader(mock_storage, mock_provider)
        
        # Simulate a test workflow with multiple jobs
        job_results = []
        for i in range(10):
            mock_job = Mock(spec=DownloadJob)
            mock_job.__str__ = Mock(return_value=f"Test Job {i}")
            
            result = downloader._process_job(mock_job)
            job_results.append(result)
        
        # All jobs should succeed in mock mode
        assert len(job_results) == 10
        assert all(result == HistoricalDataResult.OK for result in job_results)
        
        # No actual work should have been done
        mock_storage.assert_not_called()
        mock_provider.assert_not_called()
    
    def test_mock_downloader_performance_testing(self):
        """Test MockDownloader for performance testing scenarios."""
        mock_storage = Mock()
        mock_provider = Mock()
        downloader = MockDownloader(mock_storage, mock_provider)
        
        # Large number of jobs should complete quickly since no real work is done
        job_count = 100
        results = []
        
        for i in range(job_count):
            mock_job = Mock(spec=DownloadJob)
            mock_job.__str__ = Mock(return_value=f"Perf Test Job {i}")
            
            result = downloader._process_job(mock_job)
            results.append(result)
        
        # All should succeed
        assert len(results) == job_count
        assert all(result == HistoricalDataResult.OK for result in results)
    
    def test_mock_downloader_with_backup_config(self):
        """Test MockDownloader respects backup configuration even though it doesn't use it."""
        mock_storage = Mock()
        mock_provider = Mock()
        mock_backup = Mock()
        
        downloader = MockDownloader(
            data_storage=mock_storage,
            data_provider=mock_provider,
            backup_data_storage=mock_backup,
            force_backup=True
        )
        
        # Configuration should be preserved
        assert downloader.backup_data_storage == mock_backup
        assert downloader.force_backup is True
        
        # But still returns OK without using backup
        mock_job = Mock(spec=DownloadJob)
        mock_job.__str__ = Mock(return_value="Backup Test Job")
        
        result = downloader._process_job(mock_job)
        assert result == HistoricalDataResult.OK
        
        # No backup operations should occur
        mock_backup.assert_not_called()