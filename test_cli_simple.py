#!/usr/bin/env python3
"""Simple CLI test focusing on core structure."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_basic_cli():
    """Test basic CLI functionality."""
    print("Testing vortex CLI structure...")
    
    # Test 1: Import CLI module
    try:
        from bcutils.cli import __version__
        print(f"✓ CLI module version: {__version__}")
    except Exception as e:
        print(f"✗ Failed to import CLI module: {e}")
        return False
    
    # Test 2: Import config manager (no external deps)
    try:
        from bcutils.cli.utils.config_manager import ConfigManager
        config_manager = ConfigManager()
        print("✓ Config manager working")
    except Exception as e:
        print(f"✗ Config manager failed: {e}")
        return False
    
    # Test 3: Import instrument parser (no external deps)
    try:
        from bcutils.cli.utils.instrument_parser import parse_instruments
        symbols = parse_instruments(("AAPL", "GOOGL"), None)
        assert symbols == ["AAPL", "GOOGL"]
        print("✓ Instrument parser working")
    except Exception as e:
        print(f"✗ Instrument parser failed: {e}")
        return False
    
    # Test 4: Test CLI entry point exists
    try:
        # Just check if we can import it, don't run it
        from bcutils.cli.main import main
        print("✓ Main CLI entry point exists")
    except Exception as e:
        print(f"✗ Main CLI entry point failed: {e}")
        return False
    
    print("\n🎉 Basic CLI structure tests passed!")
    print("\nTo complete setup:")
    print("1. Install dependencies:")
    print("   pip install click rich tomli tomli-w")
    print("2. Install vortex:")
    print("   pip install -e .")
    print("3. Test full CLI:")
    print("   vortex --help")
    
    return True

if __name__ == "__main__":
    success = test_basic_cli()
    sys.exit(0 if success else 1)