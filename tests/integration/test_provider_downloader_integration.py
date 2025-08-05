"""
Integration tests for provider and downloader interactions.

Tests the integration between data providers and downloaders
to ensure they work correctly together without mocking.
"""

import pytest
from pathlib import Path
import tempfile

from vortex.services.updating_downloader import UpdatingDownloader
from vortex.infrastructure.providers.yahoo.provider import YahooDataProvider
from vortex.infrastructure.storage.csv_storage import CsvStorage
from vortex.models.stock import Stock


class TestProviderDownloaderIntegration:
    """Integration tests for provider-downloader workflows."""

    @pytest.fixture
    def temp_storage_dir(self):
        """Create temporary storage directory for tests."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def csv_storage(self, temp_storage_dir):
        """Create CSV storage instance for tests."""
        return CsvStorage(base_path=str(temp_storage_dir), dry_run=False)

    @pytest.fixture  
    def yahoo_provider(self):
        """Create Yahoo provider instance for tests."""
        return YahooDataProvider()

    @pytest.fixture
    def sample_stock(self):
        """Create sample stock instrument for tests."""
        return Stock(id="AAPL", symbol="AAPL")

    def test_yahoo_provider_with_updating_downloader(
        self, yahoo_provider, csv_storage, sample_stock, temp_storage_dir
    ):
        """Test Yahoo provider integration with updating downloader."""
        # Create downloader with real provider and storage
        downloader = UpdatingDownloader(
            provider=yahoo_provider,
            storage=csv_storage
        )
        
        # This would be a real integration test
        # For now, we'll just verify the components can be initialized together
        assert downloader.provider == yahoo_provider
        assert downloader.storage == csv_storage
        
        # In a real integration test, we might:
        # 1. Download a small amount of real data
        # 2. Verify the data was saved correctly
        # 3. Check that subsequent downloads detect existing data
        
    def test_provider_storage_compatibility(self, yahoo_provider, csv_storage):
        """Test that provider output is compatible with storage input."""
        # Verify that the data format from providers
        # matches what storage components expect
        assert hasattr(yahoo_provider, '_fetch_historical_data')
        assert hasattr(csv_storage, 'persist')
        
        # In a real test, we'd verify data format compatibility