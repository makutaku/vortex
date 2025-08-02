# Data Processing Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Data Flow Design](../hld/03-data-flow-design.md)

## 1. Data Fetching Implementation

### 1.1 Provider Data Fetching
```python
def fetch_instrument_data(job: DownloadJob) -> RawDataResponse:
    """Fetch data from provider with comprehensive error handling"""
    provider = job.provider
    
    try:
        # 1. Check rate limits
        if not provider.rate_limiter.can_make_request():
            wait_time = provider.rate_limiter.get_wait_time()
            logger.info(f"Rate limited, waiting {wait_time} seconds")
            time.sleep(wait_time)
        
        # 2. Build request parameters
        request_params = provider.build_request_params(
            instrument=job.instrument,
            start_date=job.date_range.start,
            end_date=job.date_range.end
        )
        
        # 3. Execute request with retry logic
        response = provider.execute_request(request_params)
        
        # 4. Validate response format
        if not provider.validate_response(response):
            raise DataProviderError("Invalid response format")
        
        # 5. Record rate limit usage
        provider.rate_limiter.record_request()
        
        return RawDataResponse(
            data=response.content,
            headers=dict(response.headers),
            metadata=provider.extract_metadata(response),
            timestamp=datetime.utcnow(),
            provider=provider.name,
            request_params=request_params
        )
        
    except RateLimitError as e:
        # Wait and retry
        wait_time = e.retry_after or provider.get_rate_limit_wait_time()
        logger.warning(f"Rate limited, waiting {wait_time} seconds")
        time.sleep(wait_time)
        return fetch_instrument_data(job)  # Recursive retry
        
    except AuthenticationError as e:
        # Re-authenticate and retry
        logger.warning(f"Authentication failed: {e}, attempting re-authentication")
        if provider.authenticate():
            logger.info("Re-authentication successful, retrying request")
            return fetch_instrument_data(job)
        else:
            raise DataAcquisitionError("Re-authentication failed")
        
    except ConnectionError as e:
        # Exponential backoff retry
        retry_count = getattr(job, 'fetch_retry_count', 0) + 1
        if retry_count <= MAX_FETCH_RETRIES:
            delay = min(300, 2 ** retry_count)  # Max 5 minutes
            logger.warning(f"Connection error, retry {retry_count} in {delay}s: {e}")
            job.fetch_retry_count = retry_count
            time.sleep(delay)
            return fetch_instrument_data(job)
        else:
            raise DataAcquisitionError(f"Max retries exceeded: {e}")
            
    except Exception as e:
        # Log unknown error and fail
        logger.error(f"Fetch failed for {job.instrument}: {e}")
        raise DataAcquisitionError(f"Failed to fetch data: {e}")
```

### 1.2 Rate Limiting Implementation
```python
class RateLimiter:
    """Advanced rate limiting with multiple time windows"""
    
    def __init__(self, requests_per_day=None, requests_per_hour=None, 
                 requests_per_minute=None, burst_limit=None):
        self.requests_per_day = requests_per_day
        self.requests_per_hour = requests_per_hour
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        
        # Track requests in different time windows
        self.daily_requests = deque()
        self.hourly_requests = deque()
        self.minute_requests = deque()
        self.burst_requests = deque()
        
        self.lock = threading.Lock()
    
    def can_make_request(self) -> bool:
        """Check if request can be made within all rate limits"""
        with self.lock:
            now = time.time()
            
            # Clean old requests
            self._clean_old_requests(now)
            
            # Check daily limit
            if (self.requests_per_day and 
                len(self.daily_requests) >= self.requests_per_day):
                return False
            
            # Check hourly limit
            if (self.requests_per_hour and 
                len(self.hourly_requests) >= self.requests_per_hour):
                return False
            
            # Check minute limit
            if (self.requests_per_minute and 
                len(self.minute_requests) >= self.requests_per_minute):
                return False
            
            # Check burst limit (last 10 seconds)
            if (self.burst_limit and 
                len(self.burst_requests) >= self.burst_limit):
                return False
            
            return True
    
    def record_request(self):
        """Record a request for rate limiting"""
        with self.lock:
            now = time.time()
            
            if self.requests_per_day:
                self.daily_requests.append(now)
            if self.requests_per_hour:
                self.hourly_requests.append(now)
            if self.requests_per_minute:
                self.minute_requests.append(now)
            if self.burst_limit:
                self.burst_requests.append(now)
    
    def get_wait_time(self) -> float:
        """Get time to wait before next request is allowed"""
        with self.lock:
            now = time.time()
            
            # Check minute limit first (shortest wait)
            if (self.requests_per_minute and 
                len(self.minute_requests) >= self.requests_per_minute):
                oldest_request = self.minute_requests[0]
                return max(0, 60 - (now - oldest_request))
            
            # Check burst limit
            if (self.burst_limit and 
                len(self.burst_requests) >= self.burst_limit):
                oldest_request = self.burst_requests[0]
                return max(0, 10 - (now - oldest_request))
            
            # Check hourly limit
            if (self.requests_per_hour and 
                len(self.hourly_requests) >= self.requests_per_hour):
                oldest_request = self.hourly_requests[0]
                return max(0, 3600 - (now - oldest_request))
            
            return 0
    
    def _clean_old_requests(self, now: float):
        """Remove requests outside of tracking windows"""
        # Clean daily requests (24 hours)
        while self.daily_requests and (now - self.daily_requests[0]) > 86400:
            self.daily_requests.popleft()
        
        # Clean hourly requests (1 hour)
        while self.hourly_requests and (now - self.hourly_requests[0]) > 3600:
            self.hourly_requests.popleft()
        
        # Clean minute requests (1 minute)
        while self.minute_requests and (now - self.minute_requests[0]) > 60:
            self.minute_requests.popleft()
        
        # Clean burst requests (10 seconds)
        while self.burst_requests and (now - self.burst_requests[0]) > 10:
            self.burst_requests.popleft()
```

## 2. Data Validation Implementation

### 2.1 Comprehensive Data Validator
```python
class DataValidator:
    """Comprehensive data validation pipeline"""
    
    def __init__(self, enable_business_rules=True, enable_statistical_validation=True,
                 quality_threshold=0.95):
        self.enable_business_rules = enable_business_rules
        self.enable_statistical_validation = enable_statistical_validation
        self.quality_threshold = quality_threshold
        self.logger = logging.getLogger(__name__)
        
    def validate_data(self, data: pd.DataFrame, instrument: Instrument) -> ValidationResult:
        """Apply all validation rules to dataset"""
        errors = []
        warnings = []
        
        # 1. Schema validation
        schema_result = self._validate_schema(data)
        errors.extend(schema_result.errors)
        warnings.extend(schema_result.warnings)
        
        # 2. Business logic validation
        if self.enable_business_rules:
            business_result = self._validate_business_rules(data, instrument)
            errors.extend(business_result.errors)
            warnings.extend(business_result.warnings)
        
        # 3. Statistical validation
        if self.enable_statistical_validation:
            stats_result = self._validate_statistical_properties(data)
            warnings.extend(stats_result.warnings)
        
        # 4. Temporal validation
        temporal_result = self._validate_temporal_consistency(data)
        errors.extend(temporal_result.errors)
        warnings.extend(temporal_result.warnings)
        
        # 5. Calculate quality score
        quality_score = self._calculate_quality_score(data, errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0 and quality_score >= self.quality_threshold,
            errors=errors,
            warnings=warnings,
            quality_score=quality_score,
            validation_timestamp=datetime.utcnow()
        )
    
    def _validate_schema(self, data: pd.DataFrame) -> ValidationResult:
        """Validate data schema and structure"""
        errors = []
        warnings = []
        
        # Required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            errors.append(f"Missing required columns: {missing_columns}")
        
        # Data types
        if 'timestamp' in data.columns:
            if not pd.api.types.is_datetime64_any_dtype(data['timestamp']):
                try:
                    pd.to_datetime(data['timestamp'])
                    warnings.append("Timestamp column not datetime type but convertible")
                except:
                    errors.append("Timestamp column cannot be converted to datetime")
        
        # Numeric columns
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in data.columns:
                if not pd.api.types.is_numeric_dtype(data[col]):
                    errors.append(f"Column {col} is not numeric")
                elif data[col].isna().any():
                    warnings.append(f"Column {col} contains NaN values")
        
        return ValidationResult(errors=errors, warnings=warnings)
    
    def _validate_business_rules(self, data: pd.DataFrame, instrument: Instrument) -> ValidationResult:
        """Validate financial data business rules"""
        errors = []
        warnings = []
        
        if not all(col in data.columns for col in ['open', 'high', 'low', 'close', 'volume']):
            return ValidationResult(errors=errors, warnings=warnings)
        
        # Price relationship validation (OHLC rules)
        invalid_high = data[data['high'] < data[['open', 'close']].max(axis=1)]
        if len(invalid_high) > 0:
            errors.append(f"High price less than max(open, close) in {len(invalid_high)} rows")
        
        invalid_low = data[data['low'] > data[['open', 'close']].min(axis=1)]
        if len(invalid_low) > 0:
            errors.append(f"Low price greater than min(open, close) in {len(invalid_low)} rows")
        
        # Volume validation
        negative_volume = data[data['volume'] < 0]
        if len(negative_volume) > 0:
            errors.append(f"Negative volume in {len(negative_volume)} rows")
        
        zero_volume = data[data['volume'] == 0]
        if len(zero_volume) > len(data) * 0.1:  # More than 10% zero volume
            warnings.append(f"High percentage of zero volume: {len(zero_volume)}/{len(data)} rows")
        
        # Price movement validation
        if len(data) > 1:
            price_changes = data['close'].pct_change().abs()
            max_daily_move = getattr(instrument, 'max_daily_move', 0.20)  # 20% default
            extreme_moves = price_changes > max_daily_move
            
            if extreme_moves.any():
                extreme_count = extreme_moves.sum()
                warnings.append(f"Extreme price movements detected: {extreme_count} instances > {max_daily_move*100}%")
        
        # Price continuity (gaps)
        if len(data) > 1:
            data_sorted = data.sort_values('timestamp')
            price_gaps = abs(data_sorted['open'].iloc[1:].values - data_sorted['close'].iloc[:-1].values)
            relative_gaps = price_gaps / data_sorted['close'].iloc[:-1].values
            large_gaps = relative_gaps > 0.05  # 5% gap
            
            if large_gaps.any():
                gap_count = large_gaps.sum()
                warnings.append(f"Large price gaps detected: {gap_count} gaps > 5%")
        
        return ValidationResult(errors=errors, warnings=warnings)
    
    def _validate_statistical_properties(self, data: pd.DataFrame) -> ValidationResult:
        """Validate statistical properties of the data"""
        warnings = []
        
        if len(data) < 10:  # Need minimum data for statistical analysis
            return ValidationResult(warnings=warnings)
        
        # Price volatility analysis
        if 'close' in data.columns and len(data) > 1:
            returns = data['close'].pct_change().dropna()
            volatility = returns.std()
            
            # Check for extremely high volatility
            if volatility > 0.1:  # 10% daily volatility
                warnings.append(f"High volatility detected: {volatility:.3f} daily standard deviation")
            
            # Check for extremely low volatility (possible stale data)
            if volatility < 0.001:  # 0.1% daily volatility
                warnings.append(f"Unusually low volatility: {volatility:.3f} daily standard deviation")
        
        # Volume analysis
        if 'volume' in data.columns:
            volume_std = data['volume'].std()
            volume_mean = data['volume'].mean()
            
            if volume_mean > 0:
                volume_cv = volume_std / volume_mean  # Coefficient of variation
                
                if volume_cv > 5:  # Very high volume variability
                    warnings.append(f"High volume variability: CV = {volume_cv:.2f}")
        
        # Outlier detection using IQR method
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in data.columns:
                Q1 = data[col].quantile(0.25)
                Q3 = data[col].quantile(0.75)
                IQR = Q3 - Q1
                
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                outliers = data[(data[col] < lower_bound) | (data[col] > upper_bound)]
                if len(outliers) > 0:
                    outlier_percentage = len(outliers) / len(data) * 100
                    if outlier_percentage > 5:  # More than 5% outliers
                        warnings.append(f"High percentage of outliers in {col}: {outlier_percentage:.1f}%")
        
        return ValidationResult(warnings=warnings)
    
    def _validate_temporal_consistency(self, data: pd.DataFrame) -> ValidationResult:
        """Validate temporal aspects of the data"""
        errors = []
        warnings = []
        
        if 'timestamp' not in data.columns or len(data) < 2:
            return ValidationResult(errors=errors, warnings=warnings)
        
        # Sort by timestamp for analysis
        data_sorted = data.sort_values('timestamp')
        
        # Check for duplicate timestamps
        duplicate_timestamps = data_sorted['timestamp'].duplicated()
        if duplicate_timestamps.any():
            dup_count = duplicate_timestamps.sum()
            errors.append(f"Duplicate timestamps found: {dup_count} duplicates")
        
        # Check timestamp ordering (should be monotonic)
        timestamps = pd.to_datetime(data_sorted['timestamp'])
        if not timestamps.is_monotonic_increasing:
            warnings.append("Timestamps are not in chronological order")
        
        # Check for reasonable time gaps
        if len(timestamps) > 1:
            time_diffs = timestamps.diff().dropna()
            
            # Very small gaps (sub-second for daily data)
            very_small_gaps = time_diffs < pd.Timedelta(seconds=1)
            if very_small_gaps.any():
                warnings.append(f"Very small time gaps detected: {very_small_gaps.sum()} sub-second gaps")
            
            # Very large gaps (more than 7 days for daily data)
            very_large_gaps = time_diffs > pd.Timedelta(days=7)
            if very_large_gaps.any():
                warnings.append(f"Large time gaps detected: {very_large_gaps.sum()} gaps > 7 days")
        
        return ValidationResult(errors=errors, warnings=warnings)
    
    def _calculate_quality_score(self, data: pd.DataFrame, errors: List[str], 
                                warnings: List[str]) -> float:
        """Calculate overall data quality score (0.0 to 1.0)"""
        if len(data) == 0:
            return 0.0
        
        score = 1.0
        
        # Penalize errors heavily
        score -= len(errors) * 0.2
        
        # Penalize warnings lightly
        score -= len(warnings) * 0.05
        
        # Data completeness bonus
        numeric_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_columns:
            if col in data.columns:
                completeness = 1 - (data[col].isna().sum() / len(data))
                score *= completeness
        
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
```

## 3. Data Transformation Implementation

### 3.1 Detailed Transformation Engine
```python
class DataTransformer:
    """Transform provider-specific data to standard format"""
    
    STANDARD_COLUMNS = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'symbol', 'provider']
    
    def __init__(self):
        self.column_mappings = {
            'barchart': {
                'Time': 'timestamp',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Last': 'close',
                'Volume': 'volume'
            },
            'yahoo': {
                # Yahoo uses lowercase names
                'timestamp': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            },
            'ibkr': {
                'date': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            }
        }
    
    def transform_to_standard(self, data: pd.DataFrame, provider: str, 
                            instrument: Instrument) -> pd.DataFrame:
        """Transform data to standard OHLCV format"""
        
        # 1. Apply provider-specific column mapping
        mapped_data = self._apply_column_mapping(data, provider)
        
        # 2. Standardize timestamps
        mapped_data['timestamp'] = self._standardize_timestamps(
            mapped_data['timestamp'], provider
        )
        
        # 3. Convert data types
        mapped_data = self._convert_data_types(mapped_data)
        
        # 4. Apply unit conversions if needed
        mapped_data = self._apply_unit_conversions(mapped_data, provider, instrument)
        
        # 5. Add metadata columns
        mapped_data['symbol'] = instrument.symbol
        mapped_data['provider'] = provider
        
        # 6. Sort by timestamp
        mapped_data = mapped_data.sort_values('timestamp').reset_index(drop=True)
        
        # 7. Select only standard columns (drop any extra columns)
        available_columns = [col for col in self.STANDARD_COLUMNS if col in mapped_data.columns]
        return mapped_data[available_columns]
    
    def _apply_column_mapping(self, data: pd.DataFrame, provider: str) -> pd.DataFrame:
        """Apply provider-specific column name mapping"""
        if provider not in self.column_mappings:
            raise ValueError(f"No column mapping available for provider: {provider}")
        
        mapping = self.column_mappings[provider]
        
        # Rename columns that exist in the mapping
        renamed_data = data.rename(columns=mapping)
        
        # Check if all required columns are present after mapping
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = set(required_columns) - set(renamed_data.columns)
        
        if missing_columns:
            raise DataTransformationError(
                f"Missing columns after mapping for {provider}: {missing_columns}"
            )
        
        return renamed_data
    
    def _standardize_timestamps(self, timestamps: pd.Series, provider: str) -> pd.Series:
        """Convert timestamps to UTC ISO format"""
        try:
            if provider == 'barchart':
                # Barchart typically uses EST/EDT, convert to UTC
                # Handle different timestamp formats
                if timestamps.dtype == 'object':
                    # String timestamps
                    parsed_timestamps = pd.to_datetime(timestamps)
                else:
                    parsed_timestamps = pd.to_datetime(timestamps)
                
                # Localize to US/Eastern and convert to UTC
                if parsed_timestamps.dt.tz is None:
                    localized = parsed_timestamps.dt.tz_localize('US/Eastern', ambiguous='infer')
                else:
                    localized = parsed_timestamps.dt.tz_convert('US/Eastern')
                
                return localized.dt.tz_convert('UTC')
                
            elif provider == 'yahoo':
                # Yahoo Finance typically provides UTC timestamps
                parsed_timestamps = pd.to_datetime(timestamps, unit='s', utc=True)
                return parsed_timestamps
                
            elif provider == 'ibkr':
                # IBKR may use various formats
                if pd.api.types.is_numeric_dtype(timestamps):
                    # Unix timestamps
                    return pd.to_datetime(timestamps, unit='s', utc=True)
                else:
                    # String timestamps
                    parsed_timestamps = pd.to_datetime(timestamps)
                    if parsed_timestamps.dt.tz is None:
                        return parsed_timestamps.dt.tz_localize('UTC')
                    else:
                        return parsed_timestamps.dt.tz_convert('UTC')
            else:
                # Generic handling
                parsed_timestamps = pd.to_datetime(timestamps)
                if parsed_timestamps.dt.tz is None:
                    return parsed_timestamps.dt.tz_localize('UTC')
                else:
                    return parsed_timestamps.dt.tz_convert('UTC')
                    
        except Exception as e:
            raise DataTransformationError(f"Failed to standardize timestamps for {provider}: {e}")
    
    def _convert_data_types(self, data: pd.DataFrame) -> pd.DataFrame:
        """Convert columns to appropriate data types"""
        converted_data = data.copy()
        
        # Price columns should be float64
        price_columns = ['open', 'high', 'low', 'close']
        for col in price_columns:
            if col in converted_data.columns:
                converted_data[col] = pd.to_numeric(converted_data[col], errors='coerce').astype('float64')
        
        # Volume should be int64 (handle NaN by filling with 0)
        if 'volume' in converted_data.columns:
            volume_numeric = pd.to_numeric(converted_data['volume'], errors='coerce')
            converted_data['volume'] = volume_numeric.fillna(0).astype('int64')
        
        # String columns
        string_columns = ['symbol', 'provider']
        for col in string_columns:
            if col in converted_data.columns:
                converted_data[col] = converted_data[col].astype('string')
        
        return converted_data
    
    def _apply_unit_conversions(self, data: pd.DataFrame, provider: str, 
                              instrument: Instrument) -> pd.DataFrame:
        """Apply unit conversions if needed"""
        converted_data = data.copy()
        
        # Example: Some providers might provide prices in different units
        if provider == 'some_provider_with_different_units':
            # Convert cents to dollars
            price_columns = ['open', 'high', 'low', 'close']
            for col in price_columns:
                if col in converted_data.columns:
                    converted_data[col] = converted_data[col] / 100
        
        # Currency conversions could be added here
        # Volume adjustments for stock splits could be added here
        
        return converted_data
```

## 4. Storage Operation Implementation

### 4.1 Deduplication Engine
```python
class DeduplicationEngine:
    """Intelligent data deduplication system"""
    
    def __init__(self, strategy: str = 'timestamp_symbol', 
                 conflict_resolution: str = 'provider_preference'):
        self.strategy = strategy
        self.conflict_resolution = conflict_resolution
        self.provider_preference = ['ibkr', 'barchart', 'yahoo']  # Preference order
        self.duplicate_threshold = 0.1  # 10% duplicate threshold for warnings
        
    def deduplicate(self, existing_data: pd.DataFrame, 
                   new_data: pd.DataFrame) -> DeduplicationResult:
        """Perform intelligent deduplication of datasets"""
        
        if len(existing_data) == 0:
            return DeduplicationResult(
                original_count=len(new_data),
                final_count=len(new_data),
                duplicates_removed=0,
                conflicts_resolved=0,
                data=new_data.copy()
            )
        
        # 1. Combine datasets
        combined_data = pd.concat([existing_data, new_data], ignore_index=True)
        original_count = len(combined_data)
        
        # 2. Identify duplicate criteria based on strategy
        duplicate_subset = self._get_duplicate_subset()
        
        # 3. Find duplicates
        duplicates_mask = combined_data.duplicated(subset=duplicate_subset, keep=False)
        duplicate_rows = combined_data[duplicates_mask]
        unique_rows = combined_data[~duplicates_mask]
        
        # 4. Resolve conflicts in duplicate groups
        resolved_data, conflicts_resolved = self._resolve_duplicates(duplicate_rows, duplicate_subset)
        
        # 5. Combine unique rows with resolved duplicates
        final_data = pd.concat([unique_rows, resolved_data], ignore_index=True)
        
        # 6. Sort by timestamp
        final_data = final_data.sort_values('timestamp').reset_index(drop=True)
        
        # 7. Generate deduplication report
        duplicates_removed = original_count - len(final_data)
        
        result = DeduplicationResult(
            original_count=original_count,
            final_count=len(final_data),
            duplicates_removed=duplicates_removed,
            conflicts_resolved=conflicts_resolved,
            data=final_data,
            duplicate_percentage=(duplicates_removed / original_count) * 100 if original_count > 0 else 0
        )
        
        # Log warning if high percentage of duplicates
        if result.duplicate_percentage > self.duplicate_threshold * 100:
            logger.warning(f"High duplicate percentage: {result.duplicate_percentage:.1f}%")
        
        return result
    
    def _get_duplicate_subset(self) -> List[str]:
        """Get columns to use for duplicate detection"""
        if self.strategy == 'timestamp_symbol':
            return ['timestamp', 'symbol']
        elif self.strategy == 'timestamp_only':
            return ['timestamp']
        elif self.strategy == 'all_columns':
            return None  # Use all columns
        else:
            raise ValueError(f"Unknown deduplication strategy: {self.strategy}")
    
    def _resolve_duplicates(self, duplicate_rows: pd.DataFrame, 
                          subset: List[str]) -> Tuple[pd.DataFrame, int]:
        """Resolve conflicts in duplicate rows"""
        if len(duplicate_rows) == 0:
            return duplicate_rows, 0
        
        resolved_groups = []
        conflicts_resolved = 0
        
        # Group by duplicate criteria and resolve each group
        for name, group in duplicate_rows.groupby(subset):
            if len(group) > 1:
                conflicts_resolved += len(group) - 1
            resolved_row = self._resolve_duplicate_group(group)
            resolved_groups.append(resolved_row)
        
        if resolved_groups:
            return pd.concat(resolved_groups, ignore_index=True), conflicts_resolved
        else:
            return pd.DataFrame(), conflicts_resolved
    
    def _resolve_duplicate_group(self, group: pd.DataFrame) -> pd.DataFrame:
        """Resolve conflicts within a group of duplicate rows"""
        
        if len(group) == 1:
            return group
        
        if self.conflict_resolution == 'provider_preference':
            # Use provider preference order
            if 'provider' in group.columns:
                group['provider_rank'] = group['provider'].map(
                    {p: i for i, p in enumerate(self.provider_preference)}
                ).fillna(999)  # Unknown providers get low priority
                
                best_row = group.loc[group['provider_rank'].idxmin()]
                return pd.DataFrame([best_row]).drop(columns=['provider_rank'])
            
        elif self.conflict_resolution == 'latest_timestamp':
            # Keep the row with the latest processing timestamp
            if 'processing_timestamp' in group.columns:
                best_row = group.loc[group['processing_timestamp'].idxmax()]
                return pd.DataFrame([best_row])
        
        elif self.conflict_resolution == 'highest_volume':
            # Keep the row with highest volume (assuming higher volume is more reliable)
            if 'volume' in group.columns:
                best_row = group.loc[group['volume'].idxmax()]
                return pd.DataFrame([best_row])
        
        # Default: keep the last row
        best_row = group.iloc[-1]
        return pd.DataFrame([best_row])
```

### 4.2 Atomic Storage Operations
```python
def save_with_deduplication(data: pd.DataFrame, filepath: str, 
                          storage: DataStorage) -> SaveResult:
    """Save data with automatic deduplication and atomic operations"""
    
    start_time = time.time()
    
    try:
        # 1. Validate input data
        if len(data) == 0:
            return SaveResult(success=False, reason="No data to save")
        
        # 2. Check if file already exists
        if storage.file_exists(filepath):
            # Load existing data
            existing_data = storage.load(filepath)
            
            # Perform deduplication
            dedup_engine = DeduplicationEngine()
            dedup_result = dedup_engine.deduplicate(existing_data, data)
            final_data = dedup_result.data
            
            logger.info(f"Deduplication: {dedup_result.original_count} -> {dedup_result.final_count} "
                       f"({dedup_result.duplicates_removed} duplicates removed)")
        else:
            final_data = data.copy()
        
        # 3. Sort by timestamp
        final_data = final_data.sort_values('timestamp').reset_index(drop=True)
        
        # 4. Validate final data before saving
        if len(final_data) < MIN_DATA_THRESHOLD:
            return SaveResult(success=False, reason="Insufficient data after deduplication")
        
        # 5. Atomic save operation
        temp_filepath = f"{filepath}.tmp.{int(time.time())}"
        
        try:
            # Save to temporary file
            storage.save_raw(final_data, temp_filepath)
            
            # Verify the temporary file
            verification_data = storage.load(temp_filepath)
            if len(verification_data) != len(final_data):
                raise StorageError("Data verification failed after save")
            
            # Atomic rename
            storage.move_file(temp_filepath, filepath)
            
        except Exception as e:
            # Clean up temporary file on failure
            if storage.file_exists(temp_filepath):
                storage.delete_file(temp_filepath)
            raise e
        
        # 6. Update metadata
        metadata = DatasetMetadata(
            filepath=filepath,
            row_count=len(final_data),
            column_count=len(final_data.columns),
            file_size=storage.get_file_size(filepath),
            last_modified=datetime.utcnow(),
            checksum=storage.calculate_checksum(filepath),
            date_range=(final_data['timestamp'].min(), final_data['timestamp'].max()) if 'timestamp' in final_data.columns else None,
            processing_duration=time.time() - start_time
        )
        storage.update_metadata(filepath, metadata)
        
        return SaveResult(
            success=True, 
            filepath=filepath, 
            row_count=len(final_data),
            processing_time=time.time() - start_time
        )
        
    except Exception as e:
        logger.error(f"Save operation failed for {filepath}: {e}")
        return SaveResult(
            success=False, 
            filepath=filepath, 
            error=str(e),
            processing_time=time.time() - start_time
        )
```

## 5. Performance Optimization Implementation

### 5.1 Caching System
```python
class DataCache:
    """Intelligent caching for frequently accessed data"""
    
    def __init__(self, max_size_mb: int = 512, default_ttl: int = 3600):
        self.max_size_mb = max_size_mb
        self.default_ttl = default_ttl
        self.cache = {}
        self.access_times = {}
        self.memory_usage_mb = 0
        self.lock = threading.Lock()
        self.hit_count = 0
        self.miss_count = 0
        
    def get_cached_data(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Retrieve cached data if available and fresh"""
        with self.lock:
            if cache_key in self.cache:
                cached_item = self.cache[cache_key]
                
                # Check if data is still fresh
                if self._is_fresh(cached_item):
                    # Update access time
                    self.access_times[cache_key] = time.time()
                    self.hit_count += 1
                    return cached_item.data.copy()
                else:
                    # Remove stale data
                    self._remove_from_cache(cache_key)
            
            self.miss_count += 1
            return None
    
    def cache_data(self, cache_key: str, data: pd.DataFrame, ttl_seconds: int = None):
        """Cache data with TTL and size management"""
        if ttl_seconds is None:
            ttl_seconds = self.default_ttl
        
        with self.lock:
            # Calculate memory usage of new data
            data_memory_mb = self._estimate_dataframe_memory(data)
            
            # Evict if necessary to make room
            while (self.memory_usage_mb + data_memory_mb > self.max_size_mb 
                   and self.cache):
                self._evict_least_recently_used()
            
            # Cache the data
            cached_item = CachedItem(
                data=data.copy(),
                timestamp=time.time(),
                ttl=ttl_seconds,
                memory_mb=data_memory_mb
            )
            
            self.cache[cache_key] = cached_item
            self.access_times[cache_key] = time.time()
            self.memory_usage_mb += data_memory_mb
    
    def _is_fresh(self, cached_item) -> bool:
        """Check if cached item is still fresh"""
        age = time.time() - cached_item.timestamp
        return age < cached_item.ttl
    
    def _evict_least_recently_used(self):
        """Remove least recently used item from cache"""
        if not self.access_times:
            return
        
        lru_key = min(self.access_times.keys(), 
                     key=lambda k: self.access_times[k])
        self._remove_from_cache(lru_key)
    
    def _remove_from_cache(self, cache_key: str):
        """Remove item from cache and update memory usage"""
        if cache_key in self.cache:
            cached_item = self.cache.pop(cache_key)
            self.access_times.pop(cache_key, None)
            self.memory_usage_mb -= cached_item.memory_mb
    
    def _estimate_dataframe_memory(self, df: pd.DataFrame) -> float:
        """Estimate DataFrame memory usage in MB"""
        return df.memory_usage(deep=True).sum() / 1024 / 1024
    
    def get_cache_stats(self) -> dict:
        """Get cache performance statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests) if total_requests > 0 else 0
        
        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': hit_rate,
            'memory_usage_mb': self.memory_usage_mb,
            'max_size_mb': self.max_size_mb,
            'cache_size': len(self.cache),
            'memory_utilization': self.memory_usage_mb / self.max_size_mb
        }
```

## Related Documents

- **[Data Flow Design](../hld/03-data-flow-design.md)** - High-level data processing architecture
- **[Component Implementation](01-component-implementation.md)** - Component implementation details
- **[Provider Implementation](03-provider-implementation.md)** - Provider-specific details
- **[Storage Implementation](04-storage-implementation.md)** - Storage layer implementation

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** Senior Developer, Data Engineer