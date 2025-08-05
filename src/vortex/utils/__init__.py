"""
Compatibility wrapper for the utils package.

This module maintains backward compatibility with existing code that imports
from vortex.utils. The actual implementation is in vortex.shared.utils.

DEPRECATED: This package is deprecated. Import from vortex.shared.utils instead.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from vortex.utils package is deprecated. "
    "Use 'from vortex.shared.utils import ...' instead.",
    DeprecationWarning,
    stacklevel=2
)