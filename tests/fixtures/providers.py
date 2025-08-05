"""
Mock provider fixtures for testing.

Provides mock implementations of data providers that can be used
consistently across different test modules.
"""

from unittest.mock import Mock, MagicMock
import pandas as pd
from typing import List, Dict, Any

from vortex.infrastructure.providers.data_providers.data_provider import DataProvider
from .mock_data import MockDataProvider


class MockDataProviderFixture(DataProvider):
    """Mock data provider implementation for testing."""
    
    def __init__(self, name: str = "mock", fail_on_fetch: bool = False):
        self.name = name
        self.fail_on_fetch = fail_on_fetch
        self._fetch_count = 0
        self._last_symbol = None
        
    def fetch_data(self, symbol: str, start_date=None, end_date=None, **kwargs) -> pd.DataFrame:
        """Mock fetch_data implementation."""
        self._fetch_count += 1
        self._last_symbol = symbol
        
        if self.fail_on_fetch:
            raise ConnectionError(f"Mock provider {self.name} configured to fail")
            
        # Return mock data based on symbol
        if symbol.startswith('GC'):
            return MockDataProvider.sample_futures_data(symbol)
        elif '/' in symbol:  # Forex pair
            return MockDataProvider.sample_forex_data(symbol) 
        else:  # Stock
            return MockDataProvider.sample_stock_data(symbol)
    
    def is_available(self) -> bool:
        """Mock availability check."""
        return True
        
    def get_supported_instruments(self) -> List[str]:
        """Mock supported instruments."""
        return ["AAPL", "GOOGL", "MSFT", "GC", "EURUSD"]
    
    @property
    def fetch_count(self) -> int:
        """Number of times fetch_data was called."""
        return self._fetch_count
        
    @property
    def last_symbol(self) -> str:
        """Last symbol that was fetched."""
        return self._last_symbol


class MockBarchartProvider(MockDataProviderFixture):
    """Mock Barchart provider for testing."""
    
    def __init__(self, **kwargs):
        super().__init__(name="barchart", **kwargs)
        self.username = "test_user"
        self.password = "test_pass"
        self.daily_limit = 150
        self.requests_made = 0
        
    def fetch_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Mock Barchart fetch with rate limiting simulation."""
        if self.requests_made >= self.daily_limit:
            raise Exception("Daily limit exceeded")
            
        self.requests_made += 1
        return super().fetch_data(symbol, **kwargs)


class MockYahooProvider(MockDataProviderFixture):
    """Mock Yahoo provider for testing."""
    
    def __init__(self, **kwargs):
        super().__init__(name="yahoo", **kwargs)
        
    def fetch_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Mock Yahoo fetch with potential bot detection."""
        import random
        
        # Simulate occasional bot detection
        if random.random() < 0.1:  # 10% chance
            raise Exception("Rate limited by Yahoo Finance")
            
        return super().fetch_data(symbol, **kwargs)


class MockIBKRProvider(MockDataProviderFixture):
    """Mock Interactive Brokers provider for testing."""
    
    def __init__(self, **kwargs):
        super().__init__(name="ibkr", **kwargs)
        self.host = "localhost"
        self.port = 7497
        self.client_id = 1
        self.connected = True
        
    def fetch_data(self, symbol: str, **kwargs) -> pd.DataFrame:
        """Mock IBKR fetch with connection simulation."""
        if not self.connected:
            raise ConnectionError("Not connected to TWS/Gateway")
            
        return super().fetch_data(symbol, **kwargs)
        
    def disconnect(self):
        """Simulate disconnection."""
        self.connected = False
        
    def connect(self):
        """Simulate connection."""
        self.connected = True