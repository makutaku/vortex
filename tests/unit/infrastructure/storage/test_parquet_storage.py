"""
Unit tests for ParquetStorage class.

Tests parquet file operations, path generation, and data handling.
"""

import tempfile
from unittest.mock import Mock, patch
import pandas as pd
import pytest

from vortex.infrastructure.storage.parquet_storage import ParquetStorage
from vortex.models.future import Future
from vortex.models.period import Period


class TestParquetStorage:
    """Test cases for ParquetStorage class."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def parquet_storage(self, temp_dir):
        """Create ParquetStorage instance for testing."""
        return ParquetStorage(base_path=temp_dir, dry_run=False)

    @pytest.fixture
    def mock_future(self):
        """Create a mock Future instrument."""
        future = Mock(spec=Future)
        future.id = "GC"
        future.year = 2024
        future.month = 12
        return future

    @pytest.fixture
    def mock_period(self):
        """Create a mock Period."""
        period = Mock(spec=Period)
        period.value = "1d"
        return period

    def test_init(self, temp_dir):
        """Test ParquetStorage initialization."""
        storage = ParquetStorage(base_path=temp_dir, dry_run=False)
        
        assert storage.base_path == temp_dir
        assert storage.dry_run is False

    def test_init_dry_run(self, temp_dir):
        """Test ParquetStorage initialization with dry_run."""
        storage = ParquetStorage(base_path=temp_dir, dry_run=True)
        
        assert storage.base_path == temp_dir
        assert storage.dry_run is True

    def test_make_file_path_for_instrument(self, parquet_storage, mock_future, mock_period):
        """Test file path generation with parquet extension."""
        result = parquet_storage._make_file_path_for_instrument(mock_future, mock_period)
        
        expected_path = f"{parquet_storage.base_path}/futures/1d/GC/GC_202412"+"00.parquet"
        assert result == expected_path

    @patch('pandas.read_parquet')
    def test_load(self, mock_read_parquet, parquet_storage):
        """Test loading data from parquet file."""
        # Setup mock DataFrame
        mock_df = pd.DataFrame({'price': [100, 101, 102]})
        mock_df.sort_index = Mock(return_value=mock_df)
        mock_read_parquet.return_value = mock_df
        
        file_path = "/test/path/file.parquet"
        result = parquet_storage._load(file_path)
        
        # Verify read_parquet was called with correct path
        mock_read_parquet.assert_called_once_with(file_path)
        
        # Verify sort_index was called
        mock_df.sort_index.assert_called_once()
        
        # Verify result
        assert result is mock_df

    def test_persist(self, parquet_storage):
        """Test persisting data to parquet file."""
        # Create mock DataFrame with sort_index and to_parquet methods
        mock_df = Mock()
        mock_sorted_df = Mock()
        mock_df.sort_index.return_value = mock_sorted_df
        
        file_path = "/test/path/file.parquet"
        parquet_storage._persist(mock_df, file_path)
        
        # Verify sort_index was called
        mock_df.sort_index.assert_called_once()
        
        # Verify to_parquet was called on sorted DataFrame
        mock_sorted_df.to_parquet.assert_called_once_with(file_path, index=True)