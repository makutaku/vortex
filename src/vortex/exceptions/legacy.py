"""
Legacy exception compatibility.

Maintains compatibility with existing code while migrating to the new exception system.
These will be removed in a future version.
"""

import warnings

from .providers import DataProviderError


class DownloadError(DataProviderError):
    """Legacy exception - use DataProviderError instead."""
    
    def __init__(self, status: str, msg: str):
        warnings.warn(
            "DownloadError is deprecated. Use DataProviderError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__("legacy", f"Download failed ({status}): {msg}", error_code="DOWNLOAD_ERROR")
        self.status = status
        self.msg = msg


class LowDataError(DataProviderError):
    """Legacy exception - use DataNotFoundError instead."""
    
    def __init__(self, provider: str = "unknown"):
        warnings.warn(
            "LowDataError is deprecated. Use DataNotFoundError instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(provider, "Insufficient data available", error_code="LOW_DATA")


# Re-export legacy exceptions for backward compatibility
from .providers import DataNotFoundError as NotFoundError
from .providers import AllowanceLimitExceededError as AllowanceLimitExceeded