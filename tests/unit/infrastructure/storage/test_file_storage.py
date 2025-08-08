"""
Unit tests for FileStorage abstract base class.

Tests path generation, metadata operations, and storage functionality.
"""

import os
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import pytest

from vortex.infrastructure.storage.file_storage import FileStorage
from vortex.infrastructure.storage.metadata import Metadata, MetadataHandler
from vortex.models.future import Future
from vortex.models.stock import Stock
from vortex.models.forex import Forex
from vortex.models.period import Period
from vortex.models.price_series import PriceSeries


class ConcreteFileStorage(FileStorage):
    """Concrete implementation of FileStorage for testing."""
    
    def _load(self, file_path) -> pd.DataFrame:
        """Mock implementation for testing."""
        return pd.DataFrame({'price': [100, 101, 102]})
    
    def _persist(self, downloaded_data: pd.DataFrame, file_path: str) -> None:
        """Mock implementation for testing."""
        # Simulate saving to file
        pass


class TestFileStorage:
    """Test cases for FileStorage abstract base class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def file_storage(self, temp_dir):
        """Create FileStorage instance for testing."""
        return ConcreteFileStorage(base_path=temp_dir, dry_run=False)

    @pytest.fixture
    def file_storage_dry_run(self, temp_dir):
        """Create FileStorage instance with dry_run enabled."""
        return ConcreteFileStorage(base_path=temp_dir, dry_run=True)

    @pytest.fixture
    def mock_future(self):
        """Create a mock Future instrument."""
        future = Mock(spec=Future)
        future.id = "GC"
        future.year = 2024
        future.month = 12
        return future

    @pytest.fixture
    def mock_stock(self):
        """Create a mock Stock instrument."""
        stock = Mock(spec=Stock)
        stock.id = "AAPL"
        return stock

    @pytest.fixture
    def mock_forex(self):
        """Create a mock Forex instrument."""
        forex = Mock(spec=Forex)
        forex.id = "EURUSD"
        return forex

    @pytest.fixture
    def mock_period(self):
        """Create a mock Period."""
        period = Mock(spec=Period)
        period.value = "1d"
        return period

    @pytest.fixture
    def sample_price_series(self):
        """Create a sample PriceSeries for testing."""
        df = pd.DataFrame({
            'price': [100, 101, 102],
            'volume': [1000, 1100, 1200]
        })
        metadata = Mock(spec=Metadata)
        return PriceSeries(df, metadata)

    def test_init_basic(self, temp_dir):
        """Test basic initialization of FileStorage."""
        storage = ConcreteFileStorage(base_path=temp_dir, dry_run=False)
        
        assert storage.base_path == temp_dir
        assert storage.dry_run is False

    def test_init_dry_run(self, temp_dir):
        """Test initialization with dry_run enabled."""
        storage = ConcreteFileStorage(base_path=temp_dir, dry_run=True)
        
        assert storage.base_path == temp_dir
        assert storage.dry_run is True

    def test_make_file_path_future(self, file_storage, mock_future, mock_period):
        """Test file path generation for Future instruments."""
        result = file_storage._make_file_path_for_instrument(mock_future, mock_period)
        
        expected_path = f"{file_storage.base_path}/futures/1d/GC/GC_202412"+"00"
        assert result == expected_path

    def test_make_file_path_stock(self, file_storage, mock_stock, mock_period):
        """Test file path generation for Stock instruments."""
        result = file_storage._make_file_path_for_instrument(mock_stock, mock_period)
        
        expected_path = f"{file_storage.base_path}/stocks/1d/AAPL"
        assert result == expected_path

    def test_make_file_path_forex(self, file_storage, mock_forex, mock_period):
        """Test file path generation for Forex instruments."""
        result = file_storage._make_file_path_for_instrument(mock_forex, mock_period)
        
        expected_path = f"{file_storage.base_path}/forex/1d/EURUSD"
        assert result == expected_path

    def test_make_file_path_future_different_month(self, file_storage, mock_period):
        """Test file path generation for Future with different month."""
        future = Mock(spec=Future)
        future.id = "CL"
        future.year = 2025
        future.month = 3
        
        result = file_storage._make_file_path_for_instrument(future, mock_period)
        
        expected_path = f"{file_storage.base_path}/futures/1d/CL/CL_202503"+"00"
        assert result == expected_path

    @patch('vortex.infrastructure.storage.file_storage.create_full_path')
    @patch.object(FileStorage, 'persist_metadata')
    def test_persist_success(self, mock_persist_metadata, mock_create_path, 
                           file_storage, sample_price_series, mock_stock, mock_period):
        """Test successful data persistence."""
        with patch.object(file_storage, '_persist') as mock_persist:
            file_storage.persist(sample_price_series, mock_stock, mock_period)
            
            expected_path = f"{file_storage.base_path}/stocks/1d/AAPL"
            
            # Verify create_full_path was called
            mock_create_path.assert_called_once_with(expected_path)
            
            # Verify _persist was called with DataFrame and path
            mock_persist.assert_called_once_with(sample_price_series.df, expected_path)
            
            # Verify metadata persistence
            mock_persist_metadata.assert_called_once_with(expected_path, sample_price_series.metadata)

    @patch('vortex.infrastructure.storage.file_storage.create_full_path')
    @patch.object(FileStorage, 'persist_metadata')
    def test_persist_with_logging_context(self, mock_persist_metadata, mock_create_path,
                                        file_storage, sample_price_series, mock_future, mock_period):
        """Test that persist uses LoggingContext correctly."""
        with patch.object(file_storage, '_persist') as mock_persist, \
             patch('vortex.infrastructure.storage.file_storage.LoggingContext') as mock_logging_context:
            
            file_storage.persist(sample_price_series, mock_future, mock_period)
            
            # Verify LoggingContext was used
            mock_logging_context.assert_called_once()
            call_args = mock_logging_context.call_args
            assert 'entry_msg' in call_args.kwargs
            assert 'success_msg' in call_args.kwargs
            assert 'failure_msg' in call_args.kwargs
            
            # Verify the messages contain relevant information
            assert 'Saving data' in call_args.kwargs['entry_msg']
            assert 'GC_202412' in call_args.kwargs['entry_msg']

    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch.object(FileStorage, 'load_metadata')
    def test_load_success(self, mock_load_metadata, mock_isfile, mock_exists,
                         file_storage, mock_stock, mock_period):
        """Test successful data loading."""
        # Setup mocks
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_metadata = Mock(spec=Metadata)
        mock_load_metadata.return_value = mock_metadata
        
        with patch.object(file_storage, '_load') as mock_load:
            mock_df = pd.DataFrame({'price': [100, 101, 102]})
            mock_load.return_value = mock_df
            
            result = file_storage.load(mock_stock, mock_period)
            
            expected_path = f"{file_storage.base_path}/stocks/1d/AAPL"
            
            # Verify file existence checks
            mock_exists.assert_called_once_with(expected_path)
            mock_isfile.assert_called_once_with(expected_path)
            
            # Verify metadata loading
            mock_load_metadata.assert_called_once_with(expected_path)
            
            # Verify data loading
            mock_load.assert_called_once_with(expected_path)
            
            # Verify result
            assert isinstance(result, PriceSeries)
            pd.testing.assert_frame_equal(result.df, mock_df)
            assert result.metadata is mock_metadata

    @patch('os.path.exists')
    def test_load_file_not_exists(self, mock_exists, file_storage, mock_stock, mock_period):
        """Test loading when file doesn't exist."""
        mock_exists.return_value = False
        
        with pytest.raises(FileNotFoundError):
            file_storage.load(mock_stock, mock_period)
            
        expected_path = f"{file_storage.base_path}/stocks/1d/AAPL"
        mock_exists.assert_called_once_with(expected_path)

    @patch('os.path.exists')
    @patch('os.path.isfile')
    def test_load_path_not_file(self, mock_isfile, mock_exists, file_storage, mock_stock, mock_period):
        """Test loading when path exists but is not a file."""
        mock_exists.return_value = True
        mock_isfile.return_value = False
        
        with pytest.raises(FileNotFoundError, match="exists but it's not a file"):
            file_storage.load(mock_stock, mock_period)

    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch.object(FileStorage, 'load_metadata')
    def test_load_no_metadata(self, mock_load_metadata, mock_isfile, mock_exists,
                             file_storage, mock_stock, mock_period):
        """Test loading when metadata is not found."""
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_load_metadata.return_value = None
        
        with pytest.raises(FileNotFoundError, match="Metadata file not found"):
            file_storage.load(mock_stock, mock_period)

    @patch('os.path.exists')
    @patch('os.path.isfile')
    @patch.object(FileStorage, 'load_metadata')
    def test_load_with_logging_context(self, mock_load_metadata, mock_isfile, mock_exists,
                                     file_storage, mock_forex, mock_period):
        """Test that load uses LoggingContext correctly."""
        # Setup mocks
        mock_exists.return_value = True
        mock_isfile.return_value = True
        mock_metadata = Mock(spec=Metadata)
        mock_load_metadata.return_value = mock_metadata
        
        with patch.object(file_storage, '_load') as mock_load, \
             patch('vortex.infrastructure.storage.file_storage.LoggingContext') as mock_logging_context:
            
            mock_load.return_value = pd.DataFrame({'price': [100]})
            
            file_storage.load(mock_forex, mock_period)
            
            # Verify LoggingContext was used
            mock_logging_context.assert_called_once()
            call_args = mock_logging_context.call_args
            assert 'entry_msg' in call_args.kwargs
            assert 'success_msg' in call_args.kwargs
            assert 'success_level' in call_args.kwargs
            
            # Verify the messages contain relevant information
            assert 'Loading data from' in call_args.kwargs['entry_msg']
            assert 'EURUSD' in call_args.kwargs['entry_msg']

    @patch('vortex.infrastructure.storage.file_storage.MetadataHandler')
    def test_load_metadata_static_method(self, mock_metadata_handler_class):
        """Test static load_metadata method."""
        # Setup mock
        mock_handler = Mock()
        mock_metadata = Mock(spec=Metadata)
        mock_handler.get_metadata.return_value = mock_metadata
        mock_metadata_handler_class.return_value = mock_handler
        
        file_path = "/test/path/file.csv"
        result = FileStorage.load_metadata(file_path)
        
        # Verify MetadataHandler was created with correct path
        mock_metadata_handler_class.assert_called_once_with(file_path)
        
        # Verify get_metadata was called
        mock_handler.get_metadata.assert_called_once()
        
        # Verify result
        assert result is mock_metadata

    @patch('vortex.infrastructure.storage.file_storage.MetadataHandler')
    def test_persist_metadata_static_method(self, mock_metadata_handler_class):
        """Test static persist_metadata method."""
        # Setup mock
        mock_handler = Mock()
        mock_metadata_handler_class.return_value = mock_handler
        mock_metadata = Mock(spec=Metadata)
        
        file_path = "/test/path/file.csv"
        FileStorage.persist_metadata(file_path, mock_metadata)
        
        # Verify MetadataHandler was created with correct path
        mock_metadata_handler_class.assert_called_once_with(file_path)
        
        # Verify set_metadata was called
        mock_handler.set_metadata.assert_called_once_with(mock_metadata)