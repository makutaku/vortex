"""
Tests for storage exception classes.
"""

from pathlib import Path
import pytest

from vortex.exceptions.storage import (
    DataStorageError,
    FileStorageError,
    VortexPermissionError,
    DiskSpaceError
)


class TestDataStorageError:
    """Test base data storage error class."""
    
    def test_data_storage_error_creation(self):
        """Test creating DataStorageError."""
        error = DataStorageError("Test storage error")
        
        # The base VortexError class adds error ID, so we check if message is included
        str_repr = str(error)
        assert "Test storage error" in str_repr
        assert "Error ID:" in str_repr
        assert error.message == "Test storage error"
        assert isinstance(error, Exception)


class TestFileStorageError:
    """Test file storage error functionality."""
    
    def test_file_storage_error_basic(self):
        """Test basic FileStorageError creation."""
        path = Path("/tmp/test.csv")
        error = FileStorageError("write", path)
        
        assert "write failed" in str(error)
        assert "/tmp/test.csv" in str(error)
        assert error.operation == "write"
        assert error.file_path == path
    
    def test_file_storage_error_with_details(self):
        """Test FileStorageError with details."""
        path = Path("/tmp/test.csv")
        error = FileStorageError("read", path, "File is corrupted")
        
        assert "read failed" in str(error)
        assert "/tmp/test.csv" in str(error)
        assert "File is corrupted" in str(error)
        assert error.operation == "read"
        assert error.file_path == path
    
    def test_file_storage_error_context(self):
        """Test FileStorageError context information."""
        path = Path("/data/output.csv")
        error = FileStorageError("save", path, "Permission denied")
        
        # Should have context with help text
        assert hasattr(error, 'context')
        assert hasattr(error, 'help_text')
        assert hasattr(error, 'error_code')
        assert "disk space" in error.help_text
        assert error.error_code == "FILE_STORAGE_ERROR"
        assert "/data" in error.help_text


class TestVortexPermissionError:
    """Test permission error functionality."""
    
    def test_permission_error_default_operation(self):
        """Test VortexPermissionError with default operation."""
        path = Path("/protected/file.txt")
        error = VortexPermissionError(path)
        
        assert "Permission denied" in str(error)
        assert "cannot access" in str(error)
        assert "/protected/file.txt" in str(error)
    
    def test_permission_error_custom_operation(self):
        """Test VortexPermissionError with custom operation."""
        path = Path("/protected/directory")
        error = VortexPermissionError(path, "write to")
        
        assert "Permission denied" in str(error)
        assert "cannot write to" in str(error)
        assert "/protected/directory" in str(error)
    
    def test_permission_error_context(self):
        """Test VortexPermissionError context information."""
        path = Path("/restricted/data")
        error = VortexPermissionError(path, "create")
        
        # Should have context with help text
        assert hasattr(error, 'context')
        assert "permissions" in error.help_text
        assert "PERMISSION_DENIED" in error.error_code
        assert "/restricted/data" in error.help_text


class TestDiskSpaceError:
    """Test disk space error functionality."""
    
    def test_disk_space_error_basic(self):
        """Test basic DiskSpaceError creation."""
        path = Path("/tmp")
        error = DiskSpaceError(path)
        
        assert "Insufficient disk space" in str(error)
        assert "/tmp" in str(error)
    
    def test_disk_space_error_with_required_space(self):
        """Test DiskSpaceError with required space information."""
        path = Path("/data")
        error = DiskSpaceError(path, "500MB")
        
        assert "Insufficient disk space" in str(error)
        assert "/data" in str(error)
        assert "need at least 500MB" in str(error)
    
    def test_disk_space_error_context(self):
        """Test DiskSpaceError context information."""
        path = Path("/output")
        error = DiskSpaceError(path, "1GB")
        
        # Should have context with help text
        assert hasattr(error, 'context')
        assert "Free up disk space" in error.help_text
        assert "DISK_SPACE_ERROR" in error.error_code
        assert "/output" in error.help_text
    
    def test_disk_space_error_without_required_space(self):
        """Test DiskSpaceError without required space info."""
        path = Path("/var/data")
        error = DiskSpaceError(path)
        
        error_msg = str(error)
        assert "Insufficient disk space: /var/data" in error_msg
        assert "need at least" not in error_msg


class TestStorageErrorInheritance:
    """Test storage error inheritance hierarchy."""
    
    def test_file_storage_error_inheritance(self):
        """Test that FileStorageError inherits correctly."""
        path = Path("/test.csv")
        error = FileStorageError("write", path)
        
        assert isinstance(error, DataStorageError)
        assert isinstance(error, Exception)
    
    def test_permission_error_inheritance(self):
        """Test that VortexPermissionError inherits correctly."""
        path = Path("/test")
        error = VortexPermissionError(path)
        
        assert isinstance(error, DataStorageError)
        assert isinstance(error, Exception)
    
    def test_disk_space_error_inheritance(self):
        """Test that DiskSpaceError inherits correctly."""
        path = Path("/test")
        error = DiskSpaceError(path)
        
        assert isinstance(error, DataStorageError)
        assert isinstance(error, Exception)


class TestStorageErrorStringRepresentation:
    """Test string representations of storage errors."""
    
    def test_all_storage_errors_have_meaningful_messages(self):
        """Test that all storage errors provide meaningful string representations."""
        path = Path("/example/path")
        
        file_error = FileStorageError("read", path, "File not found")
        perm_error = VortexPermissionError(path, "modify")
        disk_error = DiskSpaceError(path, "2GB")
        
        # All should have meaningful, different messages
        assert len(str(file_error)) > 10
        assert len(str(perm_error)) > 10
        assert len(str(disk_error)) > 10
        
        # Messages should be different
        assert str(file_error) != str(perm_error)
        assert str(perm_error) != str(disk_error)
        assert str(file_error) != str(disk_error)
        
        # All should mention the path
        assert str(path) in str(file_error)
        assert str(path) in str(perm_error)  
        assert str(path) in str(disk_error)


class TestStorageErrorAttributes:
    """Test storage error attributes and properties."""
    
    def test_file_storage_error_attributes(self):
        """Test FileStorageError attributes."""
        path = Path("/data/file.csv")
        operation = "delete"
        error = FileStorageError(operation, path, "Access denied")
        
        assert error.operation == operation
        assert error.file_path == path
        assert hasattr(error, 'context')
    
    def test_permission_error_path_types(self):
        """Test VortexPermissionError with different path types."""
        # Test with string path
        str_path = "/tmp/test"
        path_obj = Path(str_path)
        
        error = VortexPermissionError(path_obj, "read")
        
        assert str_path in str(error)
    
    def test_disk_space_error_space_formatting(self):
        """Test DiskSpaceError space requirement formatting."""
        path = Path("/data")
        
        # Test with different space formats
        space_formats = ["100MB", "1.5GB", "500KB", "2TB"]
        
        for space in space_formats:
            error = DiskSpaceError(path, space)
            assert space in str(error)
            assert "need at least" in str(error)


class TestStorageErrorEdgeCases:
    """Test storage error edge cases and boundary conditions."""
    
    def test_file_storage_error_empty_details(self):
        """Test FileStorageError with empty details string."""
        path = Path("/test.csv")
        error = FileStorageError("write", path, "")
        
        # Empty details should not add extra text
        assert "write failed: /test.csv" in str(error)
        assert " - " not in str(error)  # No details separator
    
    def test_file_storage_error_none_details(self):
        """Test FileStorageError with None details."""
        path = Path("/test.csv")
        error = FileStorageError("read", path, None)
        
        # None details should not add extra text
        assert "read failed: /test.csv" in str(error)
        assert " - " not in str(error)  # No details separator
    
    def test_permission_error_various_operations(self):
        """Test VortexPermissionError with various operation types."""
        path = Path("/restricted")
        operations = ["read", "write", "execute", "create", "delete", "modify"]
        
        for op in operations:
            error = VortexPermissionError(path, op)
            assert f"cannot {op}" in str(error)
            assert str(path) in str(error)
    
    def test_disk_space_error_different_path_types(self):
        """Test DiskSpaceError with different path representations."""
        paths = [
            Path("/"),
            Path("/home/user"),
            Path("./relative/path"),
            Path("/very/long/path/with/many/directories/that/might/cause/issues")
        ]
        
        for path in paths:
            error = DiskSpaceError(path, "1GB")
            assert str(path) in str(error)
            assert "1GB" in str(error)
    
    def test_storage_errors_with_relative_paths(self):
        """Test storage errors with relative paths."""
        rel_path = Path("./data/file.txt")
        
        file_error = FileStorageError("save", rel_path)
        perm_error = VortexPermissionError(rel_path)
        disk_error = DiskSpaceError(rel_path)
        
        for error in [file_error, perm_error, disk_error]:
            assert "./data/file.txt" in str(error) or "data/file.txt" in str(error)
    
    def test_context_error_codes_are_unique(self):
        """Test that different storage errors have unique error codes."""
        path = Path("/test")
        
        file_error = FileStorageError("write", path)
        perm_error = VortexPermissionError(path)
        disk_error = DiskSpaceError(path)
        
        error_codes = {
            file_error.error_code,
            perm_error.error_code, 
            disk_error.error_code
        }
        
        # All error codes should be different
        assert len(error_codes) == 3
    
    def test_help_text_contains_path_info(self):
        """Test that help text contains relevant path information."""
        path = Path("/important/data")
        
        file_error = FileStorageError("backup", path)
        perm_error = VortexPermissionError(path, "access")
        disk_error = DiskSpaceError(path, "5GB")
        
        # All help texts should mention the path or parent directory
        assert "/important" in file_error.help_text
        assert "/important/data" in perm_error.help_text
        assert "/important/data" in disk_error.help_text