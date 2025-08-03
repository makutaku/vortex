# Logging and Observability System

## Overview

Comprehensive logging and observability system for Vortex with structured logging, performance metrics, health checks, and configurable outputs.

## Features

### Structured Logging
- **JSON output** for machine-readable logs
- **Correlation IDs** for request tracing
- **Contextual information** with automatic metadata
- **Rich console output** with colors and formatting
- **Multiple output targets** (console, file, both)

### Performance Monitoring
- **Operation timing** with automatic duration tracking
- **Performance metrics** logging
- **Counter tracking** for events
- **Function decorators** for automatic instrumentation

### Health Checks
- **Built-in health checks** for system components
- **Custom health check registration**
- **JSON health status endpoints**
- **Automatic error reporting**

### Configuration Integration
- **Integrated with VortexConfig** system
- **Environment variable support**
- **Dynamic reconfiguration** capability
- **Backward compatibility** with existing code

## Configuration

### TOML Configuration
```toml
[general.logging]
level = "INFO"                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
format = "console"                # console, json, rich
output = ["console"]              # console, file, or both
file_path = "logs/vortex.log"     # Optional log file path
max_file_size = 10485760          # 10MB max file size
backup_count = 5                  # Number of backup files
```

### Environment Variables
```bash
# Modern variables
export VORTEX_LOGGING_LEVEL="DEBUG"
export VORTEX_LOGGING_FORMAT="json"
export VORTEX_LOGGING_OUTPUT="console,file"
export VORTEX_LOGGING_FILE_PATH="logs/app.log"

# Legacy compatibility
export VORTEX_LOG_LEVEL="INFO"  # Still supported
```

## Usage

### Basic Logging
```python
from vortex.logging_integration import get_module_logger

logger = get_module_logger()
logger.info("Processing started", user_id="123", operation="download")
logger.error("Download failed", symbol="AAPL", error_code="NETWORK_ERROR")
```

### Performance Logging
```python
from vortex.logging_integration import get_module_performance_logger

perf_logger = get_module_performance_logger()

# Time operations
with perf_logger.time_operation("database_query", table="prices"):
    result = database.query("SELECT * FROM prices")

# Log metrics
perf_logger.log_metric("response_time", 145.2, "ms")
perf_logger.log_counter("requests_processed", 5)
```

### Context Management
```python
logger = get_module_logger()

# Set persistent context
logger.set_context(user_id="123", session_id="abc")

# Temporary context
with logger.context(operation="download", symbol="AAPL"):
    logger.info("Starting download")  # Includes all context
```

### Decorators
```python
from vortex.logging import timed, logged

@timed("api_call")
@logged("info")
def download_data(symbol):
    # Function is automatically timed and logged
    return fetch_data(symbol)
```

## Output Formats

### Console Format
```
2024-01-15 12:00:00 [    INFO] vortex.cli.download: Starting download for AAPL
2024-01-15 12:00:01 [   ERROR] vortex.providers.barchart: Authentication failed
```

### JSON Format
```json
{
  "timestamp": "2024-01-15T12:00:00.000Z",
  "level": "INFO",
  "message": "Starting download for AAPL",
  "service": "vortex",
  "version": "0.1.3",
  "logger": "vortex.cli.download",
  "module": "download",
  "function": "execute_download",
  "line": 285,
  "correlation_id": "abc-123-def",
  "symbol": "AAPL",
  "provider": "barchart",
  "user_id": "123"
}
```

### Rich Format (Terminal)
```
🎯 12:00:00 vortex.cli.download:285 Starting download for AAPL        [INFO]
❌ 12:00:01 vortex.providers:142 Authentication failed               [ERROR]
```

## Health Checks

### Built-in Checks
- **Logging System**: Verifies logging is properly configured
- **Configuration System**: Tests configuration loading
- **File System**: Checks write permissions for logs and data

### Custom Health Checks
```python
from vortex.logging_integration import register_health_check

def check_database():
    try:
        database.ping()
        return {"healthy": True, "details": "Database responding"}
    except Exception as e:
        return {"healthy": False, "details": f"Database error: {e}"}

register_health_check("database", check_database)
```

### Health Status Endpoint
```python
from vortex.logging_integration import run_health_checks

# Returns comprehensive health status
status = run_health_checks()
```

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T12:00:00.000Z",
  "checks": {
    "logging_system": {
      "healthy": true,
      "duration_ms": 0.5,
      "details": "Logging system configured"
    },
    "config_system": {
      "healthy": true,
      "duration_ms": 12.3,
      "details": "Configuration loaded successfully"
    }
  }
}
```

## File Logging

### Log Rotation
- **Automatic rotation** when files exceed max size
- **Configurable backup count** (default: 5 files)
- **Atomic rotation** to prevent log loss

### Log File Structure
```
logs/
├── vortex.log          # Current log file
├── vortex.log.1        # Previous rotation
├── vortex.log.2        # Older rotation
└── ...
```

## Performance Features

### Operation Timing
```python
# Automatic timing with context
with perf_logger.time_operation("data_processing", records=1000):
    process_data()

# Logs:
# DEBUG: Started operation: data_processing
# INFO:  Completed operation: data_processing in 1234.56ms
```

### Metrics Collection
- **Response times** for API calls
- **Processing counts** for batch operations
- **Error rates** and success rates
- **Resource utilization** tracking

### Correlation Tracking
- **Request correlation IDs** for tracing
- **User session tracking**
- **Cross-component correlation**

## Integration

### CLI Integration
The CLI automatically configures logging based on:
1. Configuration file settings
2. Environment variables
3. Command-line verbosity flags

### Error Handling Integration
```python
try:
    risky_operation()
except VortexError as e:
    logger.error("Operation failed", 
                error_type=type(e).__name__,
                error_code=getattr(e, 'error_code', None),
                help_text=getattr(e, 'help_text', None))
```

### Configuration System Integration
```python
from vortex.config import ConfigManager
from vortex.logging_integration import configure_logging_from_manager

config_manager = ConfigManager()
configure_logging_from_manager(config_manager, "vortex", "0.1.3")
```

## Testing

### Test Logging Output
```python
def test_logging_output(caplog):
    logger = get_module_logger()
    
    with caplog.at_level(logging.INFO):
        logger.info("Test message", user_id="123")
    
    assert "Test message" in caplog.records[0].message
```

### Mock Performance Logging
```python
def test_performance(caplog):
    perf_logger = get_module_performance_logger()
    
    with perf_logger.time_operation("test_op"):
        time.sleep(0.01)
    
    messages = [r.message for r in caplog.records]
    assert any("Completed operation: test_op" in msg for msg in messages)
```

## Migration from Legacy

### Backward Compatibility
```python
# Old code still works
import logging
logger = logging.getLogger(__name__)
logger.info("Old style logging")

# Enhanced with new features
from vortex.logging_integration import get_module_logger
logger = get_module_logger()
logger.info("New style logging", context="enhanced")
```

### LoggingContext Compatibility
```python
# Legacy LoggingContext still works
from vortex.logging import LoggingContext

with LoggingContext(
    entry_msg="Starting operation",
    success_msg="Operation completed",
    failure_msg="Operation failed"
):
    perform_operation()
```

## Best Practices

### Structured Logging
- Use **named parameters** instead of string formatting
- Include **relevant context** in all log messages
- Use **appropriate log levels** (DEBUG for development, INFO for operations)

### Performance Logging
- Time **meaningful operations** (not trivial functions)
- Include **relevant metrics** with operations
- Use **correlation IDs** for request tracking

### Error Logging
- Always log **exception context**
- Include **user-actionable information**
- Use **appropriate error levels**

### Health Checks
- Keep checks **fast and lightweight**
- Return **actionable status information**
- Include **dependency checks** for critical services

## Configuration Examples

### Development Environment
```toml
[general.logging]
level = "DEBUG"
format = "rich"      # Pretty terminal output
output = ["console"]
```

### Production Environment
```toml  
[general.logging]
level = "INFO"
format = "json"      # Machine-readable
output = ["console", "file"]
file_path = "/var/log/vortex/app.log"
max_file_size = 52428800  # 50MB
backup_count = 10
```

### Docker Environment
```bash
# Environment variables for containerized deployment
VORTEX_LOGGING_LEVEL=INFO
VORTEX_LOGGING_FORMAT=json
VORTEX_LOGGING_OUTPUT=console
```

The logging system provides comprehensive observability while maintaining simplicity and performance, making it suitable for development, testing, and production environments.