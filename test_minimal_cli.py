#!/usr/bin/env python3
"""Minimal CLI test to verify core structure works."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_minimal_structure():
    """Test minimal CLI structure."""
    print("🧪 Testing Vortex CLI Core Structure")
    print("=" * 50)
    
    # Test 1: CLI module and version
    try:
        from vortex.cli import __version__
        print(f"✅ CLI Module: version {__version__}")
    except Exception as e:
        print(f"❌ CLI Module: {e}")
        return False
    
    # Test 2: Instrument parser (no deps)
    try:
        from vortex.cli.utils.instrument_parser import parse_instruments, validate_symbol
        
        # Test parsing
        symbols = parse_instruments(("AAPL", "googl", " MSFT "), None)
        expected = ["AAPL", "GOOGL", "MSFT"]
        assert symbols == expected, f"Expected {expected}, got {symbols}"
        
        # Test validation
        assert validate_symbol("AAPL") == True
        assert validate_symbol("") == False
        assert validate_symbol("123!@#") == False
        
        print("✅ Instrument Parser: working correctly")
    except Exception as e:
        print(f"❌ Instrument Parser: {e}")
        return False
    
    # Test 3: Basic CLI command structure exists
    try:
        # Import without running
        import vortex.cli.main
        print("✅ CLI Main: structure exists")
    except Exception as e:
        print(f"❌ CLI Main: {e}")
        return False
    
    # Test 4: Command modules exist
    commands_to_test = ['download', 'config', 'providers', 'validate']
    for cmd in commands_to_test:
        try:
            __import__(f'vortex.cli.commands.{cmd}')
            print(f"✅ Command {cmd}: structure exists")
        except Exception as e:
            print(f"❌ Command {cmd}: {e}")
            return False
    
    print("\\n" + "=" * 50)
    print("🎉 CORE STRUCTURE TEST: PASSED")
    print("\\nNext Steps:")
    print("1. Install dependencies:")
    print("   pip install click rich tomli tomli-w")
    print("2. Install vortex in development mode:")
    print("   pip install -e .")
    print("3. Test the full CLI:")
    print("   vortex --help")
    print("   vortex download --help")
    print("   vortex config --show")
    
    return True

if __name__ == "__main__":
    success = test_minimal_structure()
    if success:
        print("\\n✨ Ready to install dependencies and test full CLI!")
    sys.exit(0 if success else 1)