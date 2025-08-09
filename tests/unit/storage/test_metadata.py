import pytest
import json
import tempfile
import os
from datetime import datetime
from enum import Enum
from unittest.mock import Mock, patch
import pandas as pd

from vortex.models.metadata import Metadata, default_serializer
from vortex.infrastructure.storage.metadata import MetadataHandler
from vortex.models.period import Period
from vortex.models.columns import VOLUME_COLUMN, OPEN_COLUMN, CLOSE_COLUMN


class TestMetadata:
    def test_metadata_creation(self):
        """Test basic Metadata creation."""
        start_date = datetime(2024, 1, 1, 10, 0, 0)
        end_date = datetime(2024, 1, 31, 16, 0, 0)
        first_row = datetime(2024, 1, 2, 9, 30, 0)
        last_row = datetime(2024, 1, 30, 16, 0, 0)
        
        metadata = Metadata(
            symbol="AAPL",
            period=Period.Daily,
            start_date=start_date,
            end_date=end_date,
            first_row_date=first_row,
            last_row_date=last_row,
            data_provider="yahoo"
        )
        
        assert metadata.symbol == "AAPL"
        assert metadata.period == Period.Daily
        assert metadata.start_date == start_date
        assert metadata.end_date == end_date
        assert metadata.first_row_date == first_row
        assert metadata.last_row_date == last_row
        assert metadata.data_provider == "yahoo"
        assert metadata.expiration_date is None
        assert isinstance(metadata.created_date, datetime)

    def test_metadata_with_optional_fields(self):
        """Test Metadata creation with optional fields."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        first_row = datetime(2024, 1, 2)
        last_row = datetime(2024, 1, 30)
        expiration = datetime(2024, 1, 30)
        created = datetime(2024, 1, 1, 12, 0, 0)
        
        metadata = Metadata(
            symbol="GC",
            period=Period.Hourly,
            start_date=start_date,
            end_date=end_date,
            first_row_date=first_row,
            last_row_date=last_row,
            data_provider="barchart",
            expiration_date=expiration,
            created_date=created
        )
        
        assert metadata.expiration_date == expiration
        assert metadata.created_date == created

    def test_metadata_str_representation(self):
        """Test Metadata string representation."""
        metadata = Metadata(
            symbol="ES",
            period=Period.Daily,
            start_date=datetime(2024, 2, 1),
            end_date=datetime(2024, 2, 29),
            first_row_date=datetime(2024, 2, 1),
            last_row_date=datetime(2024, 2, 28)
        )
        
        result = str(metadata)
        expected = "ES, 1d, 2024-02-01, 2024-02-29"
        assert result == expected

    @patch('vortex.models.metadata.logging.debug')
    def test_create_metadata_basic(self, mock_debug):
        """Test basic create_metadata functionality."""
        # Create mock DataFrame
        dates = pd.date_range('2024-01-01', periods=5, freq='D', tz='UTC')
        df = pd.DataFrame({
            OPEN_COLUMN: [100, 101, 102, 103, 104],
            CLOSE_COLUMN: [104, 105, 106, 107, 108],
            VOLUME_COLUMN: [1000, 1100, 1200, 1300, 1400]
        }, index=dates)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        metadata = Metadata.create_metadata(
            df, "yahoo", "AAPL", Period.Daily, start_date, end_date
        )
        
        assert metadata.symbol == "AAPL"
        assert metadata.period == Period.Daily
        assert metadata.start_date == start_date
        assert metadata.end_date == end_date
        assert metadata.data_provider == "yahoo"
        assert metadata.first_row_date == dates[0].to_pydatetime()
        assert metadata.last_row_date == dates[-1].to_pydatetime()
        assert metadata.expiration_date is None
        mock_debug.assert_not_called()

    @patch('vortex.models.metadata.logging.debug')
    def test_create_metadata_with_expiration_detection(self, mock_debug):
        """Test create_metadata with contract expiration detection."""
        # Create DataFrame with zero volume in last row
        dates = pd.date_range('2024-01-01', periods=3, freq='D', tz='UTC')
        df = pd.DataFrame({
            'Open': [100, 101, 102],
            'Close': [104, 105, 106],
            VOLUME_COLUMN: [1000, 1100, 0]  # Last volume is 0
        }, index=dates)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)
        
        metadata = Metadata.create_metadata(
            df, "barchart", "GC", Period.Daily, start_date, end_date
        )
        
        assert metadata.symbol == "GC"
        assert metadata.period == Period.Daily
        assert metadata.expiration_date == dates[-1].to_pydatetime()
        mock_debug.assert_called_once()
        
        # Verify debug message
        debug_call = mock_debug.call_args[0][0]
        assert "Detected possible contract expiration" in debug_call
        assert "last bar has volume 0" in debug_call

    def test_create_metadata_sorts_dataframe(self):
        """Test that create_metadata sorts the DataFrame by index."""
        # Create unsorted DataFrame
        dates = [
            pd.Timestamp('2024-01-03', tz='UTC'),
            pd.Timestamp('2024-01-01', tz='UTC'),
            pd.Timestamp('2024-01-02', tz='UTC')
        ]
        df = pd.DataFrame({
            'Open': [102, 100, 101],
            'Close': [106, 104, 105],
            VOLUME_COLUMN: [1200, 1000, 1100]
        }, index=dates)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 3)
        
        metadata = Metadata.create_metadata(
            df, "yahoo", "TEST", Period.Daily, start_date, end_date
        )
        
        # Should use the earliest date as first_row_date after sorting
        assert metadata.first_row_date == pd.Timestamp('2024-01-01', tz='UTC').to_pydatetime()
        assert metadata.last_row_date == pd.Timestamp('2024-01-03', tz='UTC').to_pydatetime()


class TestDefaultSerializer:
    def test_serialize_datetime(self):
        """Test serializing datetime objects."""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = default_serializer(dt)
        assert result == dt.isoformat()

    def test_serialize_string(self):
        """Test serializing string objects."""
        result = default_serializer("test string")
        assert result == "test string"

    def test_serialize_int(self):
        """Test serializing integer objects."""
        result = default_serializer(42)
        assert result == 42

    def test_serialize_float(self):
        """Test serializing float objects."""
        result = default_serializer(3.14)
        assert result == 3.14

    def test_serialize_enum(self):
        """Test serializing enum objects."""
        result = default_serializer(Period.Daily)
        assert result == "1d"

    def test_serialize_custom_enum(self):
        """Test serializing custom enum objects."""
        class TestEnum(Enum):
            VALUE1 = "test_value"
            VALUE2 = 42
        
        result = default_serializer(TestEnum.VALUE1)
        assert result == "test_value"
        
        result = default_serializer(TestEnum.VALUE2)
        assert result == 42

    def test_serialize_unsupported_type(self):
        """Test serializing unsupported type raises TypeError."""
        with pytest.raises(TypeError, match="Type not serializable"):
            default_serializer([1, 2, 3])  # Lists are not supported
        
        with pytest.raises(TypeError, match="Type not serializable"):
            default_serializer({"key": "value"})  # Dicts are not supported


class TestMetadataHandler:
    def test_metadata_handler_creation(self):
        """Test MetadataHandler creation."""
        file_path = "/path/to/data.csv"
        handler = MetadataHandler(file_path)
        
        assert handler.file_path == file_path
        assert handler.metadata_file == "/path/to/data.csv.json"

    def test_metadata_handler_with_nested_path(self):
        """Test MetadataHandler with nested file path."""
        file_path = "/deep/nested/path/data.csv"
        handler = MetadataHandler(file_path)
        
        assert handler.file_path == file_path
        assert handler.metadata_file == "/deep/nested/path/data.csv.json"

    def test_set_and_get_metadata_roundtrip(self):
        """Test setting and getting metadata in a roundtrip."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.csv")
            handler = MetadataHandler(file_path)
            
            # Create test metadata
            metadata = Metadata(
                symbol="TEST",
                period=Period.Hourly,
                start_date=datetime(2024, 1, 1, 9, 0, 0),
                end_date=datetime(2024, 1, 1, 17, 0, 0),
                first_row_date=datetime(2024, 1, 1, 9, 30, 0),
                last_row_date=datetime(2024, 1, 1, 16, 30, 0),
                data_provider="test_provider",
                expiration_date=datetime(2024, 1, 31, 23, 59, 59),
                created_date=datetime(2024, 1, 1, 8, 0, 0)
            )
            
            # Set metadata
            handler.set_metadata(metadata)
            
            # Verify file was created
            assert os.path.exists(handler.metadata_file)
            
            # Get metadata back
            retrieved_metadata = handler.get_metadata()
            
            # Verify all fields match
            assert retrieved_metadata.symbol == metadata.symbol
            assert retrieved_metadata.period == metadata.period
            # Handle timezone differences in datetime comparison
            if hasattr(retrieved_metadata.start_date, 'replace') and hasattr(metadata.start_date, 'replace'):
                if retrieved_metadata.start_date.tzinfo is not None and metadata.start_date.tzinfo is None:
                    from datetime import timezone
                    expected_start = metadata.start_date.replace(tzinfo=timezone.utc)
                    assert retrieved_metadata.start_date == expected_start
                else:
                    assert retrieved_metadata.start_date == metadata.start_date
            else:
                assert retrieved_metadata.start_date == metadata.start_date
            # Handle timezone differences for all datetime fields
            def compare_datetime_with_tz(retrieved, original):
                if hasattr(retrieved, 'replace') and hasattr(original, 'replace'):
                    if retrieved.tzinfo is not None and original.tzinfo is None:
                        from datetime import timezone
                        return retrieved == original.replace(tzinfo=timezone.utc)
                return retrieved == original
            
            assert compare_datetime_with_tz(retrieved_metadata.end_date, metadata.end_date)
            assert compare_datetime_with_tz(retrieved_metadata.first_row_date, metadata.first_row_date)
            assert compare_datetime_with_tz(retrieved_metadata.last_row_date, metadata.last_row_date)
            assert retrieved_metadata.data_provider == metadata.data_provider
            assert compare_datetime_with_tz(retrieved_metadata.expiration_date, metadata.expiration_date)
            assert compare_datetime_with_tz(retrieved_metadata.created_date, metadata.created_date)

    def test_set_metadata_overwrites_existing(self):
        """Test that set_metadata overwrites existing metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.csv")
            handler = MetadataHandler(file_path)
            
            # Create and set first metadata
            metadata1 = Metadata(
                symbol="FIRST",
                period=Period.Daily,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                first_row_date=datetime(2024, 1, 2),
                last_row_date=datetime(2024, 1, 30),
                data_provider="provider1"
            )
            handler.set_metadata(metadata1)
            
            # Create and set second metadata
            metadata2 = Metadata(
                symbol="SECOND",
                period=Period.Hourly,
                start_date=datetime(2024, 2, 1),
                end_date=datetime(2024, 2, 28),
                first_row_date=datetime(2024, 2, 2),
                last_row_date=datetime(2024, 2, 27),
                data_provider="provider2"
            )
            handler.set_metadata(metadata2)
            
            # Get metadata - should be the second one
            retrieved = handler.get_metadata()
            assert retrieved.symbol == "SECOND"
            assert retrieved.period == Period.Hourly
            assert retrieved.data_provider == "provider2"

    def test_get_metadata_file_not_found(self):
        """Test get_metadata when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "nonexistent.csv")
            handler = MetadataHandler(file_path)
            
            with pytest.raises(FileNotFoundError):
                handler.get_metadata()

    def test_set_metadata_creates_json_file(self):
        """Test that set_metadata creates a properly formatted JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.csv")
            handler = MetadataHandler(file_path)
            
            metadata = Metadata(
                symbol="JSON_TEST",
                period=Period.Daily,
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 1, 31),
                first_row_date=datetime(2024, 1, 2),
                last_row_date=datetime(2024, 1, 30),
                data_provider="json_provider"
            )
            
            handler.set_metadata(metadata)
            
            # Read and verify JSON file content
            with open(handler.metadata_file, 'r') as f:
                json_data = json.load(f)
            
            assert json_data["symbol"] == "JSON_TEST"
            assert json_data["period"] == "1d"  # Should be serialized as string
            assert json_data["data_provider"] == "json_provider"
            assert "start_date" in json_data
            assert "end_date" in json_data

    def test_get_metadata_with_malformed_json(self):
        """Test get_metadata with malformed JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test.csv")
            handler = MetadataHandler(file_path)
            
            # Create malformed JSON file
            with open(handler.metadata_file, 'w') as f:
                f.write('{"symbol": "TEST", "period":}')  # Invalid JSON
            
            with pytest.raises(json.JSONDecodeError):
                handler.get_metadata()

    def test_metadata_handler_file_path_edge_cases(self):
        """Test MetadataHandler with edge case file paths."""
        # File without extension
        handler1 = MetadataHandler("datafile")
        assert handler1.metadata_file == "datafile.json"
        
        # File with multiple dots
        handler2 = MetadataHandler("data.backup.csv")
        assert handler2.metadata_file == "data.backup.csv.json"
        
        # Root directory file
        handler3 = MetadataHandler("/data.csv")
        assert handler3.metadata_file == "/data.csv.json"