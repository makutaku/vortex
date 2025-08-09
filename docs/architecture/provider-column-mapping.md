# Provider Column Mapping Architecture

## Overview

The Vortex column mapping system has been refactored to follow the **Provider-Owned Column Mapping** pattern, eliminating the need to modify central files when adding new data providers.

## Problem Solved

**Before:** Adding new providers required modifying the central `columns.py` file:
- ❌ Violates Open/Closed Principle  
- ❌ Creates tight coupling between core and provider logic
- ❌ Bloats central files with provider-specific knowledge
- ❌ Makes testing and maintenance difficult

**After:** Each provider owns its column mapping logic:
- ✅ Follows Open/Closed Principle (open for extension, closed for modification)
- ✅ Loose coupling - core logic independent of specific providers
- ✅ Clean separation of concerns
- ✅ Easy testing and maintenance

## Architecture

### 1. Core Components

#### `ProviderColumnMapping` (Abstract Base Class)
```python
from abc import ABC, abstractmethod

class ProviderColumnMapping(ABC):
    @abstractmethod
    def get_column_mapping(self, df_columns: List[str]) -> Dict[str, str]:
        """Map provider columns to internal standard."""
        pass
    
    @abstractmethod  
    def get_provider_specific_columns(self) -> List[str]:
        """Get provider-specific columns to preserve."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider identifier."""
        pass
```

#### `ColumnMappingRegistry` (Singleton Registry)
- Manages provider column mappings
- Auto-discovery through registration
- Backward-compatible API

### 2. Provider Implementation

Each provider implements its own column mapping:

```python
# src/vortex/infrastructure/providers/yahoo/column_mapping.py
class YahooColumnMapping(ProviderColumnMapping):
    ADJ_CLOSE_COLUMN = "Adj Close"
    
    @property
    def provider_name(self) -> str:
        return "yahoo"
    
    def get_provider_specific_columns(self) -> List[str]:
        return [self.ADJ_CLOSE_COLUMN, ...]
    
    def get_column_mapping(self, df_columns: List[str]) -> Dict[str, str]:
        # Provider-specific mapping logic
        pass
```

### 3. Auto-Registration

Providers auto-register when imported:

```python
# src/vortex/infrastructure/providers/yahoo/__init__.py
from .column_mapping import YahooColumnMapping
from vortex.models.column_registry import register_provider_column_mapping

# Auto-register when module is imported
register_provider_column_mapping(YahooColumnMapping())
```

## Adding New Providers

### Step 1: Create Column Mapping
```python
# src/vortex/infrastructure/providers/newprovider/column_mapping.py
class NewProviderColumnMapping(ProviderColumnMapping):
    # Provider-specific columns
    CUSTOM_COLUMN = "Custom Data"
    
    @property
    def provider_name(self) -> str:
        return "newprovider"
    
    def get_provider_specific_columns(self) -> List[str]:
        return [self.CUSTOM_COLUMN]
    
    def get_column_mapping(self, df_columns: List[str]) -> Dict[str, str]:
        # Custom mapping logic
        return {
            'provider_datetime': 'Datetime',
            'provider_open': 'Open',
            # ... mapping logic
        }
```

### Step 2: Auto-Register
```python
# src/vortex/infrastructure/providers/newprovider/__init__.py
from .column_mapping import NewProviderColumnMapping
from vortex.models.column_registry import register_provider_column_mapping

register_provider_column_mapping(NewProviderColumnMapping())
```

### Step 3: That's It!
No need to modify any existing files. The new provider works with all existing APIs:

```python
from vortex.models.columns import get_provider_expected_columns, get_column_mapping

# Automatically works with new provider
required, optional = get_provider_expected_columns("newprovider")
mapping = get_column_mapping("newprovider", ["provider_open", "provider_close"])
```

## Benefits

### 1. Scalability
- ✅ **10 providers:** No bloated central files
- ✅ **100 providers:** Each owns its logic
- ✅ **1000 providers:** Architecture scales linearly

### 2. Maintainability  
- ✅ **Provider changes:** Modify only provider-specific files
- ✅ **Core changes:** No impact on provider logic
- ✅ **Testing:** Test providers in isolation

### 3. Extensibility
- ✅ **Plugin system:** Providers can be dynamically loaded
- ✅ **Third-party providers:** External packages can add providers
- ✅ **Custom mappings:** Users can override standard mappings

## Backward Compatibility

The refactor maintains 100% backward compatibility:

```python
# All existing code continues to work unchanged
from vortex.models.columns import get_provider_expected_columns, get_column_mapping

required, optional = get_provider_expected_columns("yahoo")  # Works
mapping = get_column_mapping("yahoo", df.columns)           # Works
```

The system gracefully falls back to legacy behavior for unknown providers.

## Migration Path

### Phase 1: Registry Introduction (Current)
- ✅ New registry system implemented
- ✅ Providers auto-register column mappings
- ✅ 100% backward compatibility maintained
- ✅ Existing APIs delegate to registry

### Phase 2: Legacy Deprecation (Future)
- Deprecate legacy constants in `columns.py`
- Add deprecation warnings
- Update documentation to recommend registry approach

### Phase 3: Legacy Removal (Future)
- Remove deprecated constants
- Simplify `columns.py` to core functionality only
- Complete transition to provider-owned approach

## Example: Real vs Legacy Approach

### Adding AlphaVantage Provider

**Old Approach (Required modifying 3 files):**
```python
# 1. Modify src/vortex/models/columns.py
ALPHAVANTAGE_ADJUSTED_CLOSE = "5. adjusted close"
ALPHAVANTAGE_SPECIFIC_COLUMNS = [ALPHAVANTAGE_ADJUSTED_CLOSE, ...]

# 2. Modify get_provider_expected_columns()
elif provider_name.lower() == 'alphavantage':
    optional = ALPHAVANTAGE_SPECIFIC_COLUMNS

# 3. Modify get_column_mapping()
'alphavantage': {
    '1. open': OPEN_COLUMN,
    # ... 50 lines of mapping logic
}
```

**New Approach (Create 1 new file):**
```python
# 1. Create src/vortex/infrastructure/providers/alphavantage/column_mapping.py
class AlphaVantageColumnMapping(ProviderColumnMapping):
    # All provider logic contained here
    pass

# 2. Register in __init__.py
register_provider_column_mapping(AlphaVantageColumnMapping())
```

## Testing

Provider-specific mappings can be tested in isolation:

```python
def test_alphavantage_column_mapping():
    mapping = AlphaVantageColumnMapping()
    result = mapping.get_column_mapping(["1. open", "2. high"])
    assert result == {"1. open": "Open", "2. high": "High"}
```

## Conclusion

The Provider-Owned Column Mapping architecture enables Vortex to scale to hundreds of data providers while maintaining clean, maintainable code that follows SOLID principles. Each provider owns its mapping logic, eliminating central file bloat and enabling independent development and testing.