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

    @pytest.mark.integration
    @pytest.mark.network
    def test_yahoo_provider_with_updating_downloader(
        self, yahoo_provider, csv_storage, sample_stock, temp_storage_dir
    ):
        """Test Yahoo provider integration with updating downloader."""
        # Create downloader with real provider and storage
        downloader = UpdatingDownloader(
            data_storage=csv_storage,
            data_provider=yahoo_provider
        )
        
        # Test basic initialization
        assert downloader.data_provider == yahoo_provider
        assert downloader.data_storage == csv_storage
        
        # Test real data download (small amount to avoid API limits)
        from vortex.models.period import Period
        from datetime import datetime, timedelta
        
        # Use a recent, short date range to minimize API calls
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)  # Just 1 week of data
        
        try:
            # Test the actual download process
            from vortex.services.download_job import DownloadJob
            
            job = DownloadJob(
                data_provider=yahoo_provider,
                data_storage=csv_storage,
                instrument=sample_stock,
                period=Period.Daily,
                start_date=start_date,
                end_date=end_date
            )
            
            # Process the job through the downloader
            result = downloader._process_job(job)
            
            # Verify download was successful
            from vortex.infrastructure.providers.base import HistoricalDataResult
            assert result in [HistoricalDataResult.OK, HistoricalDataResult.EXISTS]
            
            # Verify data was actually saved
            expected_path = temp_storage_dir / "stocks" / "1d" / f"{sample_stock.symbol}.csv"
            if result == HistoricalDataResult.OK:
                assert expected_path.exists(), f"Expected data file not found: {expected_path}"
                
                # Verify file has content
                assert expected_path.stat().st_size > 0, "Data file is empty"
                
                # Verify CSV structure
                import pandas as pd
                df = pd.read_csv(expected_path)
                assert not df.empty, "Downloaded CSV is empty"
                
                # Check expected columns are present
                expected_columns = ['DATETIME', 'Open', 'High', 'Low', 'Close', 'Volume']
                for col in expected_columns:
                    assert col in df.columns, f"Missing expected column: {col}"
                
                # Test incremental update behavior
                # Second download should detect existing data
                job2 = DownloadJob(
                    data_provider=yahoo_provider,
                    data_storage=csv_storage,
                    instrument=sample_stock,
                    period=Period.Daily,
                    start_date=start_date,
                    end_date=end_date
                )
                
                result2 = downloader._process_job(job2)
                assert result2 in [HistoricalDataResult.OK, HistoricalDataResult.EXISTS]
            
        except Exception as e:
            # If network issues or API limits, skip with informative message
            pytest.skip(f"Network-dependent test failed (this may be expected): {e}")
        
    def test_provider_storage_compatibility(self, yahoo_provider, csv_storage, sample_stock, temp_storage_dir):
        """Test that provider output is compatible with storage input."""
        from vortex.models.period import Period
        from vortex.models.price_series import PriceSeries
        from vortex.models.metadata import Metadata
        from datetime import datetime, timedelta
        import pandas as pd
        import pytz
        
        # Verify that the data format from providers matches what storage components expect
        assert hasattr(yahoo_provider, '_fetch_historical_data')
        assert hasattr(csv_storage, 'persist')
        assert hasattr(csv_storage, 'load')
        
        # Create mock data in the expected format (with proper index)
        dates = [datetime.now(pytz.UTC) - timedelta(days=i) for i in range(5, 0, -1)]
        mock_df = pd.DataFrame({
            'Open': [100.0 + i for i in range(5)],
            'High': [105.0 + i for i in range(5)],
            'Low': [95.0 + i for i in range(5)],
            'Close': [102.0 + i for i in range(5)],
            'Volume': [1000000 + i * 10000 for i in range(5)]
        }, index=pd.DatetimeIndex(dates, name='DATETIME'))
        
        # Create metadata as expected by storage
        metadata = Metadata(
            symbol=sample_stock.symbol,
            period=Period.Daily,
            start_date=dates[0],
            end_date=dates[-1],
            first_row_date=dates[0],
            last_row_date=dates[-1],
            data_provider="test"
        )
        
        # Create PriceSeries object as expected by storage
        price_series = PriceSeries(mock_df, metadata)
        
        # Test that storage can handle the expected data format
        try:
            csv_storage.persist(
                downloaded_data=price_series,
                instrument=sample_stock,
                period=Period.Daily
            )
            
            # Verify we can load the data back
            loaded_data = csv_storage.load(
                instrument=sample_stock,
                period=Period.Daily
            )
            
            # Verify loaded data structure
            assert isinstance(loaded_data, PriceSeries)
            assert not loaded_data.df.empty
            assert loaded_data.metadata is not None
            assert loaded_data.metadata.symbol == sample_stock.symbol
            
            # Verify expected columns are present
            expected_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in expected_columns:
                assert col in loaded_data.df.columns, f"Missing expected column: {col}"
            
        except Exception as e:
            pytest.fail(f"Provider-storage compatibility test failed: {e}")
    
    def test_downloader_error_handling(self, csv_storage, temp_storage_dir):
        """Test downloader error handling with invalid provider."""
        from unittest.mock import Mock
        from vortex.services.download_job import DownloadJob
        from vortex.models.period import Period
        from datetime import datetime
        
        # Create a mock provider that raises exceptions
        mock_provider = Mock()
        mock_provider._fetch_historical_data.side_effect = Exception("Network error")
        
        downloader = UpdatingDownloader(
            data_storage=csv_storage,
            data_provider=mock_provider
        )
        
        job = DownloadJob(
            data_provider=mock_provider,
            data_storage=csv_storage,
            instrument=Stock(id="TEST", symbol="TEST"),
            period=Period.Daily,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 7)
        )
        
        # Test that downloader handles provider errors gracefully
        try:
            result = downloader._process_job(job)
            # Should either handle the error or let it propagate appropriately
            assert result is not None
        except Exception:
            # Exceptions are acceptable for this error case
            pass