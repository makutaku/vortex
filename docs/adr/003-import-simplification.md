# Import Dependencies and Architecture Simplification

## Overview

This document outlines the comprehensive simplification of import dependencies and architecture implemented in the Vortex CLI to eliminate complex try/catch blocks and provide consistent fallback behavior.

## Problems Addressed

### Before: Complex Import Handling

The original `src/vortex/cli/main.py` suffered from:

1. **6 different try/except blocks** for optional imports (lines 24-102)
2. **Scattered fallback implementations** throughout the module
3. **Maintenance complexity** - changes required updates in multiple locations  
4. **Inconsistent error handling** - different patterns for different imports
5. **Poor testability** - difficult to test fallback scenarios

**Original Code Structure:**
```python
# Complex scattered imports
try:
    from ..config import ConfigManager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

try:
    from ..resilience.correlation import CorrelationIdManager
    RESILIENCE_IMPORTS_AVAILABLE = True
except ImportError:
    RESILIENCE_IMPORTS_AVAILABLE = False
    # Inline fallback implementations
    def with_correlation(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

# ... 4 more similar blocks
```

## Solution: Dependency Injection System

### New Architecture Components

**1. Centralized Dependency Registry (`src/vortex/cli/dependencies.py`)**
- Single location for all dependency management
- Automatic fallback registration
- Clean API for dependency access
- Comprehensive logging and debugging

**2. Structured Fallback Implementations**
- `NullUX` class for minimal UX when Rich unavailable
- `NullWizard` class for basic command wizard functionality
- `NullCorrelationManager` for resilience-free environments
- Consistent interface across all fallbacks

**3. Clean Import Functions**
- Organized import functions per module group
- Centralized error handling
- Automatic fallback assignment

## Implementation Details

### Dependency Registry System

```python
class DependencyRegistry:
    """Registry for managing optional dependencies and fallback implementations."""
    
    def register_optional_module(self, name: str, import_func: Callable, fallback: Any = None):
        """Register an optional module with optional fallback."""
        try:
            module = import_func()
            self._modules[name] = module
            self._availability[name] = True
        except ImportError:
            self._modules[name] = fallback
            self._availability[name] = False
```

### Clean API Usage

**Before (main.py lines 24-102):**
- 6 complex try/except blocks
- Inline fallback definitions
- Scattered availability flags

**After (main.py lines 25-26):**
```python
from .dependencies import get_dependency, is_available, get_availability_summary

# Clean usage throughout the file
commands = get_dependency('commands')
ux_func = get_dependency('ux', 'get_ux')
rich_console = get_dependency('rich', 'Console')
```

## Benefits Delivered

### 1. **Dramatic Code Reduction**
- **Main CLI module**: Reduced import complexity from 78 lines to 2 lines
- **Eliminated 6 try/except blocks** scattered throughout the main module
- **Removed inline fallback implementations** (40+ lines of dummy classes)

### 2. **Improved Maintainability**
- Single location (`dependencies.py`) for all import logic
- Consistent fallback patterns across all optional dependencies
- Easy to add new optional dependencies
- Clear separation of concerns

### 3. **Better Testability**
- Easy to test fallback scenarios by manipulating the registry
- Centralized dependency mocking
- Clear availability checking APIs

### 4. **Enhanced Reliability**
- Consistent error handling across all optional imports
- Proper fallback behavior in all scenarios
- No runtime import failures

### 5. **Cleaner Architecture**
- Dependency injection pattern eliminates tight coupling
- Consistent interface for all optional components
- Better separation of concerns

## Fallback Implementations

### NullUX Class
```python
class NullUX:
    """Minimal UX implementation when Rich/advanced UX unavailable."""
    
    def print_panel(self, text: str, title: str = "", style: str = ""):
        """Print panel content as plain text."""
        if title:
            print(f"\n{title}")
            print("=" * len(title))
        print(text)
```

### NullWizard Class
```python
class NullWizard:
    """Minimal command wizard when advanced wizard unavailable."""
    
    def run_download_wizard(self) -> dict:
        """Simple download configuration."""
        symbol = input("Enter symbol (e.g., AAPL): ").strip().upper()
        return {"symbols": [symbol], "execute": True} if symbol else {"execute": False}
```

## Migration Benefits

### For Developers
- **Simpler code** - no complex import handling in main modules
- **Easier testing** - centralized dependency management
- **Better debugging** - clear availability checking and logging

### For Users
- **Consistent experience** - graceful degradation when dependencies missing
- **Clear error messages** - helpful guidance when features unavailable
- **No runtime surprises** - predictable fallback behavior

### For Deployment
- **Container-friendly** - works in minimal environments
- **Dependency flexibility** - graceful handling of missing optional features
- **Consistent behavior** - same CLI interface regardless of available dependencies

## Code Quality Improvements

### Reduced Complexity
**Before:**
- Cyclomatic complexity: High (multiple nested try/except blocks)
- Lines of code: 343 lines (with 78 lines of import handling)
- Import-related code: 23% of file

**After:**
- Import complexity: Eliminated (2 simple imports)
- Cleaner main.py: Focus on core CLI logic
- Import-related code: <1% of file

### Better Error Handling
- Consistent error patterns across all dependencies
- Centralized logging of import issues
- Clear availability checking APIs

### Enhanced Maintainability
- Single location for all dependency management
- Easy to add new optional dependencies
- Consistent patterns for fallback implementations

## Testing and Validation

### Functional Testing
✅ **Local environment** - All commands work with full dependencies
✅ **Container environment** - Graceful fallback behavior
✅ **Missing dependencies** - Clean error messages and fallback UX
✅ **Mixed environments** - Partial dependency availability handled correctly

### Performance Impact
- **Startup time**: No measurable impact
- **Memory usage**: Slightly reduced (fewer imported modules stored)
- **Runtime performance**: No impact on core functionality

## Future Benefits

### Extensibility
- Easy to add new optional features
- Consistent pattern for plugin system
- Simple testing of different dependency combinations

### Maintenance
- Single location for import-related updates
- Consistent fallback patterns
- Clear debugging and availability checking

## Files Modified

### New Files
- **`src/vortex/cli/dependencies.py`** - Complete dependency injection system (324 lines)

### Modified Files
- **`src/vortex/cli/main.py`** - Simplified from complex import handling to clean dependency injection usage

### Impact Summary
- **Lines of import complexity**: Reduced from 78 to 2 in main.py
- **Try/except blocks**: Reduced from 6 to 0 in main.py  
- **Fallback implementations**: Moved from inline to structured classes
- **Maintainability**: Single location for all dependency management
- **Testability**: Centralized dependency mocking and availability checking
- **User experience**: Consistent fallback behavior across all features

The import simplification provides a solid foundation for future development while dramatically reducing complexity and improving maintainability.