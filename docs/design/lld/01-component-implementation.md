# Component Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Component Architecture](../hld/02-component-architecture.md)

## 1. Download Manager Implementation

### 1.1 Core Workflow Implementation
```python
class UpdatingDownloader:
    def __init__(self, data_storage, data_provider, backup_storage=None):
        self.data_storage = data_storage
        self.data_provider = data_provider
        self.backup_storage = backup_storage
        self.logger = logging.getLogger(__name__)
        
    def download_instrument_data(self, config):
        try:
            # 1. Create download job
            job = DownloadJob.from_config(config)
            self.logger.info(f"Starting download for {job.instrument.symbol}")
            
            # 2. Check for existing data
            if self.data_storage.has_recent_data(job):
                return self._handle_incremental_update(job)
            
            # 3. Fetch from provider
            raw_data = self.data_provider.get_data(job.instrument, job.date_range)
            
            # 4. Validate data quality
            validated_data = self.validator.validate(raw_data)
            if not validated_data.is_valid:
                raise DataValidationError(f"Data validation failed: {validated_data.errors}")
            
            # 5. Store data
            save_result = self.data_storage.save(validated_data.data, job.output_path)
            
            # 6. Update metadata
            self.metadata.record_download(job, success=True, row_count=len(validated_data.data))
            
            self.logger.info(f"Download completed: {save_result.row_count} rows saved")
            return True
            
        except Exception as e:
            self.logger.error(f"Download failed for {job.instrument.symbol}: {e}")
            self._handle_download_error(job, e)
            return False
    
    def _handle_incremental_update(self, job):
        """Handle incremental data updates"""
        existing_data = self.data_storage.load(job.output_path)
        last_timestamp = existing_data['timestamp'].max()
        
        # Fetch only new data since last update
        incremental_range = DateRange(
            start=last_timestamp + timedelta(days=1),
            end=job.date_range.end
        )
        
        if incremental_range.start > incremental_range.end:
            self.logger.info(f"No new data needed for {job.instrument.symbol}")
            return True
        
        # Fetch and append new data
        new_data = self.data_provider.get_data(job.instrument, incremental_range)
        combined_data = pd.concat([existing_data, new_data]).drop_duplicates()
        
        return self.data_storage.save(combined_data, job.output_path)
    
    def _handle_download_error(self, job, error):
        """Handle download errors with appropriate recovery actions"""
        error_type = type(error).__name__
        
        if isinstance(error, RateLimitError):
            # Schedule retry after rate limit period
            retry_time = error.retry_after
            self.logger.warning(f"Rate limited, will retry in {retry_time} seconds")
            self.scheduler.schedule_retry(job, delay=retry_time)
            
        elif isinstance(error, AuthenticationError):
            # Re-authenticate and retry
            self.logger.warning("Authentication failed, attempting re-authentication")
            if self.data_provider.authenticate():
                self.scheduler.schedule_retry(job, delay=5)
            else:
                self.logger.error("Re-authentication failed, manual intervention required")
                
        elif isinstance(error, ConnectionError):
            # Exponential backoff retry
            retry_count = job.retry_count + 1
            if retry_count <= MAX_RETRIES:
                delay = min(300, 2 ** retry_count)  # Max 5 minutes
                self.logger.warning(f"Connection error, retry {retry_count} in {delay}s")
                job.retry_count = retry_count
                self.scheduler.schedule_retry(job, delay=delay)
            else:
                self.logger.error(f"Max retries exceeded for {job.instrument.symbol}")
                
        else:
            # Log unknown error and fail
            self.logger.error(f"Unknown error type {error_type}: {error}")
            self.metadata.record_download(job, success=False, error=str(error))
```

### 1.2 Job Management Implementation
```python
class DownloadJob:
    def __init__(self, instrument, date_range, provider, output_path, retry_config=None):
        self.job_id = str(uuid.uuid4())
        self.instrument = instrument
        self.date_range = date_range
        self.provider = provider
        self.output_path = output_path
        self.retry_config = retry_config or RetryConfig()
        self.retry_count = 0
        self.status = JobStatus.PENDING
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
    
    @classmethod
    def from_config(cls, config):
        """Create download job from configuration"""
        instrument = InstrumentFactory.create_instrument(config.instrument_config)
        date_range = DateRange(config.start_date, config.end_date)
        output_path = cls._generate_output_path(instrument, date_range, config.output_directory)
        
        return cls(
            instrument=instrument,
            date_range=date_range,
            provider=config.provider,
            output_path=output_path,
            retry_config=config.retry_config
        )
    
    @staticmethod
    def _generate_output_path(instrument, date_range, base_directory):
        """Generate standardized output file path"""
        symbol = instrument.symbol.replace('/', '_')  # Handle forex pairs
        start_str = date_range.start.strftime('%Y%m%d')
        end_str = date_range.end.strftime('%Y%m%d')
        filename = f"{symbol}_1D_{start_str}_{end_str}.csv"
        
        # Create subdirectory by instrument type
        if isinstance(instrument, Future):
            subdir = "futures"
        elif isinstance(instrument, Stock):
            subdir = "stocks"
        elif isinstance(instrument, Forex):
            subdir = "forex"
        else:
            subdir = "other"
        
        return Path(base_directory) / subdir / filename
    
    def mark_started(self):
        """Mark job as started"""
        self.status = JobStatus.IN_PROGRESS
        self.started_at = datetime.utcnow()
    
    def mark_completed(self, success=True, error_message=None):
        """Mark job as completed"""
        self.status = JobStatus.COMPLETED if success else JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
    
    @property
    def duration(self):
        """Calculate job execution duration"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
```

## 2. Instrument Model Implementation

### 2.1 Future Contract Implementation
```python
class Future(Instrument):
    def __init__(self, symbol, code, cycle, tick_date, exchange):
        super().__init__(symbol)
        self.code = code  # e.g., "GC" for Gold
        self.cycle = cycle  # e.g., "GJMQVZ"
        self.tick_date = tick_date
        self.exchange = exchange
        self.contract_size = self._get_contract_size()
        self.tick_value = self._get_tick_value()
    
    def get_active_contracts(self, start_date, end_date):
        """Generate list of active contracts in date range"""
        contracts = []
        for month_code in self.cycle:
            for year in range(start_date.year, end_date.year + 2):  # Include next year
                contract = FutureContract(
                    symbol=f"{self.code}{month_code}{year%100:02d}",
                    code=self.code,
                    month_code=month_code,
                    year=year,
                    expiry=self._calculate_expiry(month_code, year),
                    exchange=self.exchange
                )
                if self._is_active_during(contract, start_date, end_date):
                    contracts.append(contract)
        return sorted(contracts, key=lambda c: c.expiry)
    
    def _calculate_expiry(self, month_code, year):
        """Calculate contract expiry based on exchange rules"""
        month_map = {'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6,
                    'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12}
        month = month_map[month_code]
        
        # Exchange-specific expiry logic
        if self.exchange == "COMEX":  # Gold, Silver
            # Third-to-last business day of delivery month
            expiry_day = self._get_third_to_last_business_day(year, month)
        elif self.exchange == "CBOT":  # Corn, Wheat, Soybeans
            # Business day prior to 15th of delivery month
            expiry_day = self._get_business_day_before_15th(year, month)
        elif self.exchange == "CME":  # S&P, Currencies
            # Third Friday of delivery month
            expiry_day = self._get_third_friday(year, month)
        else:
            # Default: 15th of month
            expiry_day = 15
        
        return datetime(year, month, expiry_day)
    
    def _is_active_during(self, contract, start_date, end_date):
        """Check if contract is active during date range"""
        # Contract is active from first notice day to expiry
        first_notice = contract.expiry - timedelta(days=30)  # Approximate
        return not (contract.expiry < start_date or first_notice > end_date)
    
    def _get_contract_size(self):
        """Get contract size based on instrument code"""
        sizes = {
            'GC': 100,    # Gold: 100 troy ounces
            'SI': 5000,   # Silver: 5000 troy ounces
            'CL': 1000,   # Crude Oil: 1000 barrels
            'NG': 10000,  # Natural Gas: 10000 MMBtu
            'ES': 50,     # E-mini S&P: $50 per point
            'NQ': 20,     # E-mini Nasdaq: $20 per point
        }
        return sizes.get(self.code, 1)
    
    def _get_tick_value(self):
        """Get minimum tick value"""
        tick_values = {
            'GC': 0.10,   # Gold: $0.10 per troy ounce
            'SI': 0.005,  # Silver: $0.005 per troy ounce
            'CL': 0.01,   # Crude Oil: $0.01 per barrel
            'NG': 0.001,  # Natural Gas: $0.001 per MMBtu
            'ES': 0.25,   # E-mini S&P: 0.25 points
            'NQ': 0.25,   # E-mini Nasdaq: 0.25 points
        }
        return tick_values.get(self.code, 0.01)
```

### 2.2 Stock Implementation
```python
class Stock(Instrument):
    def __init__(self, symbol, exchange, currency='USD', sector=None, industry=None):
        super().__init__(symbol)
        self.exchange = exchange
        self.currency = currency
        self.sector = sector
        self.industry = industry
        self.corporate_actions = []
    
    def handle_split(self, split_date, split_ratio):
        """Handle stock split adjustment"""
        action = CorporateAction(
            action_type='split',
            date=split_date,
            ratio=split_ratio,
            description=f"{split_ratio}:1 stock split"
        )
        self.corporate_actions.append(action)
        
        # Adjust historical prices
        self._adjust_historical_data('split', split_date, split_ratio)
    
    def handle_dividend(self, ex_date, amount, currency=None):
        """Handle dividend payment"""
        action = CorporateAction(
            action_type='dividend',
            date=ex_date,
            amount=amount,
            currency=currency or self.currency,
            description=f"Dividend payment of {amount} {currency or self.currency}"
        )
        self.corporate_actions.append(action)
    
    def _adjust_historical_data(self, action_type, action_date, adjustment_factor):
        """Adjust historical prices for corporate actions"""
        if action_type == 'split':
            # Divide all prices before split date by split ratio
            price_columns = ['open', 'high', 'low', 'close']
            for column in price_columns:
                mask = self.data['timestamp'] < action_date
                self.data.loc[mask, column] /= adjustment_factor
            
            # Multiply volume by split ratio
            mask = self.data['timestamp'] < action_date
            self.data.loc[mask, 'volume'] *= adjustment_factor
    
    def get_adjusted_prices(self, start_date, end_date):
        """Get split and dividend adjusted prices"""
        # This would integrate with the data storage layer
        # to retrieve and apply all relevant adjustments
        raw_data = self.data_storage.load_price_data(self.symbol, start_date, end_date)
        
        # Apply all corporate actions in chronological order
        adjusted_data = raw_data.copy()
        for action in sorted(self.corporate_actions, key=lambda a: a.date):
            if action.action_type == 'split' and action.date >= start_date:
                adjusted_data = self._apply_split_adjustment(adjusted_data, action)
            elif action.action_type == 'dividend' and action.date >= start_date:
                adjusted_data = self._apply_dividend_adjustment(adjusted_data, action)
        
        return adjusted_data
```

## 3. Configuration Implementation

### 3.1 Session Configuration Details
```python
@dataclass
class SessionConfig:
    # Provider settings
    username: str = None
    password: str = None
    provider_host: str = None
    provider_port: str = "8888"
    provider_type: str = "barchart"  # barchart, yahoo, ibkr
    
    # Download settings
    download_directory: str = DEFAULT_DOWNLOAD_DIRECTORY
    start_year: int = DEFAULT_START_YEAR
    end_year: int = DEFAULT_END_YEAR
    daily_download_limit: int = DEFAULT_DAILY_DOWNLOAD_LIMIT
    chunk_size_days: int = 30  # Download in 30-day chunks
    
    # Operational settings
    dry_run: bool = DEFAULT_DRY_RUN
    backup_data: bool = False
    force_backup: bool = False
    random_sleep_in_sec: int = DEFAULT_RANDOM_SLEEP_IN_SEC
    log_level: str = DEFAULT_LOGGING_LEVEL
    max_concurrent_downloads: int = 3
    
    # Retry settings
    max_retries: int = 3
    base_retry_delay: int = 5  # seconds
    max_retry_delay: int = 300  # 5 minutes
    
    def validate(self):
        """Validate configuration completeness and correctness"""
        errors = []
        
        # Provider validation
        if self.provider_type == 'barchart':
            if not self.username or not self.password:
                errors.append("Barchart provider requires username and password")
        elif self.provider_type == 'ibkr':
            if not self.provider_host:
                errors.append("IBKR provider requires provider_host")
            try:
                port = int(self.provider_port)
                if not (1 <= port <= 65535):
                    errors.append("provider_port must be between 1 and 65535")
            except ValueError:
                errors.append("provider_port must be a valid integer")
        
        # Date validation
        if self.start_year > self.end_year:
            errors.append("start_year must be <= end_year")
        
        current_year = datetime.now().year
        if self.end_year > current_year + 1:
            errors.append(f"end_year cannot be more than one year in the future")
        
        # Directory validation
        try:
            download_path = Path(self.download_directory)
            download_path.mkdir(parents=True, exist_ok=True)
            
            # Test write permissions
            test_file = download_path / '.write_test'
            test_file.write_text('test')
            test_file.unlink()
        except Exception as e:
            errors.append(f"Cannot write to download_directory: {e}")
        
        # Operational validation
        if self.daily_download_limit <= 0:
            errors.append("daily_download_limit must be positive")
        
        if self.max_concurrent_downloads <= 0:
            errors.append("max_concurrent_downloads must be positive")
        
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    @classmethod
    def from_environment(cls):
        """Create configuration from environment variables"""
        return cls(
            username=os.getenv('BCU_USERNAME'),
            password=os.getenv('BCU_PASSWORD'),
            provider_host=os.getenv('BCU_PROVIDER_HOST'),
            provider_port=os.getenv('BCU_PROVIDER_PORT', '8888'),
            provider_type=os.getenv('BCU_PROVIDER_TYPE', 'barchart'),
            download_directory=os.getenv('BCU_DOWNLOAD_DIRECTORY', DEFAULT_DOWNLOAD_DIRECTORY),
            start_year=int(os.getenv('BCU_START_YEAR', str(DEFAULT_START_YEAR))),
            end_year=int(os.getenv('BCU_END_YEAR', str(DEFAULT_END_YEAR))),
            daily_download_limit=int(os.getenv('BCU_DAILY_LIMIT', str(DEFAULT_DAILY_DOWNLOAD_LIMIT))),
            dry_run=os.getenv('BCU_DRY_RUN', 'false').lower() == 'true',
            backup_data=os.getenv('BCU_BACKUP_DATA', 'false').lower() == 'true',
            log_level=os.getenv('BCU_LOG_LEVEL', DEFAULT_LOGGING_LEVEL),
        )
    
    @classmethod
    def from_file(cls, config_file_path):
        """Create configuration from JSON file"""
        with open(config_file_path, 'r') as f:
            config_data = json.load(f)
        
        return cls(**config_data)
    
    def to_dict(self):
        """Convert configuration to dictionary"""
        return asdict(self)
    
    def to_file(self, config_file_path):
        """Save configuration to JSON file"""
        with open(config_file_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
```

### 3.2 Component Factory Implementation
```python
class ComponentFactory:
    """Factory for creating and configuring BC-Utils components"""
    
    @staticmethod
    def create_downloader(config: SessionConfig) -> UpdatingDownloader:
        """Create fully configured downloader instance"""
        # Create storage components
        primary_storage = ComponentFactory._create_storage(
            storage_type='csv',
            base_directory=config.download_directory,
            dry_run=config.dry_run
        )
        
        backup_storage = None
        if config.backup_data:
            backup_storage = ComponentFactory._create_storage(
                storage_type='parquet',
                base_directory=config.download_directory,
                dry_run=config.dry_run
            )
        
        # Create data provider
        provider = ComponentFactory._create_provider(config)
        
        # Create validator
        validator = DataValidator(
            enable_business_rules=True,
            enable_statistical_validation=True,
            quality_threshold=0.95
        )
        
        # Create metadata store
        metadata_store = MetadataStore(
            metadata_directory=Path(config.download_directory) / '.metadata'
        )
        
        # Create downloader with all dependencies
        downloader = UpdatingDownloader(
            data_storage=primary_storage,
            data_provider=provider,
            backup_data_storage=backup_storage,
            validator=validator,
            metadata_store=metadata_store,
            force_backup=config.force_backup,
            random_sleep_in_sec=config.random_sleep_in_sec,
            dry_run=config.dry_run
        )
        
        return downloader
    
    @staticmethod
    def _create_storage(storage_type: str, base_directory: str, dry_run: bool):
        """Create storage instance based on type"""
        if storage_type == 'csv':
            return CsvStorage(
                base_directory=base_directory,
                dry_run=dry_run,
                encoding='utf-8',
                delimiter=',',
                float_precision=6
            )
        elif storage_type == 'parquet':
            return ParquetStorage(
                base_directory=base_directory,
                dry_run=dry_run,
                compression='snappy',
                engine='pyarrow'
            )
        else:
            raise ValueError(f"Unknown storage type: {storage_type}")
    
    @staticmethod
    def _create_provider(config: SessionConfig) -> DataProvider:
        """Create data provider based on configuration"""
        provider_type = config.provider_type
        
        if provider_type == "barchart":
            return BarchartDataProvider(
                username=config.username,
                password=config.password,
                daily_download_limit=config.daily_download_limit,
                base_url="https://www.barchart.com",
                timeout_seconds=60,
                max_retries=config.max_retries
            )
        elif provider_type == "yahoo":
            return YahooDataProvider(
                base_url="https://query1.finance.yahoo.com",
                timeout_seconds=30,
                max_retries=config.max_retries
            )
        elif provider_type == "ibkr":
            return IbkrDataProvider(
                host=config.provider_host,
                port=int(config.provider_port),
                client_id=1,
                timeout_seconds=config.base_retry_delay,
                max_retries=config.max_retries
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")
```

## Related Documents

- **[Component Architecture](../hld/02-component-architecture.md)** - High-level component design
- **[Provider Implementation](03-provider-implementation.md)** - Data provider details
- **[Storage Implementation](04-storage-implementation.md)** - Storage layer details
- **[Testing Implementation](06-testing-implementation.md)** - Testing strategies

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** Senior Developer, Lead Engineer