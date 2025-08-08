"""
Unit tests for DownloadJob class.

Tests download job functionality including validation, data loading, persistence,
and fetching operations.
"""

from datetime import datetime, date
from unittest.mock import MagicMock, Mock, patch
import pandas as pd
import pytest

from vortex.services.download_job import DownloadJob
from vortex.models.instrument import Instrument
from vortex.models.period import Period
from vortex.models.price_series import PriceSeries
from vortex.models.metadata import Metadata
from vortex.infrastructure.providers.base import DataProvider
from vortex.infrastructure.storage.data_storage import DataStorage


class TestDownloadJob:
    """Test cases for DownloadJob class."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock data provider."""
        provider = Mock(spec=DataProvider)
        provider.get_name.return_value = "test_provider"
        return provider

    @pytest.fixture
    def mock_storage(self):
        """Create a mock data storage."""
        return Mock(spec=DataStorage)

    @pytest.fixture
    def mock_backup_storage(self):
        """Create a mock backup data storage."""
        return Mock(spec=DataStorage)

    @pytest.fixture
    def mock_instrument(self):
        """Create a mock instrument."""
        instrument = Mock(spec=Instrument)
        instrument.get_symbol.return_value = "AAPL"
        return instrument

    @pytest.fixture
    def mock_period(self):
        """Create a mock period."""
        return Mock(spec=Period)

    @pytest.fixture
    def sample_dates(self):
        """Create sample start and end dates."""
        return datetime(2024, 1, 1), datetime(2024, 1, 31)

    @pytest.fixture
    def download_job(self, mock_provider, mock_storage, mock_instrument, mock_period, sample_dates):
        """Create a basic download job for testing."""
        start_date, end_date = sample_dates
        return DownloadJob(
            data_provider=mock_provider,
            data_storage=mock_storage,
            instrument=mock_instrument,
            period=mock_period,
            start_date=start_date,
            end_date=end_date
        )

    def test_init_basic(self, download_job, mock_provider, mock_storage, mock_instrument, mock_period, sample_dates):
        """Test basic initialization of DownloadJob."""
        start_date, end_date = sample_dates
        
        assert download_job.data_provider is mock_provider
        assert download_job.data_storage is mock_storage
        assert download_job.instrument is mock_instrument
        assert download_job.period is mock_period
        assert download_job.start_date == start_date
        assert download_job.end_date == end_date
        assert download_job.backup_data_storage is None

    def test_init_with_backup_storage(self, mock_provider, mock_storage, mock_backup_storage, 
                                     mock_instrument, mock_period, sample_dates):
        """Test initialization with backup storage."""
        start_date, end_date = sample_dates
        
        job = DownloadJob(
            data_provider=mock_provider,
            data_storage=mock_storage,
            instrument=mock_instrument,
            period=mock_period,
            start_date=start_date,
            end_date=end_date,
            backup_data_storage=mock_backup_storage
        )
        
        assert job.backup_data_storage is mock_backup_storage

    def test_post_init_valid_dates(self, download_job):
        """Test __post_init__ with valid date range."""
        # Should not raise an exception
        assert download_job.start_date < download_job.end_date

    def test_post_init_invalid_dates(self, mock_provider, mock_storage, mock_instrument, mock_period):
        """Test __post_init__ with invalid date range."""
        start_date = datetime(2024, 1, 31)
        end_date = datetime(2024, 1, 1)  # Earlier than start_date
        
        with pytest.raises(ValueError, match="start_date must come before end_date"):
            DownloadJob(
                data_provider=mock_provider,
                data_storage=mock_storage,
                instrument=mock_instrument,
                period=mock_period,
                start_date=start_date,
                end_date=end_date
            )

    def test_post_init_equal_dates(self, mock_provider, mock_storage, mock_instrument, mock_period):
        """Test __post_init__ with equal start and end dates (should be allowed)."""
        same_date = datetime(2024, 1, 15)
        
        # Equal dates should NOT raise an exception (only start_date > end_date does)
        job = DownloadJob(
            data_provider=mock_provider,
            data_storage=mock_storage,
            instrument=mock_instrument,
            period=mock_period,
            start_date=same_date,
            end_date=same_date
        )
        
        assert job.start_date == job.end_date

    def test_str_representation(self, download_job):
        """Test string representation of DownloadJob."""
        # Create specific mocks that support __str__
        with patch.object(download_job.instrument, '__str__', return_value="AAPL"), \
             patch.object(download_job.period, '__str__', return_value="1d"):
            
            expected = "AAPL|1d|2024-01-01|2024-01-31"
            result = str(download_job)
            assert result == expected

    def test_load_success(self, download_job, mock_storage):
        """Test successful data loading from primary storage."""
        mock_price_series = Mock(spec=PriceSeries)
        mock_storage.load.return_value = mock_price_series
        
        result = download_job.load()
        
        assert result is mock_price_series
        mock_storage.load.assert_called_once_with(download_job.instrument, download_job.period)

    def test_load_primary_fails_no_backup(self, download_job, mock_storage):
        """Test loading when primary storage fails and no backup is available."""
        mock_storage.load.side_effect = FileNotFoundError("File not found")
        
        with pytest.raises(FileNotFoundError):
            download_job.load()

    def test_load_primary_fails_with_backup_success(self, mock_provider, mock_storage, mock_backup_storage,
                                                   mock_instrument, mock_period, sample_dates):
        """Test loading when primary fails but backup succeeds."""
        start_date, end_date = sample_dates
        job = DownloadJob(
            data_provider=mock_provider,
            data_storage=mock_storage,
            instrument=mock_instrument,
            period=mock_period,
            start_date=start_date,
            end_date=end_date,
            backup_data_storage=mock_backup_storage
        )
        
        # Primary storage fails
        mock_storage.load.side_effect = FileNotFoundError("Primary failed")
        
        # Backup storage succeeds
        mock_price_series = Mock(spec=PriceSeries)
        mock_backup_storage.load.return_value = mock_price_series
        
        result = job.load()
        
        assert result is mock_price_series
        mock_storage.load.assert_called_once_with(mock_instrument, mock_period)
        mock_backup_storage.load.assert_called_once_with(mock_instrument, mock_period)

    def test_load_both_storages_fail(self, mock_provider, mock_storage, mock_backup_storage,
                                   mock_instrument, mock_period, sample_dates):
        """Test loading when both primary and backup storage fail."""
        start_date, end_date = sample_dates
        job = DownloadJob(
            data_provider=mock_provider,
            data_storage=mock_storage,
            instrument=mock_instrument,
            period=mock_period,
            start_date=start_date,
            end_date=end_date,
            backup_data_storage=mock_backup_storage
        )
        
        # Both storages fail
        mock_storage.load.side_effect = FileNotFoundError("Primary failed")
        mock_backup_storage.load.side_effect = FileNotFoundError("Backup failed")
        
        with pytest.raises(FileNotFoundError, match="Backup failed"):
            job.load()

    def test_persist_without_backup(self, download_job, mock_storage):
        """Test persisting data without backup."""
        mock_price_series = Mock(spec=PriceSeries)
        
        download_job.persist(mock_price_series, backup=False)
        
        mock_storage.persist.assert_called_once_with(
            mock_price_series, download_job.instrument, download_job.period
        )

    def test_persist_with_backup_enabled_no_backup_storage(self, download_job, mock_storage):
        """Test persisting with backup enabled but no backup storage available."""
        mock_price_series = Mock(spec=PriceSeries)
        
        download_job.persist(mock_price_series, backup=True)
        
        # Should only call primary storage
        mock_storage.persist.assert_called_once_with(
            mock_price_series, download_job.instrument, download_job.period
        )

    def test_persist_with_backup_enabled_and_backup_storage(self, mock_provider, mock_storage, 
                                                           mock_backup_storage, mock_instrument, 
                                                           mock_period, sample_dates):
        """Test persisting with backup enabled and backup storage available."""
        start_date, end_date = sample_dates
        job = DownloadJob(
            data_provider=mock_provider,
            data_storage=mock_storage,
            instrument=mock_instrument,
            period=mock_period,
            start_date=start_date,
            end_date=end_date,
            backup_data_storage=mock_backup_storage
        )
        
        mock_price_series = Mock(spec=PriceSeries)
        
        job.persist(mock_price_series, backup=True)
        
        # Should call both primary and backup storage
        mock_storage.persist.assert_called_once_with(mock_price_series, mock_instrument, mock_period)
        mock_backup_storage.persist.assert_called_once_with(mock_price_series, mock_instrument, mock_period)

    def test_persist_backup_disabled_with_backup_storage(self, mock_provider, mock_storage, 
                                                        mock_backup_storage, mock_instrument, 
                                                        mock_period, sample_dates):
        """Test persisting with backup disabled even when backup storage is available."""
        start_date, end_date = sample_dates
        job = DownloadJob(
            data_provider=mock_provider,
            data_storage=mock_storage,
            instrument=mock_instrument,
            period=mock_period,
            start_date=start_date,
            end_date=end_date,
            backup_data_storage=mock_backup_storage
        )
        
        mock_price_series = Mock(spec=PriceSeries)
        
        job.persist(mock_price_series, backup=False)
        
        # Should only call primary storage
        mock_storage.persist.assert_called_once_with(mock_price_series, mock_instrument, mock_period)
        mock_backup_storage.persist.assert_not_called()

    @patch('vortex.services.download_job.Metadata')
    def test_fetch_success(self, mock_metadata_class, download_job, mock_provider, mock_instrument):
        """Test successful data fetching."""
        # Setup mock data
        mock_df = pd.DataFrame({'price': [100, 101, 102]})
        mock_provider.fetch_historical_data.return_value = mock_df
        
        mock_metadata = Mock(spec=Metadata)
        mock_metadata_class.create_metadata.return_value = mock_metadata
        
        # Execute fetch
        result = download_job.fetch()
        
        # Verify provider was called with correct parameters
        mock_provider.fetch_historical_data.assert_called_once_with(
            download_job.instrument,
            download_job.period,
            download_job.start_date,
            download_job.end_date
        )
        
        # Verify metadata creation was called with correct parameters
        mock_metadata_class.create_metadata.assert_called_once_with(
            mock_df,
            "test_provider",  # From mock_provider.get_name()
            "AAPL",          # From mock_instrument.get_symbol()
            download_job.period,
            download_job.start_date,
            download_job.end_date
        )
        
        # Verify result is a PriceSeries with correct data
        assert isinstance(result, PriceSeries)
        pd.testing.assert_frame_equal(result.df, mock_df)
        assert result.metadata is mock_metadata

    def test_fetch_provider_failure(self, download_job, mock_provider):
        """Test fetch when provider fails."""
        mock_provider.fetch_historical_data.side_effect = Exception("Provider failed")
        
        with pytest.raises(Exception, match="Provider failed"):
            download_job.fetch()