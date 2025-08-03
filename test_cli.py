#!/usr/bin/env python3
"""Simple CLI test without external dependencies."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_cli_structure():
    """Test that CLI structure is correct."""
    try:
        from bcutils.cli import __version__
        print(f"✓ CLI module imported successfully (version {__version__})")
        
        # Test import of main components (without running them)
        from bcutils.cli.main import cli
        print("✓ Main CLI entry point imported")
        
        from bcutils.cli.commands import download, config, providers, validate
        print("✓ All command modules imported")
        
        from bcutils.cli.utils.config_manager import ConfigManager
        print("✓ Config manager imported")
        
        from bcutils.cli.utils.instrument_parser import parse_instruments
        print("✓ Instrument parser imported")
        
        print("\n🎉 CLI structure test passed!")
        print("\nNext steps to complete setup:")
        print("1. Install dependencies: pip install click rich tomli tomli-w")
        print("2. Install in development mode: pip install -e .")
        print("3. Test: bcutils --help")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_cli_structure()
    sys.exit(0 if success else 1)