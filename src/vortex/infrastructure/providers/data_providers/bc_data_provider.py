"""
Compatibility wrapper for the refactored Barchart data provider.

This module maintains backward compatibility with existing code that imports
BarchartDataProvider from bc_data_provider. The actual implementation has been
split into focused modules in the barchart package.

DEPRECATED: This module is deprecated. Import from vortex.infrastructure.providers.data_providers.barchart instead:
    from vortex.infrastructure.providers.data_providers.barchart import BarchartDataProvider
"""

import warnings

# Import from the new modular structure
from .barchart import BarchartDataProvider

# Issue deprecation warning
warnings.warn(
    "Importing BarchartDataProvider from bc_data_provider is deprecated. "
    "Use 'from vortex.infrastructure.providers.data_providers.barchart import BarchartDataProvider' instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export for backward compatibility
__all__ = ['BarchartDataProvider']