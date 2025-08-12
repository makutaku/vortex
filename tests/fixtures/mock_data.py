"""
Mock data fixtures for testing.

Provides consistent mock data and responses for use across
different test modules to ensure reproducible test results.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, List

from vortex.models.columns import (
    DATETIME_COLUMN_NAME, OPEN_COLUMN, HIGH_COLUMN, LOW_COLUMN, 
    CLOSE_COLUMN, VOLUME_COLUMN
)


class MockDataProvider:
    """Provides mock data for testing data providers."""
    
    @staticmethod
    def sample_stock_data(symbol: str = "AAPL", days: int = 30) -> pd.DataFrame:
        """Generate sample stock data for testing."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate mock price data with some randomness
        base_price = 150.0
        data = []
        
        for i, date in enumerate(dates):
            # Simple price simulation
            price_change = (i % 7 - 3) * 2.5  # Some variation
            open_price = base_price + price_change
            high_price = open_price + abs(price_change) * 0.5
            low_price = open_price - abs(price_change) * 0.3
            close_price = open_price + price_change * 0.8
            volume = 50000000 + (i % 5) * 10000000
            
            data.append({
                DATETIME_COLUMN_NAME: date,
                OPEN_COLUMN: round(open_price, 2),
                HIGH_COLUMN: round(high_price, 2),
                LOW_COLUMN: round(low_price, 2),
                CLOSE_COLUMN: round(close_price, 2),
                VOLUME_COLUMN: volume,
                'Symbol': symbol
            })
        
        return pd.DataFrame(data).set_index(DATETIME_COLUMN_NAME)

    @staticmethod
    def sample_futures_data(symbol: str = "GC", days: int = 30) -> pd.DataFrame:
        """Generate sample futures data for testing."""
        return MockDataProvider.sample_stock_data(symbol, days)

    @staticmethod
    def sample_forex_data(pair: str = "EURUSD", days: int = 30) -> pd.DataFrame:
        """Generate sample forex data for testing."""
        data = MockDataProvider.sample_stock_data(pair, days)
        # Forex typically has different price ranges
        data = data / 100  # Scale down for forex-like prices
        return data


class MockResponses:
    """Mock HTTP responses for testing provider integrations."""
    
    @staticmethod
    def yahoo_finance_response() -> Dict[str, Any]:
        """Mock Yahoo Finance API response."""
        return {
            "chart": {
                "result": [{
                    "meta": {
                        "currency": "USD",
                        "symbol": "AAPL",
                        "exchangeName": "NasdaqGS",
                        "instrumentType": "EQUITY"
                    },
                    "timestamp": [1640995200, 1641081600, 1641168000],
                    "indicators": {
                        "quote": [{
                            "open": [182.63, 179.61, 177.83],
                            "high": [182.94, 180.17, 182.99],
                            "low": [177.71, 174.63, 177.07],
                            "close": [177.57, 174.92, 182.01],
                            "volume": [59773000, 76138100, 64062300]
                        }]
                    }
                }]
            }
        }

    @staticmethod
    def barchart_response() -> str:
        """Mock Barchart.com HTML/CSV response."""
        return """Date,Open,High,Low,Close,Volume
2024-01-01,150.00,152.50,149.00,151.75,50000000
2024-01-02,151.75,153.25,150.50,152.80,48000000
2024-01-03,152.80,154.10,151.90,153.45,52000000"""


class MockInstruments:
    """Mock instrument definitions for testing."""
    
    @staticmethod
    def sample_stocks() -> List[Dict[str, Any]]:
        """Sample stock instruments for testing."""
        return [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "type": "stock"
            },
            {
                "symbol": "GOOGL", 
                "name": "Alphabet Inc.",
                "exchange": "NASDAQ",
                "type": "stock"
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft Corporation", 
                "exchange": "NASDAQ",
                "type": "stock"
            }
        ]

    @staticmethod
    def sample_futures() -> List[Dict[str, Any]]:
        """Sample futures instruments for testing."""
        return [
            {
                "symbol": "GC",
                "name": "Gold Futures",
                "exchange": "COMEX",
                "type": "future",
                "expiry_months": ["F", "G", "J", "M", "Q", "V", "Z"]
            },
            {
                "symbol": "CL",
                "name": "Crude Oil Futures",
                "exchange": "NYMEX", 
                "type": "future",
                "expiry_months": ["F", "G", "H", "J", "K", "M", "N", "Q", "U", "V", "X", "Z"]
            }
        ]