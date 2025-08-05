# Error Handling Consistency Improvements

## Overview

This document outlines the comprehensive error handling improvements implemented in the Vortex project to ensure consistent error reporting, logging, and user experience across all CLI commands.

## Key Improvements

### 1. Centralized Error Handler

**Created:** `src/vortex/cli/error_handler.py`

- **CLIErrorHandler class**: Unified error handling for all exception types
- **Consistent output**: Standardized error messages with emojis and color coding
- **Rich integration**: Enhanced UI when Rich library is available
- **Structured logging**: Integration with advanced logging systems
- **Exit code consistency**: Proper exit codes for different error types

**Benefits:**
- Reduced code duplication from 200+ lines to reusable components
- Consistent user experience across all commands
- Easier maintenance and updates to error handling logic

### 2. Simplified Main CLI Module

**Modified:** `src/vortex/cli/main.py`

- **Reduced complexity**: From 536 lines to 343 lines (36% reduction)
- **Cleaner code**: Removed massive try-catch block in favor of centralized handling
- **Better separation**: Error handling logic separated from main CLI logic
- **Improved readability**: Main function now focuses on core functionality

**Before:**
```python
def main() -> None:
    try:
        cli()
    except AuthenticationError as e:
        # 200+ lines of duplicated error handling
    except ConfigurationError as e:
        # More duplicated code...
    # ... 10+ more exception handlers
```

**After:**
```python
def main() -> None:
    error_handler = create_error_handler(...)
    handle_cli_exceptions(error_handler, cli)
```

### 3. Structured Error Logging

**Enhanced:** `src/vortex/utils/logging_utils.py`

- **StructuredErrorLogger class**: Advanced error logging with context
- **JSON formatting**: Machine-readable error logs for monitoring
- **Correlation IDs**: Unique identifiers for tracking related operations
- **Operation tracking**: Start/success/failure logging for operations
- **Context preservation**: Rich metadata for debugging

**Features:**
- Automatic correlation ID generation
- Timestamp and duration tracking  
- Error context and metadata capture
- Integration with existing VortexError hierarchy
- Fallback to basic logging if advanced features unavailable

### 4. Correlation ID Management

**Created:** `src/vortex/utils/correlation.py`

- **Thread-local storage**: Correlation IDs tracked per thread
- **Decorator support**: `@with_correlation_id` and `@track_operation`
- **Context managers**: `CorrelationContext` for manual management
- **Automatic propagation**: IDs flow through function calls
- **VortexError integration**: Errors automatically tagged with correlation IDs

**Usage Examples:**
```python
# Automatic correlation ID generation
@with_correlation_id()
def download_data():
    # All logging in this function uses same correlation ID
    pass

# Manual correlation context
with CorrelationContext() as correlation_id:
    logger.log_operation_start("data_download", correlation_id)
    # ... operation code ...
    logger.log_operation_success("data_download", correlation_id)
```

### 5. Enhanced Error Context

**Improved Error Information:**
- **User-friendly messages**: Clear explanations of what went wrong
- **Actionable guidance**: Specific steps users can take to resolve issues
- **Technical details**: Additional context for debugging
- **Visual indicators**: Emojis and colors for quick error type identification
- **Correlation tracking**: Unique IDs for support and debugging

**Error Types with Standardized Handling:**
- 🔐 Authentication errors (exit code 2)
- ⚙️  Configuration errors (exit code 3)  
- 🌐 Connection errors (exit code 4)
- 🔒 Permission errors (exit code 5)
- 💾 Storage errors (exit code 6)
- 📊 Provider errors (exit code 7)
- 📈 Instrument errors (exit code 8)
- ⌨️  CLI errors (exit code 9)
- ❌ General Vortex errors (exit code 10)
- 💻 System errors (exit code 11)
- 📦 Dependency errors (exit code 12)

## Implementation Details

### Error Handler Factory

```python
def create_error_handler(
    rich_available: bool = False,
    console: Any = None,
    config_available: bool = False,
    get_logger_func: Optional[callable] = None
) -> CLIErrorHandler:
    """Factory function to create a configured error handler."""
```

### Universal Exception Wrapper

```python
def handle_cli_exceptions(
    error_handler: CLIErrorHandler,
    func: callable,
    *args, **kwargs
) -> Any:
    """Universal exception handler wrapper for CLI operations."""
```

### Structured Logging Integration

```python
class StructuredErrorLogger:
    def log_error(self, error, message, correlation_id=None, context=None):
        """Log error with full structured context."""
        
    def log_operation_start(self, operation, correlation_id=None):
        """Track operation start with correlation ID."""
        
    def log_operation_success(self, operation, correlation_id):
        """Track successful operation completion."""
```

## Benefits Delivered

### 1. **Consistency**
- Unified error handling across all CLI commands
- Standardized error messages and exit codes
- Consistent logging format and structure

### 2. **Maintainability**  
- Single location for error handling logic updates
- Reduced code duplication (200+ lines removed from main CLI)
- Clear separation of concerns

### 3. **Observability**
- Structured logging for better monitoring
- Correlation IDs for tracking related operations
- Rich context for debugging and support

### 4. **User Experience**
- Clear, actionable error messages
- Visual indicators (emojis, colors) when Rich is available
- Helpful guidance for resolving issues

### 5. **Developer Experience**
- Easy-to-use decorators for correlation tracking
- Automatic error context capture
- Comprehensive logging with minimal code changes

## Compatibility

- **Backward Compatible**: All existing exception types still work
- **Graceful Degradation**: Falls back to basic logging if advanced features unavailable
- **Rich Integration**: Enhanced UI when Rich library is present
- **Thread Safe**: Correlation IDs properly isolated per thread

## Migration Guide

### For New Code
```python
# Use decorators for automatic correlation tracking
@with_correlation_id()
def my_operation():
    # Logging automatically includes correlation ID
    pass

# Or use context managers
with CorrelationContext() as corr_id:
    structured_logger.log_operation_start("my_op", corr_id)
    # ... operation code ...
```

### For Existing Code
- No changes required - existing error handling continues to work
- VortexError exceptions automatically get correlation IDs
- Structured logging captures additional context automatically

## Future Enhancements

1. **Metrics Integration**: Add metrics collection for error rates and types
2. **External Logging**: Integration with external logging services (ELK, Splunk)
3. **Error Recovery**: Automatic retry mechanisms for transient errors
4. **User Feedback**: Error reporting integration for unknown issues
5. **Performance Monitoring**: Operation duration tracking and alerting

## Files Modified

### New Files
- `src/vortex/cli/error_handler.py` - Centralized error handling
- `src/vortex/utils/correlation.py` - Correlation ID management
- `ERROR_HANDLING_IMPROVEMENTS.md` - This documentation

### Modified Files  
- `src/vortex/cli/main.py` - Simplified using centralized error handler
- `src/vortex/utils/logging_utils.py` - Added structured error logging

### Impact Summary
- **Lines Reduced**: 193 lines removed from main CLI (36% reduction)
- **Code Reuse**: Error handling logic now reusable across components
- **Maintainability**: Single location for all error handling updates
- **Observability**: Rich structured logging with correlation tracking
- **User Experience**: Consistent, helpful error messages with visual indicators