"""
Compatibility wrapper for the refactored exception system.

This module maintains backward compatibility with existing code that imports
from vortex.shared.exceptions. The actual implementation has been split into focused
modules in the vortex.exceptions package.

DEPRECATED: This module is deprecated. Import from vortex.shared.exceptions package instead:
    from vortex.shared.exceptions import VortexError, ConfigurationError, etc.
"""

import warnings

# Import everything from the new exceptions package
from .shared.exceptions import *

# Issue deprecation warning
warnings.warn(
    "Importing from vortex.shared.exceptions module is deprecated. "
    "Use 'from vortex.shared.exceptions import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)