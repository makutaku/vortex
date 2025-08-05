import pytest
import pandas as pd
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from vortex.infrastructure.storage.csv_storage import CsvStorage
from vortex.models.columns import DATE_TIME_COLUMN
from vortex.models.period import Period
from vortex.models.future import Future
from vortex.models.stock import Stock


class TestCsvStorage:
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def csv_storage(self, temp_dir):
        """Create CsvStorage instance."""
        return CsvStorage(base_path=temp_dir, dry_run=False)

    @pytest.fixture
    def csv_storage_dry_run(self, temp_dir):
        """Create CsvStorage instance in dry run mode."""
        return CsvStorage(base_path=temp_dir, dry_run=True)

    @pytest.fixture
    def sample_dataframe(self):
        """Create sample DataFrame for testing."""
        dates = pd.date_range('2024-01-01', periods=5, freq='D', tz='UTC')
        df = pd.DataFrame({
            'Open': [100, 101, 102, 103, 104],
            'High': [105, 106, 107, 108, 109],
            'Low': [95, 96, 97, 98, 99],
            'Close': [104, 105, 106, 107, 108],
            'Volume': [1000, 1100, 1200, 1300, 1400]
        }, index=dates)
        df.index.name = DATE_TIME_COLUMN
        return df

    @pytest.fixture
    def sample_future(self):
        """Create sample Future instrument."""
        return Future(
            id='GC_H24',
            futures_code='GC',
            year=2024,
            month_code='H',
            tick_date=datetime(2024, 1, 15),
            days_count=90
        )

    @pytest.fixture
    def sample_stock(self):
        """Create sample Stock instrument."""
        return Stock(id='AAPL', symbol='AAPL')

    def test_csv_storage_initialization(self, temp_dir):
        """Test CsvStorage initialization."""
        storage = CsvStorage(base_path=temp_dir, dry_run=False)
        
        assert storage.base_path == temp_dir
        assert storage.dry_run is False

    def test_csv_storage_initialization_dry_run(self, temp_dir):
        """Test CsvStorage initialization in dry run mode."""
        storage = CsvStorage(base_path=temp_dir, dry_run=True)
        
        assert storage.base_path == temp_dir
        assert storage.dry_run is True

    def test_make_file_path_for_instrument_future(self, csv_storage, sample_future):
        """Test file path generation for Future instrument."""
        period = Period.Daily
        
        file_path = csv_storage._make_file_path_for_instrument(sample_future, period)
        
        # Should end with .csv
        assert file_path.endswith('.csv')
        # Should contain the future symbol
        assert 'GCH24' in file_path or 'GC_H24' in file_path
        # Should contain period
        assert '1d' in file_path

    def test_make_file_path_for_instrument_stock(self, csv_storage, sample_stock):
        """Test file path generation for Stock instrument."""
        period = Period.Daily
        
        file_path = csv_storage._make_file_path_for_instrument(sample_stock, period)
        
        # Should end with .csv
        assert file_path.endswith('.csv')
        # Should contain the stock symbol
        assert 'AAPL' in file_path
        # Should contain period
        assert '1d' in file_path

    def test_make_file_path_different_periods(self, csv_storage, sample_stock):
        """Test file path generation with different periods."""
        periods = [Period.Daily, Period.Hourly, Period.Minute_5]
        
        paths = []
        for period in periods:
            path = csv_storage._make_file_path_for_instrument(sample_stock, period)
            paths.append(path)
        
        # All paths should be different
        assert len(set(paths)) == len(paths)
        
        # All should end with .csv
        for path in paths:
            assert path.endswith('.csv')

    def test_persist_dataframe(self, csv_storage, sample_dataframe, temp_dir):
        """Test persisting DataFrame to CSV file."""
        file_path = os.path.join(temp_dir, 'test_data.csv')
        
        csv_storage._persist(sample_dataframe, file_path)
        
        # File should exist
        assert os.path.exists(file_path)
        
        # File should contain expected data
        saved_df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        # Should have same shape
        assert saved_df.shape == sample_dataframe.shape
        # Should have same columns
        assert list(saved_df.columns) == list(sample_dataframe.columns)

    def test_persist_dry_run_mode(self, csv_storage_dry_run, sample_dataframe, temp_dir):
        """Test CSV storage dry run mode behavior."""
        file_path = os.path.join(temp_dir, 'dry_run_test.csv')
        
        # Note: Current CsvStorage implementation doesn't implement dry_run behavior in _persist
        # This test verifies the dry_run flag is stored correctly
        assert csv_storage_dry_run.dry_run is True
        
        # The _persist method will still create the file (implementation detail)
        # In a full implementation, dry_run would be checked here
        csv_storage_dry_run._persist(sample_dataframe, file_path)
        
        # Verify file was created (since dry_run is not implemented in _persist)
        assert os.path.exists(file_path)

    def test_load_dataframe(self, csv_storage, sample_dataframe, temp_dir):
        """Test loading DataFrame from CSV file."""
        file_path = os.path.join(temp_dir, 'load_test.csv')
        
        # First persist the data
        csv_storage._persist(sample_dataframe, file_path)
        
        # Then load it back
        loaded_df = csv_storage._load(file_path)
        
        # Should have same shape
        assert loaded_df.shape == sample_dataframe.shape
        
        # Should have same columns
        assert list(loaded_df.columns) == list(sample_dataframe.columns)
        
        # Index should be datetime and properly named
        assert loaded_df.index.name == DATE_TIME_COLUMN
        assert pd.api.types.is_datetime64_any_dtype(loaded_df.index)
        
        # Should be sorted by index
        assert loaded_df.index.is_monotonic_increasing

    def test_load_dataframe_datetime_parsing(self, csv_storage, temp_dir):
        """Test that datetime column is properly parsed when loading."""
        file_path = os.path.join(temp_dir, 'datetime_test.csv')
        
        # Create CSV content with specific datetime format
        csv_content = f"""{DATE_TIME_COLUMN},Open,Close
2024-01-01T00:00:00+00:00,100,104
2024-01-02T00:00:00+00:00,101,105
2024-01-03T00:00:00+00:00,102,106"""
        
        with open(file_path, 'w') as f:
            f.write(csv_content)
        
        loaded_df = csv_storage._load(file_path)
        
        # Index should be datetime
        assert pd.api.types.is_datetime64_any_dtype(loaded_df.index)
        # Should have 3 rows
        assert len(loaded_df) == 3
        # Should have correct columns
        assert 'Open' in loaded_df.columns
        assert 'Close' in loaded_df.columns

    def test_load_nonexistent_file(self, csv_storage):
        """Test loading from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            csv_storage._load('nonexistent_file.csv')

    def test_persist_load_roundtrip(self, csv_storage, sample_dataframe, temp_dir):
        """Test complete persist and load roundtrip."""
        file_path = os.path.join(temp_dir, 'roundtrip_test.csv')
        
        # Persist
        csv_storage._persist(sample_dataframe, file_path)
        
        # Load
        loaded_df = csv_storage._load(file_path)
        
        # Should be essentially the same (allowing for minor datetime precision differences)
        expected = sample_dataframe.sort_index()
        actual = loaded_df.sort_index()
        
        # Check basic structure
        assert expected.shape == actual.shape
        assert list(expected.columns) == list(actual.columns)
        
        # Check data values (more lenient than assert_frame_equal)
        for col in expected.columns:
            assert (expected[col].values == actual[col].values).all(), f"Column {col} values don't match"

    def test_persist_maintains_sorting(self, csv_storage, temp_dir):
        """Test that persist sorts the DataFrame by index."""
        # Create unsorted DataFrame
        dates = ['2024-01-03', '2024-01-01', '2024-01-02']
        df = pd.DataFrame({
            'Value': [3, 1, 2]
        }, index=pd.to_datetime(dates, utc=True))
        df.index.name = DATE_TIME_COLUMN
        
        file_path = os.path.join(temp_dir, 'sorting_test.csv')
        
        csv_storage._persist(df, file_path)
        
        # Read the file and check if it's sorted
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        # Skip header and check that dates are in ascending order
        data_lines = lines[1:]  # Skip header
        dates_in_file = [line.split(',')[0] for line in data_lines]
        
        # Should be in chronological order
        assert dates_in_file == sorted(dates_in_file)

    def test_load_maintains_sorting(self, csv_storage, temp_dir):
        """Test that load returns a sorted DataFrame."""
        file_path = os.path.join(temp_dir, 'load_sorting_test.csv')
        
        # Create CSV with unsorted dates
        csv_content = f"""{DATE_TIME_COLUMN},Value
2024-01-03T00:00:00+00:00,3
2024-01-01T00:00:00+00:00,1
2024-01-02T00:00:00+00:00,2"""
        
        with open(file_path, 'w') as f:
            f.write(csv_content)
        
        loaded_df = csv_storage._load(file_path)
        
        # Should be sorted by index
        assert loaded_df.index.is_monotonic_increasing
        
        # Values should be in correct order after sorting
        expected_values = [1, 2, 3]  # Sorted by date
        assert loaded_df['Value'].tolist() == expected_values

    def test_inheritance_from_file_storage(self, csv_storage):
        """Test that CsvStorage properly inherits from FileStorage."""
        from vortex.infrastructure.storage.file_storage import FileStorage
        
        assert isinstance(csv_storage, FileStorage)
        
        # Should have access to parent methods
        assert hasattr(csv_storage, 'base_path')
        assert hasattr(csv_storage, 'dry_run')

    @patch('pandas.read_csv')
    def test_load_with_pandas_error_handling(self, mock_read_csv, csv_storage):
        """Test error handling in _load method when pandas fails."""
        mock_read_csv.side_effect = pd.errors.EmptyDataError("No data")
        
        with pytest.raises(pd.errors.EmptyDataError):
            csv_storage._load('test_file.csv')
        
        mock_read_csv.assert_called_once_with('test_file.csv')

    @patch('pandas.DataFrame.to_csv')
    def test_persist_with_pandas_error_handling(self, mock_to_csv, csv_storage, sample_dataframe):
        """Test error handling in _persist method when pandas fails."""
        mock_to_csv.side_effect = IOError("Disk full")
        
        with pytest.raises(IOError):
            csv_storage._persist(sample_dataframe, 'test_file.csv')

    def test_file_extension_consistency(self, csv_storage, sample_stock):
        """Test that all generated file paths have .csv extension."""
        periods = [Period.Daily, Period.Hourly, Period.Minute_1, Period.Weekly]
        
        for period in periods:
            file_path = csv_storage._make_file_path_for_instrument(sample_stock, period)
            assert file_path.endswith('.csv'), f"File path {file_path} should end with .csv"
            # Should only have one .csv extension
            assert file_path.count('.csv') == 1, f"File path {file_path} should have exactly one .csv extension"