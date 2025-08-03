import os
import pytest
from vortex.data_providers.bc_data_provider import BarchartDataProvider
from vortex.data_storage.csv_storage import CsvStorage
from vortex.data_storage.parquet_storage import ParquetStorage
from vortex.downloaders.updating_downloader import UpdatingDownloader
from vortex.initialization.session_config import OsEnvironSessionConfig


@pytest.fixture(autouse=True)
def download_dir(tmp_path):
    download_dir = tmp_path / "prices"
    download_dir.mkdir()
    return download_dir.absolute()


def create_barchart_downloader(config: OsEnvironSessionConfig) -> UpdatingDownloader:
    """Create a barchart downloader for testing."""
    data_storage = CsvStorage(config.download_directory, config.dry_run)
    backup_data_storage = ParquetStorage(config.download_directory, config.dry_run) if config.backup_data else None
    data_provider = BarchartDataProvider(
        username=config.username,
        password=config.password,
        daily_download_limit=config.daily_download_limit
    )
    return UpdatingDownloader(
        data_storage, 
        data_provider, 
        backup_data_storage,
        force_backup=config.force_backup, 
        random_sleep_in_sec=config.random_sleep_in_sec,
        dry_run=config.dry_run
    )


class TestDownloader:

    def test_no_credentials(self, download_dir):
        with pytest.raises(Exception):
            config = OsEnvironSessionConfig()
            config.download_directory = str(download_dir)
            downloader = create_barchart_downloader(config)

    def test_bad_credentials(self, download_dir):
        with pytest.raises(Exception):
            config = OsEnvironSessionConfig()
            config.username = "user@domain.com"
            config.password = "fake_password"
            config.download_directory = str(download_dir)
            downloader = create_barchart_downloader(config)

    def test_good_credentials(self, download_dir):
        # This test is skipped if no valid credentials are provided
        if not (os.environ.get('BCU_USERNAME') and os.environ.get('BCU_PASSWORD')):
            pytest.skip("Skipping test - no valid credentials in environment")
            
        config = OsEnvironSessionConfig()
        config.username = os.environ.get('BCU_USERNAME')
        config.password = os.environ.get('BCU_PASSWORD')
        config.download_directory = str(download_dir)
        config.dry_run = True  # Always dry run in tests
        config.daily_download_limit = 2
        
        # This should not raise an exception with valid credentials
        downloader = create_barchart_downloader(config)
        assert downloader is not None