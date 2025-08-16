# Provider Implementation Details

**Version:** 2.0  
**Date:** 2025-08-16  
**Related:** [Provider Abstraction](../hld/04-provider-abstraction.md)

## 1. Dependency Injection Provider Architecture

### 1.1 Protocol-Based Provider Interface

Vortex implements protocol-based dependency injection for provider abstractions, enabling testability and loose coupling.

**Core Provider Protocol (From `src/vortex/infrastructure/providers/interfaces.py`):**
```python
class DataProviderProtocol(Protocol):
    """Protocol defining provider interface contract"""
    
    def initialize(self, config: Any) -> bool:
        """Initialize provider with configuration"""
        ...
    
    def fetch_historical_data(self, instrument: 'Instrument', 
                            date_range: 'DateRange') -> pd.DataFrame:
        """Fetch historical market data"""
        ...
    
    def get_name(self) -> str:
        """Get provider name"""
        ...
    
    def get_supported_timeframes(self) -> List[str]:
        """Get supported time periods"""
        ...

# Dependency injection protocols
class HTTPClientProtocol(Protocol):
    """HTTP client abstraction"""
    def get(self, url: str, **kwargs) -> Any: ...
    def post(self, url: str, **kwargs) -> Any: ...

class CacheManagerProtocol(Protocol):
    """Cache management abstraction"""
    def configure_cache(self, cache_dir: str) -> None: ...
    def clear_cache(self) -> None: ...

class ConnectionManagerProtocol(Protocol):
    """Connection management abstraction"""
    def connect(self, **kwargs) -> bool: ...
    def disconnect(self) -> None: ...
    def is_connected(self) -> bool: ...
```

**Key Design Principles:**
- **Constructor injection**: Dependencies injected via constructor parameters
- **Explicit initialization**: Separate construction from initialization lifecycle
- **Protocol-based contracts**: Type-safe interfaces with runtime checking
- **Default implementations**: Fallback dependencies when not explicitly provided

**Source Reference:** `src/vortex/infrastructure/providers/interfaces.py`

### 1.2 Provider Factory with Dependency Injection

**Factory Pattern Implementation (From `src/vortex/infrastructure/providers/factory.py`):**
```python
class ProviderFactory:
    """Enhanced factory with comprehensive dependency injection"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
        self._providers = {
            'barchart': BarchartDataProvider,
            'yahoo': YahooDataProvider,
            'ibkr': IbkrDataProvider,
        }
        self._provider_builders = {
            'barchart': self._build_barchart_provider,
            'yahoo': self._build_yahoo_provider,
            'ibkr': self._build_ibkr_provider,
        }
    
    def create_provider(self, provider_name: str, 
                       config_overrides: Optional[Dict[str, Any]] = None) -> DataProviderProtocol:
        """Create provider with dependency injection"""
        
        # Get provider configuration
        provider_config = self._get_provider_config(provider_name, config_overrides)
        
        # Use builder method for provider-specific dependency injection
        builder_method = self._provider_builders.get(provider_name.lower())
        if not builder_method:
            raise PluginNotFoundError(f"Provider '{provider_name}' not supported")
        
        # Build provider with dependencies
        provider = builder_method(provider_config)
        
        # Initialize explicitly (separate from construction)
        if not provider.initialize(provider_config):
            raise ProviderError(f"Failed to initialize {provider_name} provider")
        
        return provider
    
    def _build_barchart_provider(self, config: BarchartProviderConfig) -> BarchartDataProvider:
        """Build Barchart provider with dependency injection"""
        # Create HTTP client dependency
        http_client = create_barchart_http_client(session=requests.Session())
        
        # Create authentication dependency
        auth = BarchartAuth()
        
        # Create circuit breaker dependency
        circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker.failure_threshold,
            reset_timeout=config.circuit_breaker.reset_timeout,
            name="barchart"
        )
        
        # Create client with injected dependencies
        client = BarchartClient(
            http_client=http_client,
            auth=auth,
            circuit_breaker=circuit_breaker
        )
        
        return BarchartDataProvider(client=client)
```

**Initialization Lifecycle Pattern:**
```python
# 1. Construct with dependencies (no side effects)
provider = BarchartDataProvider(client=injected_client)

# 2. Initialize explicitly (performs login/setup)
success = provider.initialize(config)
if not success:
    raise ProviderError("Initialization failed")

# 3. Use provider for operations
data = provider.fetch_historical_data(instrument, date_range)
```

**Source Reference:** `src/vortex/infrastructure/providers/factory.py`

## 2. Barchart Provider Implementation

### 2.1 HTTP Client with Authentication

**Barchart HTTP Client (From `src/vortex/infrastructure/providers/barchart/http_client.py`):**
```python
class BarchartHTTPClient:
    """HTTP client with session management and security"""
    
    def __init__(self, session: requests.Session, config: BarchartProviderConfig):
        self.session = session
        self.config = config
        self._configure_security()
    
    def _configure_security(self):
        """Configure session security settings"""
        self.session.verify = True  # Certificate validation
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; Vortex Financial Data Client)',
            'Accept': 'text/html,application/json',
            'Connection': 'keep-alive'
        })
    
    def authenticated_get(self, url: str, params: Dict[str, Any] = None) -> requests.Response:
        """Perform authenticated GET request"""
        if not url.startswith('https://'):
            raise SecurityError("Only HTTPS URLs allowed")
        
        response = self.session.get(
            url, 
            params=params, 
            timeout=self.config.request_timeout
        )
        response.raise_for_status()
        return response
```

### 2.2 Authentication with Session Management

**Barchart Auth Implementation (From `src/vortex/infrastructure/providers/barchart/auth.py`):**
```python
class BarchartAuth:
    """Barchart authentication with session management"""
    
    def __init__(self):
        self.session = None
        self.username = None
        self.last_login = None
        self.csrf_token = None
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate with Barchart.com"""
        try:
            self.session = requests.Session()
            self.username = username
            
            # 1. Get login page and extract CSRF token
            login_page = self.session.get("https://www.barchart.com/login")
            self.csrf_token = self.extract_xsrf_token(login_page.text)
            
            # 2. Submit login credentials
            login_data = {
                'email': username,
                'password': password,
                'remember': 'on',
                '_token': self.csrf_token
            }
            
            login_response = self.session.post(
                "https://www.barchart.com/login",
                data=login_data,
                allow_redirects=False
            )
            
            # 3. Validate authentication success
            if login_response.status_code in [302, 200]:
                self.last_login = datetime.now()
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Barchart authentication failed: {e}")
            return False
    
    def extract_xsrf_token(self, page_content: str) -> Optional[str]:
        """Extract CSRF token from login page"""
        # Implementation using BeautifulSoup or regex
        pass
```

### 2.3 Data Parsing with Configurable Methods

**Barchart Parser (From `src/vortex/infrastructure/providers/barchart/parser.py`):**
```python
class BarchartParser:
    """Configurable CSV parser for Barchart data"""
    
    def __init__(self, column_mapping: Optional[Dict[str, str]] = None):
        self.column_mapping = column_mapping or {
            'Time': 'timestamp',
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Last': 'close',
            'Volume': 'volume'
        }
    
    def convert_daily_csv_to_df(self, csv_content: str, symbol: str, 
                               **kwargs) -> pd.DataFrame:
        """Convert Barchart CSV to standard DataFrame (configurable instance method)"""
        
        # Parse CSV with configurable parameters
        df = pd.read_csv(io.StringIO(csv_content))
        
        # Apply column mapping (allows configuration override)
        column_mapping = kwargs.get('column_mapping', self.column_mapping)
        df = df.rename(columns=column_mapping)
        
        # Parse timestamps with configurable format
        timestamp_format = kwargs.get('timestamp_format', '%m/%d/%Y')
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format=timestamp_format)
            df.set_index('timestamp', inplace=True)
        
        # Convert to numeric types
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Apply custom transformations if provided
        if 'custom_transform' in kwargs:
            df = kwargs['custom_transform'](df)
        
        # Validate result
        if df.empty:
            raise BarchartParsingError("No valid data after parsing")
            
        return df
```

**Source Reference:** `src/vortex/infrastructure/providers/barchart/parser.py`

## 3. Yahoo Finance Provider Implementation

### 3.1 Cache-Enabled Yahoo Provider

**Yahoo Provider with Dependency Injection (From `src/vortex/infrastructure/providers/yahoo/provider.py`):**
```python
class YahooDataProvider:
    """Yahoo Finance provider with dependency injection"""
    
    def __init__(self, 
                 cache_manager: Optional[CacheManagerProtocol] = None,
                 data_fetcher: Optional[DataFetcherProtocol] = None):
        """Constructor with dependency injection (no auto-initialization)"""
        self.cache_manager = cache_manager
        self.data_fetcher = data_fetcher
        self._initialized = False
    
    def initialize(self) -> bool:
        """Initialize dependencies explicitly"""
        try:
            # Initialize cache manager
            if self.cache_manager is None:
                self.cache_manager = create_yahoo_cache_manager()
            
            # Initialize data fetcher
            if self.data_fetcher is None:
                self.data_fetcher = create_yahoo_data_fetcher()
            
            # Configure yfinance cache (removed from constructor)
            self.cache_manager.configure_cache(cache_dir=None)
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Yahoo provider initialization failed: {e}")
            return False
    
    def fetch_historical_data(self, instrument: 'Instrument', 
                            date_range: 'DateRange') -> pd.DataFrame:
        """Fetch data with caching and validation"""
        if not self._initialized:
            raise ProviderError("Provider not initialized")
        
        # Use injected data fetcher
        data = self.data_fetcher.fetch_historical_data(
            symbol=instrument.symbol,
            interval=self._map_period_to_interval(instrument.period),
            start_date=date_range.start,
            end_date=date_range.end
        )
        
        # Validate and standardize data
        return self._standardize_yahoo_data(data, instrument.symbol)
```

### 3.2 Data Fetcher Abstraction

**Yahoo Data Fetcher (From `src/vortex/infrastructure/providers/interfaces.py`):**
```python
class YahooDataFetcher:
    """Default Yahoo Finance data fetcher implementation"""
    
    def fetch_historical_data(self, symbol: str, interval: str, 
                            start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Fetch data using yfinance with built-in security"""
        import yfinance as yf
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval=interval,
            back_adjust=True,
            repair=True,
            raise_errors=True  # Fail fast on errors
        )
        return df
```

**Source Reference:** `src/vortex/infrastructure/providers/yahoo/provider.py`

## 4. Interactive Brokers Provider Implementation

### 4.1 Connection Manager Pattern

**IBKR Provider with Connection Management (From `src/vortex/infrastructure/providers/ibkr/provider.py`):**
```python
class IbkrDataProvider:
    """Interactive Brokers provider with connection manager injection"""
    
    def __init__(self, 
                 connection_manager: Optional[ConnectionManagerProtocol] = None):
        """Constructor with dependency injection (no auto-connection)"""
        self.connection_manager = connection_manager
        self.config = None
        self._initialized = False
    
    def initialize(self, config: 'IBKRProviderConfig') -> bool:
        """Initialize with explicit configuration and connection"""
        try:
            self.config = config
            
            # Create connection manager if not provided
            if self.connection_manager is None:
                from ib_insync import IB
                ib_client = IB()
                self.connection_manager = create_ibkr_connection_manager(
                    ib_client=ib_client,
                    ip_address=config.host,
                    port=config.port,
                    client_id=config.client_id
                )
            
            # Establish connection (removed from constructor)
            success = self.connection_manager.connect(timeout=config.connection_timeout)
            if success:
                self._initialized = True
                logger.info("IBKR provider initialized successfully")
                return True
            else:
                logger.error("Failed to establish IBKR connection")
                return False
                
        except Exception as e:
            logger.error(f"IBKR provider initialization failed: {e}")
            return False
    
    def fetch_historical_data(self, instrument: 'Instrument', 
                            date_range: 'DateRange') -> pd.DataFrame:
        """Fetch historical data from TWS/Gateway"""
        if not self._initialized:
            raise ProviderError("Provider not initialized")
            
        if not self.connection_manager.is_connected():
            raise ProviderError("Not connected to TWS/Gateway")
        
        # Map parameters using configurable instance methods
        duration_str = self.map_date_range_to_duration(date_range)
        bar_size = self.map_period_to_bar_size(instrument.period)
        
        # Create IBKR contract
        contract = self._create_contract(instrument)
        
        # Request data through connection manager
        bars = self.connection_manager.request_historical_data(
            contract=contract,
            duration=duration_str,
            bar_size=bar_size
        )
        
        return self._convert_bars_to_dataframe(bars, instrument.symbol)
    
    def map_date_range_to_duration(self, date_range: 'DateRange', 
                                 **kwargs) -> str:
        """Map date range to IBKR duration (configurable instance method)"""
        days = (date_range.end - date_range.start).days
        
        # Allow configuration override
        if 'duration_override' in kwargs:
            return kwargs['duration_override']
            
        if days <= 30:
            return f"{days} D"
        elif days <= 365:
            return f"{days // 7} W"
        else:
            return f"{days // 365} Y"
    
    def map_period_to_bar_size(self, period: str, **kwargs) -> str:
        """Map period to IBKR bar size (configurable instance method)"""
        mapping = {
            '1m': '1 min', '5m': '5 mins', '15m': '15 mins',
            '30m': '30 mins', '1h': '1 hour', '1d': '1 day',
            '1W': '1 week', '1M': '1 month'
        }
        
        # Allow configuration override
        if 'bar_size_override' in kwargs:
            return kwargs['bar_size_override']
            
        return mapping.get(period, '1 day')
```

**Source Reference:** `src/vortex/infrastructure/providers/ibkr/provider.py`

## 5. Data Validation and Schema Implementation

### 5.1 Column Constants and Validation

**OHLCV Schema Validation (From `src/vortex/models/column_constants.py`):**
```python
class ColumnConstants:
    """Standardized column definitions and validation"""
    
    # Required OHLCV columns
    REQUIRED_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    OPTIONAL_COLUMNS = ['symbol', 'provider', 'adjusted_close']
    
    # Data type specifications
    COLUMN_TYPES = {
        'timestamp': 'datetime64[ns]',
        'open': 'float64',
        'high': 'float64',
        'low': 'float64', 
        'close': 'float64',
        'volume': 'int64',
        'symbol': 'object'
    }
    
    @classmethod
    def validate_required_columns(cls, df: pd.DataFrame, provider: str = None) -> List[str]:
        """Validate required columns presence"""
        missing_columns = [col for col in cls.REQUIRED_COLUMNS if col not in df.columns]
        
        if missing_columns:
            logger.warning(f"Missing columns in {provider} data: {missing_columns}")
            
        return missing_columns
    
    @classmethod
    def validate_column_data_types(cls, df: pd.DataFrame) -> List[str]:
        """Validate OHLCV data types"""
        type_errors = []
        
        for col, expected_type in cls.COLUMN_TYPES.items():
            if col in df.columns:
                actual_type = str(df[col].dtype)
                if not cls._is_compatible_type(actual_type, expected_type):
                    type_errors.append(f"{col}: expected {expected_type}, got {actual_type}")
        
        return type_errors
    
    @classmethod
    def standardize_dataframe_columns(cls, df: pd.DataFrame, strict: bool = False) -> pd.DataFrame:
        """Standardize DataFrame to OHLCV format"""
        # Validate columns
        missing = cls.validate_required_columns(df)
        if strict and missing:
            raise ValidationError(f"Cannot standardize: missing {missing}")
        
        # Select available standard columns
        available_standard = [col for col in cls.REQUIRED_COLUMNS + cls.OPTIONAL_COLUMNS 
                            if col in df.columns]
        
        return df[available_standard].copy()
```

### 5.2 Business Rule Validation

**OHLCV Business Rules:**
```python
def validate_ohlcv_relationships(df: pd.DataFrame) -> List[str]:
    """Validate OHLCV business logic relationships"""
    violations = []
    
    # High must be >= max(Open, Close)
    high_violations = df[df['high'] < df[['open', 'close']].max(axis=1)]
    if not high_violations.empty:
        violations.append(f"High < max(Open,Close) in {len(high_violations)} rows")
    
    # Low must be <= min(Open, Close)  
    low_violations = df[df['low'] > df[['open', 'close']].min(axis=1)]
    if not low_violations.empty:
        violations.append(f"Low > min(Open,Close) in {len(low_violations)} rows")
    
    # Volume must be non-negative
    if 'volume' in df.columns:
        negative_volume = df[df['volume'] < 0]
        if not negative_volume.empty:
            violations.append(f"Negative volume in {len(negative_volume)} rows")
    
    return violations
```

**Source Reference:** `src/vortex/models/column_constants.py`

## 6. Resilience and Circuit Breaker Implementation

### 6.1 Circuit Breaker Pattern

**Circuit Breaker with Correlation Tracking (From `src/vortex/infrastructure/resilience/circuit_breaker.py`):**
```python
class CircuitBreaker:
    """Circuit breaker implementation with correlation tracking"""
    
    def __init__(self, failure_threshold: int = 5, 
                 reset_timeout: int = 60,
                 name: str = "default"):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.name = name
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.Lock()
        self.correlation_manager = get_correlation_manager()
    
    def call(self, func: callable, *args, **kwargs):
        """Execute function through circuit breaker"""
        correlation_id = self.correlation_manager.get_current_id()
        
        # Check circuit state
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker {self.name} is OPEN",
                        correlation_id=correlation_id
                    )
        
        try:
            # Execute with correlation context
            with self.correlation_manager.correlation_context(correlation_id):
                result = func(*args, **kwargs)
            
            # Success - reset failure count
            with self.lock:
                if self.failure_count > 0:
                    logger.info(f"Circuit breaker {self.name} recovered")
                    
                self.failure_count = 0
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
            
            return result
            
        except Exception as e:
            self._handle_failure(e, correlation_id)
            raise
    
    def _handle_failure(self, exception: Exception, correlation_id: str):
        """Handle circuit breaker failure with correlation"""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            logger.warning(
                f"Circuit breaker {self.name} failure {self.failure_count}/{self.failure_threshold}",
                extra={'correlation_id': correlation_id, 'exception': str(exception)}
            )
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                logger.error(f"Circuit breaker {self.name} OPENED")
```

**Source Reference:** `src/vortex/infrastructure/resilience/circuit_breaker.py`

### 6.2 Retry Strategy with Exponential Backoff

**Retry Logic Implementation (From `src/vortex/infrastructure/resilience/retry.py`):**
```python
class RetryStrategy:
    """Configurable retry with exponential backoff and correlation"""
    
    def __init__(self, max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 backoff_factor: float = 2.0):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
    
    def execute(self, func: callable, *args, **kwargs):
        """Execute function with retry logic and correlation"""
        correlation_id = get_correlation_manager().get_current_id()
        last_exception = None
        
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                
                if attempt > 1:
                    logger.info(f"Retry succeeded on attempt {attempt}",
                              extra={'correlation_id': correlation_id})
                
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt == self.max_attempts or not self._should_retry(e):
                    break
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt} failed, retrying in {delay:.1f}s",
                             extra={'correlation_id': correlation_id})
                
                time.sleep(delay)
        
        raise last_exception
    
    def _should_retry(self, exception: Exception) -> bool:
        """Determine if exception is retryable"""
        # Don't retry authentication errors
        if isinstance(exception, (AuthenticationError, AuthorizationError)):
            return False
        
        # Don't retry validation errors
        if isinstance(exception, ValidationError):
            return False
        
        # Retry network and server errors
        if isinstance(exception, (requests.exceptions.RequestException, ServerError)):
            return True
        
        return False
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff"""
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        return min(delay, self.max_delay)
```

**Source Reference:** `src/vortex/infrastructure/resilience/retry.py`

## 7. Configuration and Provider Management

### 7.1 Configuration Models

**Provider Configuration Classes (From `src/vortex/infrastructure/providers/config.py`):**
```python
class BarchartProviderConfig(BaseModel):
    """Barchart provider configuration with validation"""
    
    username: str = Field(..., description="Barchart username")
    password: str = Field(..., description="Barchart password") 
    daily_limit: int = Field(default=150, description="Daily download limit")
    request_timeout: int = Field(default=30, description="Request timeout seconds")
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v

class YahooProviderConfig(BaseModel):
    """Yahoo Finance provider configuration"""
    
    cache_enabled: bool = Field(default=True, description="Enable data caching")
    max_cache_size: int = Field(default=1000, description="Maximum cache entries")
    request_timeout: int = Field(default=30, description="Request timeout seconds")

class IBKRProviderConfig(BaseModel):
    """Interactive Brokers provider configuration"""
    
    host: str = Field(default="localhost", description="TWS/Gateway host")
    port: int = Field(default=7497, description="TWS/Gateway port")
    client_id: int = Field(default=1, description="Client ID")
    connection_timeout: int = Field(default=30, description="Connection timeout")
    
    @validator('port')
    def validate_port(cls, v):
        if not (1024 <= v <= 65535):
            raise ValueError("Port must be between 1024 and 65535")
        return v
```

**Source Reference:** `src/vortex/infrastructure/providers/config.py`

### 7.2 Provider Builder Pattern

**Provider Builders (From `src/vortex/infrastructure/providers/builders.py`):**
```python
class BarchartProviderBuilder:
    """Builder for Barchart provider with dependency injection"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def build(self, config_overrides: Optional[Dict[str, Any]] = None) -> BarchartDataProvider:
        """Build Barchart provider with all dependencies"""
        
        # Get configuration
        config = self._build_config(config_overrides)
        
        # Create dependencies
        http_client = create_barchart_http_client(session=requests.Session())
        auth = BarchartAuth()
        circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker.failure_threshold,
            reset_timeout=config.circuit_breaker.reset_timeout,
            name="barchart"
        )
        
        # Create client with dependencies
        client = BarchartClient(
            http_client=http_client,
            auth=auth,
            circuit_breaker=circuit_breaker
        )
        
        return BarchartDataProvider(client=client)
    
    def _build_config(self, overrides: Optional[Dict[str, Any]] = None) -> BarchartProviderConfig:
        """Build configuration with overrides"""
        base_config = self.config_manager.get_provider_config('barchart')
        
        if overrides:
            config_dict = base_config.dict()
            config_dict.update(overrides)
            return BarchartProviderConfig(**config_dict)
        
        return base_config

class YahooProviderBuilder:
    """Builder for Yahoo provider with dependency injection"""
    
    def build(self, config_overrides: Optional[Dict[str, Any]] = None) -> YahooDataProvider:
        """Build Yahoo provider with dependencies"""
        
        # Create cache manager
        cache_manager = create_yahoo_cache_manager()
        
        # Create data fetcher
        data_fetcher = create_yahoo_data_fetcher()
        
        return YahooDataProvider(
            cache_manager=cache_manager,
            data_fetcher=data_fetcher
        )
```

**Source Reference:** `src/vortex/infrastructure/providers/builders.py`

## 8. Correlation and Request Tracking

### 8.1 Correlation ID Management

**Thread-Safe Correlation Tracking (From `src/vortex/core/correlation/manager.py`):**
```python
class CorrelationIdManager:
    """Thread-local correlation ID management"""
    
    @staticmethod
    @contextmanager
    def correlation_context(correlation_id: Optional[str] = None,
                          operation: Optional[str] = None,
                          provider: Optional[str] = None):
        """Context manager for correlation tracking"""
        
        correlation_id = correlation_id or CorrelationIdManager.generate_id()
        
        context = CorrelationContext(
            correlation_id=correlation_id,
            operation=operation,
            provider=provider,
            start_time=datetime.now()
        )
        
        try:
            CorrelationIdManager.set_context(context)
            logger.info("Operation started", 
                       extra={'correlation_id': correlation_id})
            
            yield context
            
            elapsed = context.elapsed_seconds()
            logger.info("Operation completed successfully",
                       extra={'correlation_id': correlation_id, 'elapsed': elapsed})
            
        except Exception as e:
            logger.error("Operation failed",
                        extra={'correlation_id': correlation_id, 'error': str(e)})
            raise
        finally:
            CorrelationIdManager.clear_context()

# Decorator for automatic correlation tracking
@with_correlation
def fetch_with_correlation(provider: DataProviderProtocol, instrument: 'Instrument'):
    """Example of correlation-aware provider operation"""
    correlation_id = get_correlation_manager().get_current_id()
    
    # All provider operations inherit correlation context
    return provider.fetch_historical_data(instrument, date_range)
```

**Source Reference:** `src/vortex/core/correlation/manager.py`

## 9. Testing Implementation Patterns

### 9.1 Dependency Injection Testing

**Provider Testing with Mocks:**
```python
class TestBarchartProvider:
    """Test Barchart provider with dependency injection"""
    
    def test_provider_with_mock_dependencies(self):
        """Test provider using mock dependencies"""
        
        # Create mock dependencies
        mock_http_client = Mock(spec=HTTPClientProtocol)
        mock_auth = Mock(spec=BarchartAuth)
        mock_circuit_breaker = Mock(spec=CircuitBreaker)
        
        # Configure mock responses
        mock_http_client.get.return_value.text = "mock,csv,data"
        mock_auth.login.return_value = True
        mock_circuit_breaker.call.side_effect = lambda f, *args: f(*args)
        
        # Create client with injected mocks
        client = BarchartClient(
            http_client=mock_http_client,
            auth=mock_auth,
            circuit_breaker=mock_circuit_breaker
        )
        
        provider = BarchartDataProvider(client=client)
        
        # Test initialization
        config = BarchartProviderConfig(username="test", password="test123")
        assert provider.initialize(config) is True
        
        # Verify mock interactions
        mock_auth.login.assert_called_once_with("test", "test123")
        
    def test_provider_factory_dependency_injection(self):
        """Test factory-created providers"""
        
        factory = ProviderFactory()
        
        # Create provider with custom configuration
        provider = factory.create_provider('barchart', {
            'username': 'test_user',
            'password': 'test_pass',
            'daily_limit': 100
        })
        
        assert isinstance(provider, BarchartDataProvider)
        assert provider.client is not None
```

**Source Reference:** `tests/unit/infrastructure/providers/test_barchart_provider.py`

### 9.2 Integration Testing Patterns

**End-to-End Provider Testing:**
```python
class TestProviderIntegration:
    """End-to-end provider integration testing"""
    
    @pytest.mark.integration
    def test_complete_download_workflow(self):
        """Test complete download workflow with real providers"""
        
        # Setup correlation context
        correlation_id = "test-e2e-workflow"
        
        with get_correlation_manager().correlation_context(correlation_id):
            # Create provider through factory
            factory = ProviderFactory()
            provider = factory.create_provider('yahoo')
            
            # Create test instrument
            instrument = Stock(symbol="AAPL", periods="1d")
            date_range = DateRange(
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 7)
            )
            
            # Execute download
            data = provider.fetch_historical_data(instrument, date_range)
            
            # Validate data
            assert isinstance(data, pd.DataFrame)
            assert len(data) > 0
            
            # Validate OHLCV schema
            missing_columns = ColumnConstants.validate_required_columns(data)
            assert len(missing_columns) == 0
            
            # Validate business rules
            ohlcv_violations = validate_ohlcv_relationships(data)
            assert len(ohlcv_violations) == 0
```

**Source Reference:** `tests/integration/test_provider_downloader_integration.py`

## 10. Implementation Summary

### 10.1 Architecture Achievements

**✅ Dependency Injection Implementation:**
- Protocol-based interfaces with default implementations
- Constructor injection with explicit initialization lifecycle  
- Configurable dependencies for HTTP clients, caches, connection managers
- Factory pattern with builder support for complex provider creation

**✅ Provider Abstraction Implementation:**
- Barchart: HTTP client with session-based authentication and CSRF handling
- Yahoo Finance: Cache manager and data fetcher injection with yfinance integration
- IBKR: Connection manager for TWS/Gateway communication with proper lifecycle management
- Standardized OHLCV data format with comprehensive validation

**✅ Resilience Implementation:**
- Circuit breaker pattern with correlation tracking and configurable thresholds
- Retry logic with exponential backoff and jitter for transient failures
- Structured exception hierarchy with actionable error messages and resolution steps

**✅ Configuration Implementation:**
- TOML-based configuration with Pydantic models and validation
- Environment variable overrides with proper precedence handling
- Provider-specific configuration sections with type safety

### 10.2 Implementation Patterns Summary

| Pattern | Purpose | Location | Benefits |
|---------|---------|----------|----------|
| **Dependency Injection** | Loose coupling | `interfaces.py` | Testability, flexibility |
| **Circuit Breaker** | Fault isolation | `resilience/circuit_breaker.py` | Prevents cascade failures |
| **Retry Strategy** | Transient error recovery | `resilience/retry.py` | Network resilience |
| **Correlation Tracking** | Request tracing | `core/correlation/` | End-to-end observability |
| **Configuration Models** | Type-safe config | `providers/config.py` | Validation, documentation |
| **Factory + Builder** | Provider creation | `factory.py`, `builders.py` | Centralized construction |

The current implementation provides production-ready patterns for financial data provider integration with comprehensive dependency injection, resilience, and observability features.

## Related Documents

- **[Provider Abstraction](../hld/04-provider-abstraction.md)** - High-level provider design
- **[Component Implementation](01-component-implementation.md)** - Overall component implementation
- **[Data Flow Design](../hld/03-data-flow-design.md)** - Data flow architecture
- **[Integration Design](../hld/08-integration-design.md)** - External integration patterns

---

**Next Review:** 2026-02-16  
**Reviewers:** Senior Developer, Integration Engineer, QA Lead