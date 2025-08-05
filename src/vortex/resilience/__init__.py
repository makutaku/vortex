"""
Compatibility wrapper for the resilience package.

This module maintains backward compatibility with existing code that imports
from vortex.resilience. The actual implementation is in vortex.shared.resilience.

DEPRECATED: This package is deprecated. Import from vortex.shared.resilience instead.
"""

import warnings

# Import everything from the new resilience package
from ..shared.resilience import *

# Issue deprecation warning
warnings.warn(
    "Importing from vortex.resilience package is deprecated. "
    "Use 'from vortex.shared.resilience import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)