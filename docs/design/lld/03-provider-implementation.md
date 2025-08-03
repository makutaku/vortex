# Provider Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Provider Abstraction](../hld/04-provider-abstraction.md)

## 1. Data Provider Interface Implementation

### 1.1 Abstract Base Class Implementation
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import logging

class DataProvider(ABC):
    """Abstract base class for all data providers"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.authenticated = False
        self.rate_limiter = None
        self.session = None
        
    @abstractmethod
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Provider-specific authentication implementation"""
        pass
        
    @abstractmethod
    def get_data(self, instrument: 'Instrument', date_range: 'DateRange') -> pd.DataFrame:
        """Retrieve data for specified instrument and date range"""
        pass
        
    @abstractmethod
    def get_supported_instruments(self) -> List[str]:
        """Return list of supported instrument types"""
        pass
        
    def validate_instrument(self, instrument: 'Instrument') -> bool:
        """Validate instrument compatibility with provider"""
        supported = self.get_supported_instruments()
        return instrument.type in supported
        
    def get_rate_limits(self) -> Dict[str, int]:
        """Return current rate limit status"""
        if self.rate_limiter:
            return self.rate_limiter.get_status()
        return {"daily": -1, "hourly": -1, "remaining": -1}
```

### 1.2 Rate Limiting Implementation
```python
import time
from collections import defaultdict, deque
from threading import Lock

class RateLimiter:
    """Thread-safe rate limiter for API providers"""
    
    def __init__(self, daily_limit: int = None, hourly_limit: int = None, 
                 minute_limit: int = None):
        self.daily_limit = daily_limit
        self.hourly_limit = hourly_limit
        self.minute_limit = minute_limit
        
        self.daily_requests = deque()
        self.hourly_requests = deque()
        self.minute_requests = deque()
        
        self.lock = Lock()
        
    def can_make_request(self) -> bool:
        """Check if request can be made within limits"""
        with self.lock:
            now = time.time()
            self._cleanup_old_requests(now)
            
            if self.daily_limit and len(self.daily_requests) >= self.daily_limit:
                return False
            if self.hourly_limit and len(self.hourly_requests) >= self.hourly_limit:
                return False
            if self.minute_limit and len(self.minute_requests) >= self.minute_limit:
                return False
                
            return True
            
    def record_request(self):
        """Record a successful request"""
        with self.lock:
            now = time.time()
            self.daily_requests.append(now)
            self.hourly_requests.append(now)
            self.minute_requests.append(now)
            
    def get_wait_time(self) -> int:
        """Get seconds to wait before next request is allowed"""
        with self.lock:
            now = time.time()
            self._cleanup_old_requests(now)
            
            wait_times = []
            
            if self.daily_limit and len(self.daily_requests) >= self.daily_limit:
                oldest = self.daily_requests[0]
                wait_times.append(86400 - (now - oldest))
                
            if self.hourly_limit and len(self.hourly_requests) >= self.hourly_limit:
                oldest = self.hourly_requests[0]
                wait_times.append(3600 - (now - oldest))
                
            if self.minute_limit and len(self.minute_requests) >= self.minute_limit:
                oldest = self.minute_requests[0]
                wait_times.append(60 - (now - oldest))
                
            return max(wait_times) if wait_times else 0
```

## 2. Barchart Provider Implementation

### 2.1 Authentication Implementation
```python
import requests
from bs4 import BeautifulSoup
import re

class BarchartDataProvider(DataProvider):
    """Barchart.com data provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("barchart", config)
        self.base_url = "https://www.barchart.com"
        self.session = requests.Session()
        self.csrf_token = None
        self.rate_limiter = RateLimiter(daily_limit=150, hourly_limit=50)
        
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Implement Barchart session-based authentication"""
        try:
            # Step 1: Get login page and extract CSRF token
            login_page = self.session.get(f"{self.base_url}/login")
            soup = BeautifulSoup(login_page.content, 'html.parser')
            
            csrf_input = soup.find('input', {'name': '_token'})
            if not csrf_input:
                raise AuthenticationError("Could not find CSRF token")
            self.csrf_token = csrf_input['value']
            
            # Step 2: Submit login credentials
            login_data = {
                '_token': self.csrf_token,
                'email': credentials['username'],
                'password': credentials['password'],
                'remember': '1'
            }
            
            response = self.session.post(
                f"{self.base_url}/login",
                data=login_data,
                headers={'Referer': f"{self.base_url}/login"}
            )
            
            # Step 3: Verify successful login
            if 'dashboard' in response.url or response.status_code == 200:
                self.authenticated = True
                self.logger.info("Barchart authentication successful")
                return True
            else:
                self.logger.error("Barchart authentication failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False
    
    def get_data(self, instrument: 'Instrument', date_range: 'DateRange') -> pd.DataFrame:
        """Download historical data from Barchart"""
        if not self.authenticated:
            raise AuthenticationError("Must authenticate before downloading data")
            
        # Check rate limits
        if not self.rate_limiter.can_make_request():
            wait_time = self.rate_limiter.get_wait_time()
            raise RateLimitError(f"Rate limit exceeded, wait {wait_time} seconds")
            
        try:
            # Construct download URL
            download_url = self._build_download_url(instrument, date_range)
            
            # Make request with session
            response = self.session.get(download_url, timeout=60)
            response.raise_for_status()
            
            # Record successful request
            self.rate_limiter.record_request()
            
            # Parse CSV response
            return self._parse_csv_response(response.text, instrument)
            
        except Exception as e:
            self.logger.error(f"Data download failed: {e}")
            raise
            
    def _build_download_url(self, instrument: 'Instrument', date_range: 'DateRange') -> str:
        """Build Barchart download URL for instrument and date range"""
        symbol = instrument.symbol
        start_date = date_range.start.strftime('%Y%m%d')
        end_date = date_range.end.strftime('%Y%m%d')
        
        return (f"{self.base_url}/proxies/timeseries/queryeod.ashx?"
                f"symbol={symbol}&data=daily&maxrecords=640&"
                f"volume=contract&order=asc&dividends=false&"
                f"backadjust=false&daystoexpiration=1&"
                f"contractroll=expiration&"
                f"startdate={start_date}&enddate={end_date}")
```

## 3. Yahoo Finance Provider Implementation

### 3.1 RESTful API Implementation
```python
import yfinance as yf
from urllib.parse import urlencode
import json

class YahooDataProvider(DataProvider):
    """Yahoo Finance data provider implementation"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("yahoo", config)
        self.base_url = "https://query1.finance.yahoo.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Yahoo Finance requires no authentication for basic data"""
        self.authenticated = True
        return True
        
    def get_data(self, instrument: 'Instrument', date_range: 'DateRange') -> pd.DataFrame:
        """Download data using Yahoo Finance API"""
        try:
            # Use yfinance library for reliable data access
            ticker = yf.Ticker(instrument.symbol)
            
            data = ticker.history(
                start=date_range.start,
                end=date_range.end,
                interval='1d',
                auto_adjust=False,
                prepost=False
            )
            
            if data.empty:
                raise DataNotFoundError(f"No data found for {instrument.symbol}")
                
            # Convert to standard format
            return self._standardize_yahoo_data(data, instrument)
            
        except Exception as e:
            self.logger.error(f"Yahoo data download failed: {e}")
            raise
            
    def _standardize_yahoo_data(self, data: pd.DataFrame, instrument: 'Instrument') -> pd.DataFrame:
        """Convert Yahoo Finance data to standard OHLCV format"""
        standardized = pd.DataFrame()
        
        standardized['timestamp'] = data.index
        standardized['open'] = data['Open']
        standardized['high'] = data['High']
        standardized['low'] = data['Low']
        standardized['close'] = data['Close']
        standardized['volume'] = data['Volume']
        standardized['symbol'] = instrument.symbol
        standardized['provider'] = 'yahoo'
        
        return standardized.reset_index(drop=True)
```

## 4. Interactive Brokers Provider Implementation

### 4.1 TWS API Integration
```python
from ib_insync import IB, Stock, Future, Contract
import asyncio

class IbkrDataProvider(DataProvider):
    """Interactive Brokers data provider using TWS Gateway"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__("ibkr", config)
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 7497)
        self.client_id = config.get('client_id', 1)
        self.ib = IB()
        
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Connect to TWS/Gateway"""
        try:
            self.ib.connect(self.host, self.port, self.client_id)
            if self.ib.isConnected():
                self.authenticated = True
                self.logger.info("IBKR connection established")
                return True
            return False
        except Exception as e:
            self.logger.error(f"IBKR connection failed: {e}")
            return False
            
    def get_data(self, instrument: 'Instrument', date_range: 'DateRange') -> pd.DataFrame:
        """Request historical data from IBKR"""
        if not self.authenticated:
            raise AuthenticationError("Must connect to TWS/Gateway first")
            
        try:
            # Create contract specification
            contract = self._create_contract(instrument)
            
            # Request historical data
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime=date_range.end,
                durationStr=f"{(date_range.end - date_range.start).days} D",
                barSizeSetting='1 day',
                whatToShow='TRADES',
                useRTH=True
            )
            
            if not bars:
                raise DataNotFoundError(f"No data found for {instrument.symbol}")
                
            # Convert to DataFrame
            return self._convert_bars_to_dataframe(bars, instrument)
            
        except Exception as e:
            self.logger.error(f"IBKR data request failed: {e}")
            raise
            
    def _create_contract(self, instrument: 'Instrument') -> Contract:
        """Create IBKR contract specification"""
        if instrument.type == 'stock':
            return Stock(instrument.symbol, 'SMART', 'USD')
        elif instrument.type == 'future':
            return Future(instrument.symbol, instrument.exchange)
        else:
            raise ValueError(f"Unsupported instrument type: {instrument.type}")
```

## 5. Provider Factory Implementation

### 5.1 Dynamic Provider Creation
```python
class ProviderFactory:
    """Factory for creating configured data provider instances"""
    
    _providers = {
        'barchart': BarchartDataProvider,
        'yahoo': YahooDataProvider,
        'ibkr': IbkrDataProvider
    }
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> DataProvider:
        """Create provider instance with configuration"""
        if provider_type not in cls._providers:
            raise ValueError(f"Unknown provider type: {provider_type}")
            
        provider_class = cls._providers[provider_type]
        return provider_class(config)
        
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Return list of available provider types"""
        return list(cls._providers.keys())
        
    @classmethod
    def register_provider(cls, name: str, provider_class: type):
        """Register new provider implementation"""
        cls._providers[name] = provider_class
```

## Related Documents

- **[Provider Abstraction](../hld/04-provider-abstraction.md)** - High-level provider design
- **[Component Implementation](01-component-implementation.md)** - Component integration details
- **[Security Implementation](05-security-implementation.md)** - Credential security details

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** Senior Developer, Integration Engineer