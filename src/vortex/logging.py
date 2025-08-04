"""
Compatibility wrapper for the refactored logging system.

This module maintains backward compatibility with existing code that imports
from vortex.logging. The actual implementation has been split into focused
modules in the vortex.logging package.

DEPRECATED: This module is deprecated. Import from vortex.logging package instead:
    from vortex.logging import get_logger, LoggingConfig, configure_logging
"""

import warnings

# Import everything from the new logging package
from .logging import *

# Issue deprecation warning
warnings.warn(
    "Importing from vortex.logging module is deprecated. "
    "Use 'from vortex.logging import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)