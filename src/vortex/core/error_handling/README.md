# Standardized Error Handling Guide

## Overview

This module provides consistent error handling patterns to replace the inconsistent approaches currently used throughout the Vortex codebase.

## Error Handling Strategies

### 1. FAIL_FAST (Critical Operations)
Use for operations where failure should stop execution immediately:
- Database connection failures
- Critical configuration errors
- Authentication failures

**Before:**
```python
if not credentials:
    raise Exception("No credentials found")
```

**After:**
```python
@fail_fast("authenticate", "BarchartAuth")
def login(self):
    if not self.credentials:
        raise AuthenticationError("No credentials found")
```

### 2. RETURN_NONE (Optional Operations)
Use for operations that are optional or can gracefully fail:
- Optional data enrichment
- Cache lookups
- Non-critical API calls

**Before:**
```python
try:
    data = fetch_optional_data()
    return data
except Exception as e:
    logger.error(f"Error: {e}")
    return None
```

**After:**
```python
@return_none_on_error("fetch_optional_data", "DataService")
def fetch_optional_data(self):
    # Implementation that may fail
    return api_call()
```

### 3. RETURN_DEFAULT (Operations with Fallbacks)
Use for operations that have sensible default values:
- Configuration parsing with defaults
- Feature toggles
- Optional settings

**Before:**
```python
try:
    limit = int(config.get("daily_limit"))
except (ValueError, KeyError):
    limit = 100  # default
    return limit
```

**After:**
```python
@return_default_on_error("get_daily_limit", "ConfigService", default_value=100)
def get_daily_limit(self):
    return int(self.config.get("daily_limit"))
```

### 4. LOG_AND_CONTINUE (Best-effort Operations)
Use for operations that should continue despite errors:
- Metrics collection
- Non-critical logging
- Background cleanup tasks

**Before:**
```python
try:
    collect_metrics()
except Exception as e:
    logger.warning(f"Metrics collection failed: {e}")
    # continue execution
```

**After:**
```python
@log_and_continue("collect_metrics", "MetricsService")  
def collect_metrics(self):
    # Implementation that may fail but shouldn't stop execution
    send_metrics_to_server()
```

### 5. COLLECT_ERRORS (Batch Operations)
Use for operations that process multiple items and need to report all failures:
- Batch downloads
- Multi-file validation
- Bulk operations

**Before:**
```python
errors = []
for item in items:
    try:
        process(item)
    except Exception as e:
        errors.append(f"Failed to process {item}: {e}")
return errors
```

**After:**
```python
@with_error_handling(ErrorHandlingStrategy.COLLECT_ERRORS, "process_batch", "BatchProcessor")
def process_batch(self, items):
    results = []
    for item in items:
        result = self.process_item(item)  # This will collect errors
        results.append(result)
    return results
```

## Migration Guide

### Step 1: Identify Current Patterns
Look for these patterns in your code:
- `return None` after error logging
- `raise SomeException()` 
- `logger.error()` followed by continued execution
- Mixed error handling within the same component

### Step 2: Choose Appropriate Strategy
- **Critical path operations**: FAIL_FAST
- **Optional operations**: RETURN_NONE  
- **Operations with defaults**: RETURN_DEFAULT
- **Background/metrics operations**: LOG_AND_CONTINUE
- **Batch operations**: COLLECT_ERRORS

### Step 3: Apply Decorators
Replace existing try/catch blocks with appropriate decorators.

### Step 4: Update Tests
Ensure tests account for the new error handling behavior.

## Examples by Component

### Data Providers
```python
@fail_fast("authenticate", "BarchartProvider")
def login(self):
    # Authentication must succeed
    
@return_none_on_error("fetch_usage_info", "BarchartProvider")  
def get_usage_info(self):
    # Usage info is optional
    
@return_default_on_error("get_daily_limit", "BarchartProvider", default_value=100)
def get_daily_limit(self):
    # Has sensible default
```

### CLI Commands
```python
@fail_fast("validate_config", "DownloadCommand")
def validate_configuration(self):
    # Config validation is critical
    
@return_none_on_error("get_default_assets", "DownloadCommand")
def get_default_assets_file(self):
    # Default assets are optional
```

### Background Services
```python
@log_and_continue("update_cache", "CacheService")
def update_background_cache(self):
    # Cache updates shouldn't fail the main operation
```

## Benefits

1. **Consistency**: Same error handling pattern across all components
2. **Maintainability**: Clear intent and standardized logging
3. **Debugging**: Consistent error messages with context
4. **Testing**: Predictable error behavior
5. **Documentation**: Self-documenting error handling strategy