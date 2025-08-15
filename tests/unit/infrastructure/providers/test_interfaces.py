"""
Unit tests for provider dependency injection interfaces.

Tests protocols, default implementations, and factory functions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pandas import DataFrame

from vortex.infrastructure.providers.interfaces import (
    CacheManagerProtocol,
    ConnectionManagerProtocol, 
    HTTPClientProtocol,
    DataFetcherProtocol,
    YahooCacheManager,
    IBKRConnectionManager,
    BarchartHTTPClient,
    YahooDataFetcher,
    create_yahoo_cache_manager,
    create_ibkr_connection_manager,
    create_barchart_http_client,
    create_yahoo_data_fetcher
)


@pytest.mark.unit
class TestYahooCacheManager:
    """Test YahooCacheManager implementation."""
    
    def test_configure_cache(self):
        """Test cache configuration."""
        manager = YahooCacheManager()
        
        with patch('os.makedirs') as mock_makedirs, \
             patch('yfinance.set_tz_cache_location') as mock_set_tz:
            
            manager.configure_cache('/test/cache')
            
            mock_makedirs.assert_called_once_with('/test/cache', exist_ok=True)
            mock_set_tz.assert_called_once_with('/test/cache')
    
    def test_clear_cache(self):
        """Test cache clearing (currently no-op)."""
        manager = YahooCacheManager()
        # Should not raise exception
        manager.clear_cache()


@pytest.mark.unit
class TestIBKRConnectionManager:
    """Test IBKRConnectionManager implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_ib = Mock()
        self.manager = IBKRConnectionManager(
            self.mock_ib, '127.0.0.1', 7497, 1
        )
    
    def test_init(self):
        """Test initialization."""
        assert self.manager.ib == self.mock_ib
        assert self.manager.ip_address == '127.0.0.1'
        assert self.manager.port == 7497
        assert self.manager.client_id == 1
        assert not self.manager._connected
    
    def test_connect_success(self):
        """Test successful connection."""
        with patch('time.sleep'):
            result = self.manager.connect(timeout=1)
            
            assert result is True
            assert self.manager._connected is True
            self.mock_ib.connect.assert_called_once_with(
                '127.0.0.1', 7497, clientId=1, readonly=True, timeout=1
            )
    
    def test_connect_failure(self):
        """Test failed connection."""
        self.mock_ib.connect.side_effect = Exception("Connection failed")
        
        with patch('time.sleep'):
            result = self.manager.connect()
            
            assert result is False
            assert self.manager._connected is False
    
    def test_disconnect_when_connected(self):
        """Test disconnection when connected."""
        self.manager._connected = True
        
        self.manager.disconnect()
        
        self.mock_ib.disconnect.assert_called_once()
        assert self.manager._connected is False
    
    def test_disconnect_when_not_connected(self):
        """Test disconnection when not connected."""
        self.manager._connected = False
        
        self.manager.disconnect()
        
        self.mock_ib.disconnect.assert_not_called()
        assert self.manager._connected is False
    
    def test_disconnect_with_exception(self):
        """Test disconnection handles exceptions."""
        self.manager._connected = True
        self.mock_ib.disconnect.side_effect = Exception("Disconnect failed")
        
        # Should handle exception gracefully and still set _connected to False
        # The implementation uses try/finally so _connected should be False regardless
        try:
            self.manager.disconnect()
        except Exception:
            pass  # Exception expected but should be handled
        
        assert self.manager._connected is False
    
    def test_is_connected_true(self):
        """Test is_connected when truly connected."""
        self.manager._connected = True
        self.mock_ib.isConnected.return_value = True
        
        assert self.manager.is_connected() is True
    
    def test_is_connected_false_local(self):
        """Test is_connected when locally not connected."""
        self.manager._connected = False
        
        assert self.manager.is_connected() is False
        self.mock_ib.isConnected.assert_not_called()
    
    def test_is_connected_false_remote(self):
        """Test is_connected when locally connected but remotely not."""
        self.manager._connected = True
        self.mock_ib.isConnected.return_value = False
        
        assert self.manager.is_connected() is False


@pytest.mark.unit 
class TestBarchartHTTPClient:
    """Test BarchartHTTPClient implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.client = BarchartHTTPClient(self.mock_session)
    
    def test_init(self):
        """Test initialization."""
        assert self.client.session == self.mock_session
    
    def test_get_basic(self):
        """Test basic GET request."""
        mock_response = Mock()
        self.mock_session.get.return_value = mock_response
        
        result = self.client.get('https://test.com')
        
        assert result == mock_response
        self.mock_session.get.assert_called_once_with(
            'https://test.com', headers=None, timeout=None
        )
    
    def test_get_with_headers_and_timeout(self):
        """Test GET request with headers and timeout."""
        headers = {'Authorization': 'Bearer token'}
        mock_response = Mock()
        self.mock_session.get.return_value = mock_response
        
        result = self.client.get('https://test.com', headers=headers, timeout=30)
        
        assert result == mock_response
        self.mock_session.get.assert_called_once_with(
            'https://test.com', headers=headers, timeout=30
        )
    
    def test_post_basic(self):
        """Test basic POST request."""
        mock_response = Mock()
        self.mock_session.post.return_value = mock_response
        
        result = self.client.post('https://test.com')
        
        assert result == mock_response
        self.mock_session.post.assert_called_once_with(
            'https://test.com', data=None, headers=None, timeout=None
        )
    
    def test_post_with_data_headers_timeout(self):
        """Test POST request with data, headers, and timeout."""
        data = {'key': 'value'}
        headers = {'Content-Type': 'application/json'}
        mock_response = Mock()
        self.mock_session.post.return_value = mock_response
        
        result = self.client.post('https://test.com', data=data, headers=headers, timeout=30)
        
        assert result == mock_response
        self.mock_session.post.assert_called_once_with(
            'https://test.com', data=data, headers=headers, timeout=30
        )


@pytest.mark.unit
class TestYahooDataFetcher:
    """Test YahooDataFetcher implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.fetcher = YahooDataFetcher()
    
    @patch('yfinance.Ticker')
    def test_fetch_historical_data(self, mock_ticker_class):
        """Test fetching historical data."""
        # Mock ticker and data
        mock_ticker = Mock()
        mock_df = DataFrame({'Open': [100, 101], 'Close': [101, 102]})
        mock_ticker.history.return_value = mock_df
        mock_ticker_class.return_value = mock_ticker
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 2)
        
        result = self.fetcher.fetch_historical_data('AAPL', '1d', start_date, end_date)
        
        assert result.equals(mock_df)
        mock_ticker_class.assert_called_once_with('AAPL')
        mock_ticker.history.assert_called_once_with(
            start='2024-01-01',
            end='2024-01-02',
            interval='1d',
            back_adjust=True,
            repair=True,
            raise_errors=True
        )


@pytest.mark.unit
class TestFactoryFunctions:
    """Test factory functions for creating default implementations."""
    
    def test_create_yahoo_cache_manager_no_dir(self):
        """Test creating Yahoo cache manager without cache directory."""
        manager = create_yahoo_cache_manager()
        
        assert isinstance(manager, YahooCacheManager)
    
    @patch.object(YahooCacheManager, 'configure_cache')
    def test_create_yahoo_cache_manager_with_dir(self, mock_configure):
        """Test creating Yahoo cache manager with cache directory."""
        manager = create_yahoo_cache_manager('/test/cache')
        
        assert isinstance(manager, YahooCacheManager)
        mock_configure.assert_called_once_with('/test/cache')
    
    def test_create_ibkr_connection_manager(self):
        """Test creating IBKR connection manager."""
        mock_ib = Mock()
        
        manager = create_ibkr_connection_manager(mock_ib, '127.0.0.1', 7497, 1)
        
        assert isinstance(manager, IBKRConnectionManager)
        assert manager.ib == mock_ib
        assert manager.ip_address == '127.0.0.1'
        assert manager.port == 7497
        assert manager.client_id == 1
    
    def test_create_barchart_http_client(self):
        """Test creating Barchart HTTP client."""
        mock_session = Mock()
        
        client = create_barchart_http_client(mock_session)
        
        assert isinstance(client, BarchartHTTPClient)
        assert client.session == mock_session
    
    def test_create_yahoo_data_fetcher(self):
        """Test creating Yahoo data fetcher."""
        fetcher = create_yahoo_data_fetcher()
        
        assert isinstance(fetcher, YahooDataFetcher)


@pytest.mark.unit
class TestProtocolCompliance:
    """Test that implementations comply with their protocols."""
    
    def test_yahoo_cache_manager_protocol_compliance(self):
        """Test YahooCacheManager implements CacheManagerProtocol."""
        manager = YahooCacheManager()
        
        # Should have required methods
        assert hasattr(manager, 'configure_cache')
        assert hasattr(manager, 'clear_cache')
        assert callable(manager.configure_cache)
        assert callable(manager.clear_cache)
    
    def test_ibkr_connection_manager_protocol_compliance(self):
        """Test IBKRConnectionManager implements ConnectionManagerProtocol."""
        mock_ib = Mock()
        manager = IBKRConnectionManager(mock_ib, '127.0.0.1', 7497, 1)
        
        # Should have required methods
        assert hasattr(manager, 'connect')
        assert hasattr(manager, 'disconnect') 
        assert hasattr(manager, 'is_connected')
        assert callable(manager.connect)
        assert callable(manager.disconnect)
        assert callable(manager.is_connected)
    
    def test_barchart_http_client_protocol_compliance(self):
        """Test BarchartHTTPClient implements HTTPClientProtocol."""
        mock_session = Mock()
        client = BarchartHTTPClient(mock_session)
        
        # Should have required methods
        assert hasattr(client, 'get')
        assert hasattr(client, 'post')
        assert callable(client.get)
        assert callable(client.post)
    
    def test_yahoo_data_fetcher_protocol_compliance(self):
        """Test YahooDataFetcher implements DataFetcherProtocol."""
        fetcher = YahooDataFetcher()
        
        # Should have required methods
        assert hasattr(fetcher, 'fetch_historical_data')
        assert callable(fetcher.fetch_historical_data)


@pytest.mark.unit
class TestProtocolTypes:
    """Test protocol type definitions."""
    
    def test_cache_manager_protocol_methods(self):
        """Test CacheManagerProtocol has expected method signatures."""
        # This is more of a compile-time check, but we can verify the protocol exists
        assert hasattr(CacheManagerProtocol, 'configure_cache')
        assert hasattr(CacheManagerProtocol, 'clear_cache')
    
    def test_connection_manager_protocol_methods(self):
        """Test ConnectionManagerProtocol has expected method signatures."""
        assert hasattr(ConnectionManagerProtocol, 'connect')
        assert hasattr(ConnectionManagerProtocol, 'disconnect')
        assert hasattr(ConnectionManagerProtocol, 'is_connected')
    
    def test_http_client_protocol_methods(self):
        """Test HTTPClientProtocol has expected method signatures."""
        assert hasattr(HTTPClientProtocol, 'get')
        assert hasattr(HTTPClientProtocol, 'post')
    
    def test_data_fetcher_protocol_methods(self):
        """Test DataFetcherProtocol has expected method signatures."""
        assert hasattr(DataFetcherProtocol, 'fetch_historical_data')