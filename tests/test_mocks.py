"""
Mock implementations for testing Vortex components.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import Mock

import pytest

from vortex.data_providers.data_provider import DataProvider
from vortex.data_storage.file_storage import FileStorage
from vortex.instruments.instrument import Instrument


class MockDataProvider(DataProvider):
    """Mock data provider for testing."""
    
    def __init__(self, fail_on_symbol: Optional[str] = None, delay: float = 0):
        """Initialize mock provider.
        
        Args:
            fail_on_symbol: Symbol that should cause download to fail
            delay: Simulated delay for downloads (seconds)
        """
        self.fail_on_symbol = fail_on_symbol
        self.delay = delay
        self.download_count = 0
        self.downloaded_symbols = []
    
    def download_data(self, instrument: Instrument, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Mock download data implementation."""
        import time
        
        if self.delay > 0:
            time.sleep(self.delay)
        
        self.download_count += 1
        symbol = instrument.name
        self.downloaded_symbols.append(symbol)
        
        if self.fail_on_symbol and symbol == self.fail_on_symbol:
            raise Exception(f"Mock failure for symbol {symbol}")
        
        # Generate mock data
        data = []
        current_date = start_date
        price = 100.0
        
        while current_date <= end_date:
            # Simple price simulation
            price_change = (hash(f"{symbol}{current_date}") % 10 - 5) * 0.01
            price = max(price + price_change, 1.0)
            
            data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "open": round(price * 0.99, 2),
                "high": round(price * 1.02, 2),
                "low": round(price * 0.97, 2),
                "close": round(price, 2),
                "volume": hash(f"{symbol}{current_date}") % 10000 + 1000
            })
            
            current_date += timedelta(days=1)
        
        return data
    
    def reset_stats(self):
        """Reset download statistics."""
        self.download_count = 0
        self.downloaded_symbols = []


class MockFileStorage(FileStorage):
    """Mock file storage for testing."""
    
    def __init__(self, fail_on_save: bool = False, fail_on_load: bool = False):
        """Initialize mock storage.
        
        Args:
            fail_on_save: Whether to fail on save operations
            fail_on_load: Whether to fail on load operations
        """
        self.fail_on_save = fail_on_save
        self.fail_on_load = fail_on_load
        self.saved_data = {}
        self.save_count = 0
        self.load_count = 0
    
    def save(self, data: List[Dict[str, Any]], instrument: Instrument, 
             start_date: datetime, end_date: datetime) -> bool:
        """Mock save implementation."""
        self.save_count += 1
        
        if self.fail_on_save:
            raise Exception("Mock save failure")
        
        key = f"{instrument.name}_{start_date}_{end_date}"
        self.saved_data[key] = data.copy()
        return True
    
    def load(self, instrument: Instrument, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Mock load implementation."""
        self.load_count += 1
        
        if self.fail_on_load:
            raise Exception("Mock load failure")
        
        key = f"{instrument.name}_{start_date}_{end_date}"
        return self.saved_data.get(key, [])
    
    def exists(self, instrument: Instrument, start_date: datetime, end_date: datetime) -> bool:
        """Mock exists check."""
        key = f"{instrument.name}_{start_date}_{end_date}"
        return key in self.saved_data
    
    def reset_stats(self):
        """Reset storage statistics."""
        self.save_count = 0
        self.load_count = 0
        self.saved_data = {}


class MockInstrument(Instrument):
    """Mock instrument for testing."""
    
    def __init__(self, name: str = "TEST", symbol: str = "TEST"):
        """Initialize mock instrument."""
        super().__init__(name)
        self.symbol = symbol
    
    def __str__(self) -> str:
        return f"MockInstrument({self.name})"


@pytest.fixture
def mock_data_provider():
    """Create a mock data provider."""
    return MockDataProvider()


@pytest.fixture
def mock_failing_provider():
    """Create a mock data provider that fails on FAIL symbol."""
    return MockDataProvider(fail_on_symbol="FAIL")


@pytest.fixture
def mock_slow_provider():
    """Create a mock data provider with artificial delay."""
    return MockDataProvider(delay=0.1)


@pytest.fixture
def mock_file_storage():
    """Create a mock file storage."""
    return MockFileStorage()


@pytest.fixture
def mock_failing_storage():
    """Create a mock file storage that fails on save."""
    return MockFileStorage(fail_on_save=True)


@pytest.fixture
def mock_instrument():
    """Create a mock instrument."""
    return MockInstrument("MOCK", "MOCK")


@pytest.fixture
def sample_instruments():
    """Create sample instruments for testing."""
    return [
        MockInstrument("AAPL", "AAPL"),
        MockInstrument("GOOGL", "GOOGL"), 
        MockInstrument("MSFT", "MSFT"),
        MockInstrument("FAIL", "FAIL")  # This one will fail with mock_failing_provider
    ]


@pytest.mark.unit
class TestMockDataProvider:
    """Test the mock data provider."""
    
    def test_basic_download(self, mock_data_provider, mock_instrument):
        """Test basic data download."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 5)
        
        data = mock_data_provider.download_data(mock_instrument, start_date, end_date)
        
        assert len(data) == 5  # 5 days
        assert mock_data_provider.download_count == 1
        assert "MOCK" in mock_data_provider.downloaded_symbols
        
        # Check data structure
        for record in data:
            assert "date" in record
            assert "open" in record
            assert "high" in record
            assert "low" in record
            assert "close" in record
            assert "volume" in record
    
    def test_failure_simulation(self, mock_failing_provider):
        """Test simulated failure."""
        failing_instrument = MockInstrument("FAIL", "FAIL")
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        with pytest.raises(Exception, match="Mock failure for symbol FAIL"):
            mock_failing_provider.download_data(failing_instrument, start_date, end_date)
    
    def test_delay_simulation(self, mock_slow_provider, mock_instrument):
        """Test delay simulation."""
        import time
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        start_time = time.time()
        data = mock_slow_provider.download_data(mock_instrument, start_date, end_date)
        elapsed = time.time() - start_time
        
        assert elapsed >= 0.1  # Should take at least 0.1 seconds
        assert len(data) == 1
    
    def test_statistics_tracking(self, mock_data_provider, sample_instruments):
        """Test download statistics tracking."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        # Download data for multiple instruments
        for instrument in sample_instruments[:3]:  # Skip the failing one
            mock_data_provider.download_data(instrument, start_date, end_date)
        
        assert mock_data_provider.download_count == 3
        assert len(mock_data_provider.downloaded_symbols) == 3
        assert "AAPL" in mock_data_provider.downloaded_symbols
        assert "GOOGL" in mock_data_provider.downloaded_symbols
        assert "MSFT" in mock_data_provider.downloaded_symbols
        
        # Reset and verify
        mock_data_provider.reset_stats()
        assert mock_data_provider.download_count == 0
        assert len(mock_data_provider.downloaded_symbols) == 0


@pytest.mark.unit
class TestMockFileStorage:
    """Test the mock file storage."""
    
    def test_save_and_load(self, mock_file_storage, mock_instrument):
        """Test save and load operations."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        test_data = [
            {"date": "2024-01-01", "close": 100.0},
            {"date": "2024-01-02", "close": 101.0}
        ]
        
        # Save data
        result = mock_file_storage.save(test_data, mock_instrument, start_date, end_date)
        assert result is True
        assert mock_file_storage.save_count == 1
        
        # Check exists
        assert mock_file_storage.exists(mock_instrument, start_date, end_date) is True
        
        # Load data
        loaded_data = mock_file_storage.load(mock_instrument, start_date, end_date)
        assert loaded_data == test_data
        assert mock_file_storage.load_count == 1
    
    def test_save_failure(self, mock_failing_storage, mock_instrument):
        """Test save failure simulation."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        test_data = [{"date": "2024-01-01", "close": 100.0}]
        
        with pytest.raises(Exception, match="Mock save failure"):
            mock_failing_storage.save(test_data, mock_instrument, start_date, end_date)
    
    def test_load_failure(self):
        """Test load failure simulation."""
        storage = MockFileStorage(fail_on_load=True)
        instrument = MockInstrument("TEST")
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        with pytest.raises(Exception, match="Mock load failure"):
            storage.load(instrument, start_date, end_date)
    
    def test_nonexistent_data(self, mock_file_storage, mock_instrument):
        """Test loading nonexistent data."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        
        # Should return empty list for nonexistent data
        data = mock_file_storage.load(mock_instrument, start_date, end_date)
        assert data == []
        
        # Should return False for exists check
        assert mock_file_storage.exists(mock_instrument, start_date, end_date) is False
    
    def test_statistics_tracking(self, mock_file_storage, sample_instruments):
        """Test storage statistics tracking."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 1)
        test_data = [{"date": "2024-01-01", "close": 100.0}]
        
        # Save data for multiple instruments
        for instrument in sample_instruments:
            mock_file_storage.save(test_data, instrument, start_date, end_date)
        
        assert mock_file_storage.save_count == 4
        
        # Load data for multiple instruments
        for instrument in sample_instruments:
            mock_file_storage.load(instrument, start_date, end_date)
        
        assert mock_file_storage.load_count == 4
        
        # Reset and verify
        mock_file_storage.reset_stats()
        assert mock_file_storage.save_count == 0
        assert mock_file_storage.load_count == 0
        # Data should still exist after stats reset
        assert len(mock_file_storage.saved_data) == 4


@pytest.mark.unit
class TestMockInstrument:
    """Test the mock instrument."""
    
    def test_creation(self):
        """Test mock instrument creation."""
        instrument = MockInstrument("TEST", "SYMBOL")
        
        assert instrument.name == "TEST"
        assert instrument.symbol == "SYMBOL"
        assert str(instrument) == "MockInstrument(TEST)"
    
    def test_default_values(self):
        """Test default values."""
        instrument = MockInstrument()
        
        assert instrument.name == "TEST"
        assert instrument.symbol == "TEST"