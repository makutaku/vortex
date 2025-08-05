"""
Data storage-related exceptions.

All exceptions related to file operations, disk space, and data persistence.
"""

from pathlib import Path
from typing import Optional

from .base import VortexError


class DataStorageError(VortexError):
    """Base class for data storage-related errors."""
    pass


class FileStorageError(DataStorageError):
    """Raised when file storage operations fail."""
    
    def __init__(self, operation: str, file_path: Path, details: Optional[str] = None):
        self.operation = operation
        self.file_path = file_path
        
        message = f"File {operation} failed: {file_path}"
        if details:
            message += f" - {details}"
        
        help_text = f"Check file permissions and available disk space for {file_path.parent}"
        super().__init__(message, help_text, "FILE_STORAGE_ERROR")


class VortexPermissionError(DataStorageError):
    """Raised when file system permissions prevent operations."""
    
    def __init__(self, path: Path, operation: str = "access"):
        message = f"Permission denied: cannot {operation} {path}"
        help_text = f"Check file/directory permissions for {path} and ensure Vortex has the necessary access rights"
        super().__init__(message, help_text, "PERMISSION_DENIED")


class DiskSpaceError(DataStorageError):
    """Raised when insufficient disk space is available."""
    
    def __init__(self, path: Path, required_space: Optional[str] = None):
        message = f"Insufficient disk space: {path}"
        if required_space:
            message += f" (need at least {required_space})"
        
        help_text = f"Free up disk space in {path} or choose a different output directory"
        super().__init__(message, help_text, "DISK_SPACE_ERROR")