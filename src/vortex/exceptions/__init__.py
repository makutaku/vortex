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

# Import all exceptions
from .base import VortexError

# CLI exceptions
from .cli import CLIError, InvalidCommandError, MissingArgumentError, UserAbortError

# Configuration exceptions
from .config import (
    ConfigurationError,
    ConfigurationValidationError,
    InvalidConfigurationError,
    MissingConfigurationError,
)

# Instrument exceptions
from .instruments import (
    InstrumentError,
    InvalidInstrumentError,
    UnsupportedInstrumentError,
)

# Plugin exceptions
from .plugins import (
    PluginConfigurationError,
    PluginError,
    PluginLoadError,
    PluginNotFoundError,
    PluginValidationError,
)

# Data provider exceptions
from .providers import (
    AllowanceLimitExceededError,
    AuthenticationError,
    DataNotFoundError,
    DataProviderError,
    RateLimitError,
    VortexConnectionError,
)

# Storage exceptions
from .storage import (
    DataStorageError,
    DiskSpaceError,
    FileStorageError,
    VortexPermissionError,
)

__all__ = [
    # Base
    "VortexError",
    # Configuration
    "ConfigurationError",
    "InvalidConfigurationError",
    "MissingConfigurationError",
    "ConfigurationValidationError",
    # Data providers
    "DataProviderError",
    "AuthenticationError",
    "RateLimitError",
    "VortexConnectionError",
    "DataNotFoundError",
    "AllowanceLimitExceededError",
    # Storage
    "DataStorageError",
    "FileStorageError",
    "VortexPermissionError",
    "DiskSpaceError",
    # Instruments
    "InstrumentError",
    "InvalidInstrumentError",
    "UnsupportedInstrumentError",
    # CLI
    "CLIError",
    "InvalidCommandError",
    "MissingArgumentError",
    "UserAbortError",
    # Plugins
    "PluginError",
    "PluginNotFoundError",
    "PluginValidationError",
    "PluginConfigurationError",
    "PluginLoadError",
]
