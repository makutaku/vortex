# Provider Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Provider Abstraction](../hld/04-provider-abstraction.md)

## 1. Data Provider Interface

### 1.1 Core Interface Contract
The abstract base class defines the contract all providers must implement:

```python
class DataProvider(ABC):
    """Abstract base class for all data providers"""
    
    @abstractmethod
    def authenticate(self, credentials: Dict[str, str]) -> bool:
        """Provider-specific authentication implementation"""
        
    @abstractmethod
    def get_data(self, instrument: 'Instrument', date_range: 'DateRange') -> pd.DataFrame:
        """Retrieve data for specified instrument and date range"""
        
    @abstractmethod
    def get_supported_instruments(self) -> List[str]:
        """Return list of supported instrument types"""
```

**Key Design Decisions:**
- **Stateful authentication**: Providers maintain authentication state
- **Unified data format**: All providers return standardized DataFrames
- **Rate limit awareness**: Built-in rate limiting support

**Source Reference:** `src/vortex/data_providers/data_provider.py`

### 1.2 Rate Limiting Strategy

**Algorithm: Token Bucket Rate Limiter**
```
MAINTAIN three sliding windows:
  - daily_window (24 hours)
  - hourly_window (60 minutes)  
  - minute_window (60 seconds)

ON each request:
  1. Remove expired entries from windows
  2. Check if request count < limit for all windows
  3. If allowed: record timestamp, return true
  4. If blocked: calculate wait time, return false
```

**Key Implementation Points:**
- Thread-safe with locking mechanism
- Multiple time window support
- Automatic cleanup of old requests

**Source Reference:** `src/vortex/data_providers/rate_limiter.py`

## 2. Provider Implementations

### 2.1 Barchart Provider

**Authentication Flow:**
```
1. GET /login → Extract CSRF token from form
2. POST /login with credentials + CSRF token
3. Verify redirect to dashboard
4. Store session cookies for subsequent requests
```

**Data Retrieval Pattern:**
```python
def get_data(self, instrument, date_range):
    # Key steps only
    if not self.rate_limiter.can_make_request():
        wait_time = self.rate_limiter.get_wait_time()
        raise RateLimitError(f"Wait {wait_time}s")
    
    url = self._build_download_url(instrument, date_range)
    response = self.session.get(url, timeout=60)
    
    return self._parse_csv_response(response.text)
```

**Configuration:**
- Daily limit: 150 requests
- Session-based authentication
- CSV response format

**Source Reference:** `src/vortex/data_providers/barchart_provider.py`

### 2.2 Yahoo Finance Provider

**Authentication:**
- No authentication required for basic data
- User-Agent header for request identification

**Data Access Pattern:**
```python
# Using yfinance library
ticker = yf.Ticker(instrument.symbol)
data = ticker.history(
    start=date_range.start,
    end=date_range.end,
    interval='1d'
)
```

**Data Standardization:**
```
Yahoo Format → Standard OHLCV:
  - Index → timestamp column
  - Capitalize column names → lowercase
  - Add metadata (symbol, provider)
```

**Source Reference:** `src/vortex/data_providers/yahoo_provider.py`

### 2.3 Interactive Brokers Provider

**Connection Management:**
```
1. Connect to TWS/Gateway on specified host:port
2. Verify connection status
3. Create contract specifications
4. Request historical data with parameters
```

**Contract Specification Pattern:**
```python
# Pseudo-code for contract creation
IF instrument.type == 'stock':
    contract = Stock(symbol, 'SMART', 'USD')
ELIF instrument.type == 'future':
    contract = Future(symbol, exchange)
```

**Key Features:**
- Real-time connection monitoring
- Multi-asset support
- Event-driven data delivery

**Source Reference:** `src/vortex/data_providers/ibkr_provider.py`

## 3. Provider Factory Pattern

### 3.1 Dynamic Provider Creation

**Factory Registry:**
```python
_providers = {
    'barchart': BarchartDataProvider,
    'yahoo': YahooDataProvider,
    'ibkr': IbkrDataProvider
}
```

**Creation Pattern:**
```
1. Validate provider type exists in registry
2. Instantiate provider class with configuration
3. Return configured provider instance
```

**Extensibility:**
- New providers register via `register_provider(name, class)`
- Configuration passed through to provider constructors
- Runtime provider discovery

**Source Reference:** `src/vortex/data_providers/factory.py`

## 4. Error Handling Patterns

### 4.1 Provider-Specific Exceptions

**Exception Hierarchy:**
```
DataProviderError
├── AuthenticationError
├── RateLimitError  
├── DataNotFoundError
└── ConnectionError
```

**Recovery Strategies:**
| Error Type | Recovery Action | Retry Strategy |
|------------|----------------|----------------|
| Authentication | Re-authenticate | Immediate retry once |
| Rate Limit | Wait specified time | Delayed retry |
| Connection | Exponential backoff | Max 3 retries |
| Data Not Found | No recovery | Fail immediately |

**Source Reference:** `src/vortex/data_providers/exceptions.py`

## 5. Testing Approach

### 5.1 Mock Provider Pattern

**Mock Provider Structure:**
```python
class MockDataProvider:
    """Simplified mock for testing"""
    
    def __init__(self, return_data=None):
        self.call_history = []
        self.return_data = return_data
        
    def get_data(self, instrument, date_range):
        self.call_history.append(('get_data', instrument, date_range))
        return self.return_data or self._generate_mock_data()
```

**Test Scenarios:**
- Authentication success/failure
- Rate limit enforcement
- Data format validation
- Error condition handling

**Source Reference:** `tests/test_providers/mock_provider.py`

## 6. Configuration Examples

### 6.1 Provider Configuration

**Barchart Configuration:**
```json
{
  "provider_type": "barchart",
  "username": "${VORTEX_BARCHART_USERNAME}",
  "password": "${VORTEX_BARCHART_PASSWORD}",
  "daily_limit": 150,
  "timeout_seconds": 60
}
```

**IBKR Configuration:**
```json
{
  "provider_type": "ibkr",
  "host": "localhost",
  "port": 7497,
  "client_id": 1
}
```

**Environment Variables:**
```bash
VORTEX_DEFAULT_PROVIDER=barchart
VORTEX_BARCHART_USERNAME=user@example.com
VORTEX_BARCHART_PASSWORD=secure_password
```

## Related Documents

- **[Provider Abstraction](../hld/04-provider-abstraction.md)** - High-level provider design
- **[Component Implementation](01-component-implementation.md)** - Component integration details
- **[Security Implementation](05-security-implementation.md)** - Credential security details

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** Senior Developer, Integration Engineer