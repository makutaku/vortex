"""
Vortex Exception Hierarchy

This package provides a comprehensive exception hierarchy for the Vortex financial data
download automation tool. All exceptions include actionable error messages and
context to help users resolve issues.

Exception Hierarchy:
    VortexError (base)
    ├── ConfigurationError
    │   ├── InvalidConfigurationError
    │   ├── MissingConfigurationError
    │   └── ConfigurationValidationError
    ├── DataProviderError  
    │   ├── AuthenticationError
    │   ├── RateLimitError
    │   ├── ConnectionError
    │   ├── DataNotFoundError
    │   └── AllowanceLimitExceededError
    ├── DataStorageError
    │   ├── FileStorageError
    │   ├── PermissionError
    │   └── DiskSpaceError
    ├── InstrumentError
    │   ├── InvalidInstrumentError
    │   └── UnsupportedInstrumentError
    └── CLIError
        ├── InvalidCommandError
        ├── MissingArgumentError
        └── UserAbortError

This package provides focused exception components:
- base: Core VortexError base class
- config: Configuration-related exceptions
- providers: Data provider exceptions (auth, connection, data)
- storage: File and disk storage exceptions
- instruments: Financial instrument validation exceptions
- cli: Command-line interface exceptions
"""

# Import all exceptions for backward compatibility
from .base import VortexError

# Configuration exceptions
from .config import (
    ConfigurationError,
    InvalidConfigurationError,
    MissingConfigurationError,
    ConfigurationValidationError,
)

# Data provider exceptions
from .providers import (
    DataProviderError,
    AuthenticationError,
    RateLimitError,
    VortexConnectionError,
    DataNotFoundError,
    AllowanceLimitExceededError,
)

# For backward compatibility
ConnectionError = VortexConnectionError

# Storage exceptions
from .storage import (
    DataStorageError,
    FileStorageError,
    VortexPermissionError,
    DiskSpaceError,
)

# For backward compatibility
PermissionError = VortexPermissionError

# Instrument exceptions
from .instruments import (
    InstrumentError,
    InvalidInstrumentError,
    UnsupportedInstrumentError,
)

# CLI exceptions
from .cli import (
    CLIError,
    InvalidCommandError,
    MissingArgumentError,
    UserAbortError,
)

# Plugin exceptions
from .plugins import (
    PluginError,
    PluginNotFoundError,
    PluginValidationError,
    PluginConfigurationError,
    PluginLoadError,
)

# Legacy compatibility removed - no customers to break

__all__ = [
    # Base
    'VortexError',
    
    # Configuration
    'ConfigurationError',
    'InvalidConfigurationError',
    'MissingConfigurationError',
    'ConfigurationValidationError',
    
    # Data providers
    'DataProviderError',
    'AuthenticationError',
    'RateLimitError',
    'VortexConnectionError',
    'ConnectionError',  # Backward compatibility alias
    'DataNotFoundError',
    'AllowanceLimitExceededError',
    
    # Storage
    'DataStorageError',
    'FileStorageError',
    'VortexPermissionError',
    'PermissionError',  # Backward compatibility alias
    'DiskSpaceError',
    
    # Instruments
    'InstrumentError',
    'InvalidInstrumentError',
    'UnsupportedInstrumentError',
    
    # CLI
    'CLIError',
    'InvalidCommandError',
    'MissingArgumentError',
    'UserAbortError',
    
    # Plugins
    'PluginError',
    'PluginNotFoundError',
    'PluginValidationError',
    'PluginConfigurationError',
    'PluginLoadError',
    
]