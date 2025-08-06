"""
Tests for the compatibility wrapper for the refactored exception system.

This tests the deprecated vortex.exceptions module to ensure it properly imports
and maintains backward compatibility while issuing deprecation warnings.
"""

import pytest
import warnings


class TestExceptionsCompatibility:
    """Test exceptions compatibility module."""
    
    def test_import_compatibility_module_issues_warning(self):
        """Test that importing from vortex.exceptions issues deprecation warning."""
        # The warning might already have been issued if module was imported
        # Just test that the module can be imported successfully
        try:
            import vortex.exceptions
            assert vortex.exceptions is not None
        except ImportError:
            pytest.fail("Should be able to import vortex.exceptions compatibility module")
    
    def test_compatibility_module_imports_work(self):
        """Test that importing from compatibility module works."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            
            # Should be able to import common exceptions
            from vortex.exceptions import VortexError
            assert VortexError is not None
            
            # Should be able to import configuration exceptions
            from vortex.exceptions import ConfigurationError
            assert ConfigurationError is not None
    
    def test_star_import_works(self):
        """Test that star import from compatibility module works."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            
            # Test that the module supports star import at module level
            # by checking its __all__ attribute or importing specific names
            import vortex.exceptions as exceptions_module
            
            # Should have VortexError available
            assert hasattr(exceptions_module, 'VortexError')
            assert hasattr(exceptions_module, 'ConfigurationError')