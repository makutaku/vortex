"""
Data storage-related exceptions.

All exceptions related to file operations, disk space, and data persistence.
"""

from pathlib import Path
from typing import Optional

from .base import VortexError


class DataStorageError(VortexError):
    """Base class for data storage-related errors."""


class FileStorageError(DataStorageError):
    """Raised when file storage operations fail."""

    def __init__(self, operation: str, file_path: Path, details: Optional[str] = None):
        from .base import ExceptionContext

        self.operation = operation
        self.file_path = file_path

        message = f"File {operation} failed: {file_path}"
        if details:
            message += f" - {details}"

        help_text = (
            f"Check file permissions and available disk space for {file_path.parent}"
        )
        context = ExceptionContext(help_text=help_text, error_code="FILE_STORAGE_ERROR")
        super().__init__(message, context)


class VortexPermissionError(DataStorageError):
    """Raised when file system permissions prevent operations."""

    def __init__(self, path: Path, operation: str = "access"):
        from .base import ExceptionContext

        message = f"Permission denied: cannot {operation} {path}"
        help_text = f"Check file/directory permissions for {path} and ensure Vortex has the necessary access rights"
        context = ExceptionContext(help_text=help_text, error_code="PERMISSION_DENIED")
        super().__init__(message, context)


class DiskSpaceError(DataStorageError):
    """Raised when insufficient disk space is available."""

    def __init__(self, path: Path, required_space: Optional[str] = None):
        from .base import ExceptionContext

        message = f"Insufficient disk space: {path}"
        if required_space:
            message += f" (need at least {required_space})"

        help_text = (
            f"Free up disk space in {path} or choose a different output directory"
        )
        context = ExceptionContext(help_text=help_text, error_code="DISK_SPACE_ERROR")
        super().__init__(message, context)
