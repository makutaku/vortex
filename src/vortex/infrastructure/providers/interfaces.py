"""
Provider dependency injection interfaces.

This module defines protocols and interfaces for provider dependencies
to enable proper dependency injection and loose coupling.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Optional, Dict, Any
from datetime import datetime
from pandas import DataFrame


class CacheManagerProtocol(Protocol):
    """Protocol for cache management operations."""
    
    def configure_cache(self, cache_dir: str) -> None:
        """Configure cache directory and settings."""
        ...
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        ...


class ConnectionManagerProtocol(Protocol):
    """Protocol for connection management operations."""
    
    def connect(self, **kwargs) -> bool:
        """Establish connection. Returns True if successful."""
        ...
    
    def disconnect(self) -> None:
        """Close connection."""
        ...
    
    def is_connected(self) -> bool:
        """Check if connection is active."""
        ...


class HTTPClientProtocol(Protocol):
    """Protocol for HTTP client operations."""
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Any:
        """Perform HTTP GET request."""
        ...
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Any:
        """Perform HTTP POST request."""
        ...


class DataFetcherProtocol(Protocol):
    """Protocol for data fetching operations."""
    
    def fetch_historical_data(self, symbol: str, interval: str, start_date: datetime, end_date: datetime) -> DataFrame:
        """Fetch historical market data."""
        ...


class YahooCacheManager:
    """Default implementation of cache management for Yahoo Finance."""
    
    def configure_cache(self, cache_dir: str) -> None:
        """Configure yfinance cache directory."""
        import os
        import yfinance as yf
        os.makedirs(cache_dir, exist_ok=True)
        yf.set_tz_cache_location(cache_dir)
    
    def clear_cache(self) -> None:
        """Clear yfinance cache."""
        # Implementation would depend on yfinance internal cache structure
        pass


class IBKRConnectionManager:
    """Default implementation of connection management for IBKR."""
    
    def __init__(self, ib_client, ip_address: str, port: int, client_id: int):
        self.ib = ib_client
        self.ip_address = ip_address
        self.port = port
        self.client_id = client_id
        self._connected = False
    
    def connect(self, **kwargs) -> bool:
        """Establish IBKR connection."""
        try:
            timeout = kwargs.get('timeout', 30)
            self.ib.connect(self.ip_address, self.port, clientId=self.client_id, readonly=True, timeout=timeout)
            import time
            time.sleep(timeout)  # Allow connection to stabilize
            self._connected = True
            return True
        except Exception:
            self._connected = False
            return False
    
    def disconnect(self) -> None:
        """Close IBKR connection."""
        try:
            if self._connected:
                self.ib.disconnect()
        finally:
            self._connected = False
    
    def is_connected(self) -> bool:
        """Check if IBKR connection is active."""
        return self._connected and self.ib.isConnected()


class BarchartHTTPClient:
    """Default implementation of HTTP client for Barchart."""
    
    def __init__(self, session):
        self.session = session
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Any:
        """Perform HTTP GET request."""
        return self.session.get(url, headers=headers, timeout=timeout)
    
    def post(self, url: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: Optional[int] = None) -> Any:
        """Perform HTTP POST request."""
        return self.session.post(url, data=data, headers=headers, timeout=timeout)


class YahooDataFetcher:
    """Default implementation of data fetching for Yahoo Finance."""
    
    def fetch_historical_data(self, symbol: str, interval: str, start_date: datetime, end_date: datetime) -> DataFrame:
        """Fetch historical data from Yahoo Finance."""
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=interval,
            back_adjust=True,
            repair=True,
            raise_errors=True
        )
        return df


# Factory functions for creating default implementations
def create_yahoo_cache_manager(cache_dir: Optional[str] = None) -> YahooCacheManager:
    """Create a Yahoo cache manager with optional custom cache directory."""
    manager = YahooCacheManager()
    if cache_dir:
        manager.configure_cache(cache_dir)
    return manager


def create_ibkr_connection_manager(ib_client, ip_address: str, port: int, client_id: int) -> IBKRConnectionManager:
    """Create an IBKR connection manager."""
    return IBKRConnectionManager(ib_client, ip_address, port, client_id)


def create_barchart_http_client(session) -> BarchartHTTPClient:
    """Create a Barchart HTTP client."""
    return BarchartHTTPClient(session)


def create_yahoo_data_fetcher() -> YahooDataFetcher:
    """Create a Yahoo data fetcher."""
    return YahooDataFetcher()