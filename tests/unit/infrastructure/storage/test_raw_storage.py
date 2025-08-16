"""
Unit tests for RawDataStorage.

Tests raw data trail functionality including raw data storage,
metadata handling, compression settings, and configuration options.
"""

import gzip
import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from vortex.infrastructure.storage.raw_storage import RawDataStorage
from vortex.models.stock import Stock
from vortex.models.future import Future
from vortex.models.forex import Forex
from vortex.models.period import Period


class TestRawDataStorage:
    """Test cases for RawDataStorage functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def stock_instrument(self):
        """Create stock instrument for testing."""
        return Stock(id="AAPL", symbol="AAPL")

    @pytest.fixture
    def future_instrument(self):
        """Create future instrument for testing."""
        return Future(
            id="GC_Z24",
            futures_code="GC",
            year=2024,
            month_code="Z",
            tick_date=datetime(2024, 8, 1),
            days_count=90
        )

    @pytest.fixture
    def raw_storage_enabled(self, temp_dir):
        """Create enabled raw data storage instance."""
        return RawDataStorage(
            base_dir=temp_dir,
            enabled=True,
            compress=True,
            include_metadata=True
        )

    @pytest.fixture
    def raw_storage_disabled(self, temp_dir):
        """Create disabled raw data storage instance."""
        return RawDataStorage(
            base_dir=temp_dir,
            enabled=False
        )

    @pytest.fixture
    def sample_raw_data(self):
        """Sample raw CSV data from provider."""
        return "Date,Open,High,Low,Close,Volume\n2024-08-16,150.0,152.0,149.0,151.0,1000000\n2024-08-17,151.0,153.0,150.0,152.0,1100000\n"

    @pytest.fixture
    def sample_metadata(self):
        """Sample request metadata."""
        return {
            'data_source': 'yahoo',
            'interval': '1d',
            'start_date': '2024-08-01',
            'end_date': '2024-08-17',
            'response_status': 200
        }

    def test_raw_storage_initialization_enabled(self, temp_dir):
        """Test raw data storage initialization when enabled."""
        storage = RawDataStorage(
            base_dir=temp_dir,
            enabled=True,
            retention_days=30,
            compress=True,
            include_metadata=True
        )
        
        assert storage.enabled is True
        assert storage.retention_days == 30
        assert storage.compress is True
        assert storage.include_metadata is True
        assert storage.base_dir == Path(temp_dir)
        assert storage.raw_dir.exists()

    def test_raw_storage_initialization_disabled(self, temp_dir):
        """Test raw data storage initialization when disabled."""
        storage = RawDataStorage(
            base_dir=temp_dir,
            enabled=False
        )
        
        assert storage.enabled is False
        # When disabled, raw_dir property still exists but directory not created
        assert hasattr(storage, 'raw_dir')
        # The actual directory should not exist on filesystem
        raw_path = Path(temp_dir) / "raw"
        assert not raw_path.exists()

    def test_save_raw_response_enabled_with_compression(self, raw_storage_enabled, stock_instrument, sample_raw_data, sample_metadata):
        """Test saving raw response when raw data storage is enabled with compression."""
        with patch.object(raw_storage_enabled.correlation_manager, 'get_current_id', return_value='test-correlation-123'):
            file_path = raw_storage_enabled.save_raw_response(
                provider="yahoo",
                instrument=stock_instrument,
                raw_data=sample_raw_data,
                request_metadata=sample_metadata
            )
        
        assert file_path is not None
        raw_file = Path(file_path)
        assert raw_file.exists()
        assert raw_file.suffix == '.gz'
        
        # Verify compressed content
        with gzip.open(raw_file, 'rt', encoding='utf-8') as f:
            saved_data = f.read()
        assert saved_data == sample_raw_data
        
        # Verify metadata file exists
        metadata_file = raw_file.with_suffix('.meta.json')
        assert metadata_file.exists()
        
        with open(metadata_file, 'r') as f:
            saved_metadata = json.load(f)
        assert saved_metadata['provider_info']['name'] == "yahoo"
        assert saved_metadata['instrument_info']['symbol'] == "AAPL"
        assert saved_metadata['request_info'] == sample_metadata

    def test_save_raw_response_no_compression(self, temp_dir, stock_instrument, sample_raw_data):
        """Test saving raw response without compression."""
        storage = RawDataStorage(
            base_dir=temp_dir,
            enabled=True,
            compress=False,
            include_metadata=True
        )
        
        with patch.object(storage.correlation_manager, 'get_current_id', return_value='test-correlation-456'):
            file_path = storage.save_raw_response(
                provider="barchart",
                instrument=stock_instrument,
                raw_data=sample_raw_data
            )
        
        assert file_path is not None
        raw_file = Path(file_path)
        assert raw_file.exists()
        assert raw_file.suffix == '.csv'
        
        # Verify uncompressed content
        with open(raw_file, 'r', encoding='utf-8') as f:
            saved_data = f.read()
        assert saved_data == sample_raw_data

    def test_save_raw_response_no_metadata(self, temp_dir, stock_instrument, sample_raw_data):
        """Test saving raw response without metadata."""
        storage = RawDataStorage(
            base_dir=temp_dir,
            enabled=True,
            compress=True,
            include_metadata=False
        )
        
        file_path = storage.save_raw_response(
            provider="yahoo",
            instrument=stock_instrument,
            raw_data=sample_raw_data
        )
        
        assert file_path is not None
        raw_file = Path(file_path)
        assert raw_file.exists()
        
        # Verify no metadata file created
        metadata_file = raw_file.with_suffix('.meta.json')
        assert not metadata_file.exists()

    def test_save_raw_response_disabled(self, raw_storage_disabled, stock_instrument, sample_raw_data):
        """Test saving raw response when raw data storage is disabled."""
        file_path = raw_storage_disabled.save_raw_response(
            provider="yahoo",
            instrument=stock_instrument,
            raw_data=sample_raw_data
        )
        
        assert file_path is None
        # No files should be created
        assert not any(raw_storage_disabled.base_dir.rglob("*"))

    def test_generate_raw_file_path_stock(self, raw_storage_enabled, stock_instrument):
        """Test raw data file path generation for stock instruments."""
        with patch('vortex.infrastructure.storage.raw_storage.datetime') as mock_datetime:
            mock_now = datetime(2024, 8, 16, 14, 30, 45, 123000)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.strftime
            
            file_path = raw_storage_enabled._generate_raw_file_path("yahoo", stock_instrument)
            
            expected_path = (raw_storage_enabled.raw_dir / 
                           "yahoo" / "2024" / "08" / "stock" / "AAPL_20240816_143045_123.csv.gz")
            assert file_path == expected_path

    def test_generate_raw_file_path_future(self, raw_storage_enabled, future_instrument):
        """Test raw data file path generation for future instruments."""
        with patch('vortex.infrastructure.storage.raw_storage.datetime') as mock_datetime:
            mock_now = datetime(2024, 8, 16, 14, 30, 45, 123000)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.strftime
            
            file_path = raw_storage_enabled._generate_raw_file_path("barchart", future_instrument)
            
            expected_path = (raw_storage_enabled.raw_dir / 
                           "barchart" / "2024" / "08" / "future" / "GCZ24_20240816_143045_123.csv.gz")
            assert file_path == expected_path

    def test_generate_raw_file_path_uncompressed(self, temp_dir, stock_instrument):
        """Test raw data file path generation without compression."""
        storage = RawDataStorage(
            base_dir=temp_dir,
            enabled=True,
            compress=False
        )
        
        with patch('vortex.infrastructure.storage.raw_storage.datetime') as mock_datetime:
            mock_now = datetime(2024, 8, 16, 14, 30, 45, 123000)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.strftime
            
            file_path = storage._generate_raw_file_path("yahoo", stock_instrument)
            
            expected_path = (storage.raw_dir / 
                           "yahoo" / "2024" / "08" / "stock" / "AAPL_20240816_143045_123.csv")
            assert file_path == expected_path

    def test_create_raw_metadata(self, raw_storage_enabled, stock_instrument, sample_metadata):
        """Test raw data metadata creation."""
        with patch.object(raw_storage_enabled.correlation_manager, 'get_current_id', return_value='test-correlation-789'):
            metadata = raw_storage_enabled._create_raw_metadata(
                provider="yahoo",
                instrument=stock_instrument,
                raw_data="test,data\n1,2\n",
                request_metadata=sample_metadata,
                correlation_id="test-correlation-789"
            )
        
        assert metadata['provider_info']['name'] == "yahoo"
        assert metadata['instrument_info']['symbol'] == "AAPL"
        assert metadata['instrument_info']['type'] == "stock"
        assert metadata['raw_info']['correlation_id'] == "test-correlation-789"
        assert metadata['request_info'] == sample_metadata
        assert 'created_at' in metadata['raw_info']
        assert 'raw_size_bytes' in metadata['data_info']

    def test_save_raw_response_error_handling(self, temp_dir, stock_instrument, sample_raw_data):
        """Test error handling during raw data storage operations."""
        storage = RawDataStorage(
            base_dir=temp_dir,
            enabled=True
        )
        
        # Mock gzip.open to raise an exception
        with patch('vortex.infrastructure.storage.raw_storage.gzip.open', side_effect=IOError("Simulated file error")):
            with patch('vortex.infrastructure.storage.raw_storage.logger') as mock_logger:
                file_path = storage.save_raw_response(
                    provider="yahoo",
                    instrument=stock_instrument,
                    raw_data=sample_raw_data
                )
        
        assert file_path is None
        mock_logger.error.assert_called_once()

    def test_directory_structure_creation(self, raw_storage_enabled, stock_instrument, sample_raw_data):
        """Test that directory structure is created correctly."""
        with patch('vortex.infrastructure.storage.raw_storage.datetime') as mock_datetime:
            mock_now = datetime(2024, 8, 16, 14, 30, 45, 123000)
            mock_datetime.now.return_value = mock_now
            mock_datetime.strftime = datetime.strftime
            
            raw_storage_enabled.save_raw_response(
                provider="yahoo",
                instrument=stock_instrument,
                raw_data=sample_raw_data
            )
        
        # Verify directory structure
        expected_dir = raw_storage_enabled.raw_dir / "yahoo" / "2024" / "08" / "stock"
        assert expected_dir.exists()
        assert expected_dir.is_dir()

    def test_different_providers_separate_directories(self, raw_storage_enabled, stock_instrument, sample_raw_data):
        """Test that different providers create separate directories."""
        providers = ["yahoo", "barchart", "ibkr"]
        
        for provider in providers:
            raw_storage_enabled.save_raw_response(
                provider=provider,
                instrument=stock_instrument,
                raw_data=sample_raw_data
            )
        
        # Verify each provider has its own directory
        for provider in providers:
            provider_dir = raw_storage_enabled.raw_dir / provider
            assert provider_dir.exists()

    def test_correlation_id_injection(self, raw_storage_enabled, stock_instrument, sample_raw_data):
        """Test correlation ID is properly injected in metadata."""
        test_correlation_id = "test-correlation-custom-id"
        
        with patch.object(raw_storage_enabled.correlation_manager, 'get_current_id', return_value='default-id'):
            file_path = raw_storage_enabled.save_raw_response(
                provider="yahoo",
                instrument=stock_instrument,
                raw_data=sample_raw_data,
                correlation_id=test_correlation_id
            )
        
        # Read metadata and verify custom correlation ID was used
        metadata_file = Path(file_path).with_suffix('.meta.json')
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata['raw_info']['correlation_id'] == test_correlation_id

    @pytest.mark.parametrize("compress,expected_extension", [
        (True, ".csv.gz"),
        (False, ".csv")
    ])
    def test_file_extension_based_on_compression(self, temp_dir, stock_instrument, sample_raw_data, compress, expected_extension):
        """Test file extension changes based on compression setting."""
        storage = RawDataStorage(
            base_dir=temp_dir,
            enabled=True,
            compress=compress,
            include_metadata=False
        )
        
        file_path = storage.save_raw_response(
            provider="yahoo",
            instrument=stock_instrument,
            raw_data=sample_raw_data
        )
        
        assert file_path is not None
        path = Path(file_path)
        if expected_extension == ".csv.gz":
            assert path.suffixes == [".csv", ".gz"]
        else:
            assert path.suffix == expected_extension

    def test_multiple_instruments_same_provider(self, raw_storage_enabled, sample_raw_data):
        """Test saving data for multiple instruments from same provider."""
        instruments = [
            Stock(id="AAPL", symbol="AAPL"),
            Stock(id="GOOGL", symbol="GOOGL"),
            Future(id="GC_Z24", futures_code="GC", year=2024, month_code="Z", tick_date=datetime(2024, 8, 1), days_count=90)
        ]
        
        file_paths = []
        for instrument in instruments:
            file_path = raw_storage_enabled.save_raw_response(
                provider="yahoo",
                instrument=instrument,
                raw_data=sample_raw_data
            )
            file_paths.append(file_path)
        
        # All should be saved successfully
        assert all(path is not None for path in file_paths)
        assert all(Path(path).exists() for path in file_paths)
        
        # Verify different files for different symbols
        assert len(set(file_paths)) == len(instruments)

    def test_timestamp_uniqueness(self, raw_storage_enabled, stock_instrument, sample_raw_data):
        """Test that timestamps make filenames unique."""
        import time
        file_paths = []
        
        # Save multiple times with tiny delay to ensure different timestamps
        for i in range(3):
            file_path = raw_storage_enabled.save_raw_response(
                provider="yahoo",
                instrument=stock_instrument,
                raw_data=sample_raw_data
            )
            file_paths.append(file_path)
            if i < 2:  # Don't sleep after last iteration
                time.sleep(0.001)  # 1ms delay to ensure different timestamps
        
        # All should be unique files
        assert len(set(file_paths)) == 3
        assert all(Path(path).exists() for path in file_paths)

    @patch('vortex.infrastructure.storage.raw_storage.logger')
    def test_logging_on_successful_save(self, mock_logger, raw_storage_enabled, stock_instrument, sample_raw_data):
        """Test that successful saves are logged appropriately."""
        raw_storage_enabled.save_raw_response(
            provider="yahoo",
            instrument=stock_instrument,
            raw_data=sample_raw_data
        )
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Raw data saved for yahoo" in call_args[0][0]

    @patch('vortex.infrastructure.storage.raw_storage.logger')
    def test_logging_on_error(self, mock_logger, temp_dir, stock_instrument, sample_raw_data):
        """Test that errors during save are logged appropriately."""
        storage = RawDataStorage(
            base_dir=temp_dir,
            enabled=True
        )
        
        # Mock the file operations to trigger an error during save
        with patch('vortex.infrastructure.storage.raw_storage.gzip.open', side_effect=IOError("Simulated save error")):
            file_path = storage.save_raw_response(
                provider="yahoo",
                instrument=stock_instrument,
                raw_data=sample_raw_data
            )
        
        assert file_path is None
        mock_logger.error.assert_called_once()

    def test_metadata_content_structure(self, raw_storage_enabled, future_instrument, sample_raw_data, sample_metadata):
        """Test the structure and content of saved metadata."""
        test_correlation_id = "test-correlation-metadata"
        
        with patch('vortex.infrastructure.storage.raw_storage.datetime') as mock_datetime:
            mock_now = datetime(2024, 8, 16, 14, 30, 45)
            mock_datetime.now.return_value = mock_now
            
            file_path = raw_storage_enabled.save_raw_response(
                provider="barchart",
                instrument=future_instrument,
                raw_data=sample_raw_data,
                request_metadata=sample_metadata,
                correlation_id=test_correlation_id
            )
        
        # Read and verify metadata structure
        metadata_file = Path(file_path).with_suffix('.meta.json')
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Verify required metadata sections
        required_sections = ['raw_info', 'provider_info', 'instrument_info', 'request_info', 'data_info']
        for section in required_sections:
            assert section in metadata
        
        assert metadata['provider_info']['name'] == "barchart"
        assert metadata['instrument_info']['symbol'] == "GCZ24"
        assert metadata['instrument_info']['type'] == "future"
        assert metadata['raw_info']['correlation_id'] == test_correlation_id
        assert metadata['data_info']['raw_size_bytes'] == len(sample_raw_data.encode('utf-8'))
        assert metadata['request_info'] == sample_metadata

    def test_forex_instrument_handling(self, raw_storage_enabled, sample_raw_data):
        """Test handling of forex instruments in raw data storage."""
        forex_instrument = Forex(id="EURUSD", symbol="EURUSD")
        
        file_path = raw_storage_enabled.save_raw_response(
            provider="ibkr",
            instrument=forex_instrument,
            raw_data=sample_raw_data
        )
        
        assert file_path is not None
        raw_file = Path(file_path)
        assert "forex" in str(raw_file)
        assert "EURUSD" in str(raw_file)

    def test_raw_storage_with_none_correlation_manager(self, temp_dir, stock_instrument, sample_raw_data):
        """Test raw data storage behavior when correlation manager returns None."""
        storage = RawDataStorage(base_dir=temp_dir, enabled=True)
        
        with patch.object(storage.correlation_manager, 'get_current_id', return_value=None):
            file_path = storage.save_raw_response(
                provider="yahoo",
                instrument=stock_instrument,
                raw_data=sample_raw_data
            )
        
        assert file_path is not None
        
        # Verify metadata handles None correlation ID
        metadata_file = Path(file_path).with_suffix('.meta.json')
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        assert metadata['raw_info']['correlation_id'] is None