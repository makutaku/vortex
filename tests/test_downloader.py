import os
import pytest
from unittest.mock import Mock, patch

from vortex.data_providers.bc_data_provider import BarchartDataProvider
from vortex.data_providers.yf_data_provider import YahooDataProvider
from vortex.data_providers.ib_data_provider import IbkrDataProvider
from vortex.data_storage.csv_storage import CsvStorage  
from vortex.data_storage.parquet_storage import ParquetStorage
from vortex.downloaders.updating_downloader import UpdatingDownloader
from vortex.config import ConfigManager, VortexConfig


@pytest.fixture
def download_dir(temp_dir):
    """Create download directory for tests."""
    download_dir = temp_dir / "prices"
    download_dir.mkdir()
    return download_dir


def create_barchart_downloader(config: VortexConfig, download_dir: str) -> UpdatingDownloader:
    """Create a barchart downloader for testing."""
    data_storage = CsvStorage(download_dir, config.general.dry_run)
    backup_data_storage = ParquetStorage(download_dir, config.general.dry_run) if config.general.backup_enabled else None
    data_provider = BarchartDataProvider(
        username=config.providers.barchart.username,
        password=config.providers.barchart.password,
        daily_download_limit=config.providers.barchart.daily_limit
    )
    return UpdatingDownloader(
        data_storage, 
        data_provider, 
        backup_data_storage,
        force_backup=config.general.force_backup, 
        random_sleep_in_sec=config.general.random_sleep_max,
        dry_run=config.general.dry_run
    )


@pytest.mark.integration
class TestDownloader:
    """Integration tests for downloaders."""

    def test_no_barchart_credentials(self, download_dir):
        """Test downloader creation fails without credentials."""
        config = VortexConfig()
        with pytest.raises(Exception):
            downloader = create_barchart_downloader(config, str(download_dir))

    def test_bad_barchart_credentials(self, download_dir):
        """Test downloader creation fails with bad credentials."""
        config = VortexConfig(
            providers={
                "barchart": {
                    "username": "user@domain.com",
                    "password": "fake_password"
                }
            }
        )
        with pytest.raises(Exception):
            downloader = create_barchart_downloader(config, str(download_dir))

    @pytest.mark.credentials
    @pytest.mark.network
    def test_good_barchart_credentials(self, download_dir, skip_if_no_credentials):
        """Test downloader creation with valid credentials."""
        username = os.environ.get('VORTEX_BARCHART_USERNAME') or os.environ.get('BCU_USERNAME')
        password = os.environ.get('VORTEX_BARCHART_PASSWORD') or os.environ.get('BCU_PASSWORD')
        
        if not (username and password):
            pytest.skip("No valid credentials in environment")
            
        config = VortexConfig(
            general={"dry_run": True},  # Always dry run in tests
            providers={
                "barchart": {
                    "username": username,
                    "password": password,
                    "daily_limit": 2
                }
            }
        )
        
        # This should not raise an exception with valid credentials
        downloader = create_barchart_downloader(config, str(download_dir))
        assert downloader is not None
        assert downloader.dry_run is True


@pytest.mark.unit
class TestDataProviders:
    """Unit tests for data providers."""
    
    def test_yahoo_provider_creation(self):
        """Test Yahoo provider can be created without credentials."""
        provider = YahooDataProvider()
        assert provider is not None
    
    def test_barchart_provider_creation(self):
        """Test Barchart provider creation with credentials."""
        provider = BarchartDataProvider(
            username="test@example.com",
            password="testpass",
            daily_download_limit=100
        )
        assert provider is not None
        assert provider.username == "test@example.com"
        assert provider.daily_download_limit == 100
    
    def test_ibkr_provider_creation(self):
        """Test IBKR provider creation with connection details."""
        provider = IbkrDataProvider(
            ipaddress="localhost",
            port="7497"
        )
        assert provider is not None


@pytest.mark.unit  
class TestDataStorage:
    """Unit tests for data storage."""
    
    def test_csv_storage_creation(self, download_dir):
        """Test CSV storage creation."""
        storage = CsvStorage(str(download_dir), dry_run=True)
        assert storage is not None
        assert storage.dry_run is True
    
    def test_parquet_storage_creation(self, download_dir):
        """Test Parquet storage creation."""
        storage = ParquetStorage(str(download_dir), dry_run=True)
        assert storage is not None
        assert storage.dry_run is True


@pytest.mark.unit
class TestUpdatingDownloader:
    """Unit tests for UpdatingDownloader."""
    
    def test_downloader_creation_with_mocks(self, mock_data_provider, mock_storage):
        """Test downloader creation with mock dependencies."""
        downloader = UpdatingDownloader(
            data_storage=mock_storage,
            data_provider=mock_data_provider,
            backup_data_storage=None,
            force_backup=False,
            random_sleep_in_sec=1,
            dry_run=True
        )
        
        assert downloader is not None
        assert downloader.dry_run is True
        assert downloader.force_backup is False