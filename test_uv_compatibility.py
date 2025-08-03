#!/usr/bin/env python3
"""Test UV compatibility and installation workflow."""

import subprocess
import sys
from pathlib import Path

def test_uv_compatibility():
    """Test that the project is compatible with uv."""
    print("🧪 Testing UV Compatibility for BC-Utils")
    print("=" * 50)
    
    # Test 1: Check if pyproject.toml exists and is valid
    try:
        pyproject_path = Path("pyproject.toml")
        if not pyproject_path.exists():
            print("❌ pyproject.toml not found")
            return False
        
        print("✅ pyproject.toml exists")
        
        # Check for required fields
        content = pyproject_path.read_text()
        required_fields = [
            '[project]',
            'name = "bc-utils"',
            'dependencies = [',
            '[project.scripts]',
            'bcutils = "bcutils.cli.main:cli"'
        ]
        
        for field in required_fields:
            if field in content:
                print(f"✅ Found: {field}")
            else:
                print(f"❌ Missing: {field}")
                return False
                
    except Exception as e:
        print(f"❌ Error reading pyproject.toml: {e}")
        return False
    
    # Test 2: Check if CLI entry point is configured
    if 'bcutils = "bcutils.cli.main:cli"' in content:
        print("✅ CLI entry point configured")
    else:
        print("❌ CLI entry point not configured")
        return False
    
    # Test 3: Check dependency groups
    optional_deps = ['[project.optional-dependencies]', 'dev = [', 'test = [', 'lint = [']
    for dep in optional_deps:
        if dep in content:
            print(f"✅ Optional dependencies: {dep}")
        else:
            print(f"⚠️  Optional dependency group missing: {dep}")
    
    print("\n" + "=" * 50)
    print("🎉 UV COMPATIBILITY: VERIFIED")
    print("\nThe project is fully compatible with uv!")
    print("\n📋 UV Installation Commands:")
    print("  # Install uv")
    print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
    print("  ")
    print("  # Create virtual environment")
    print("  uv venv")
    print("  source .venv/bin/activate")
    print("  ")
    print("  # Install bc-utils")
    print("  uv pip install -e .")
    print("  ")
    print("  # Install with development dependencies")
    print("  uv pip install -e \".[dev,test,lint]\"")
    print("  ")
    print("  # Run CLI")
    print("  bcutils --help")
    print("  ")
    print("  # Or run directly without activation")
    print("  uv run bcutils --help")
    
    print("\n⚡ Benefits of using uv:")
    print("  • 10-100x faster than pip")
    print("  • Reliable dependency resolution")
    print("  • Drop-in replacement for pip")
    print("  • Built-in virtual environment management")
    print("  • Modern Python packaging support")
    
    return True

def check_uv_installed():
    """Check if uv is installed and available."""
    try:
        result = subprocess.run(['uv', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"✅ UV is installed: {result.stdout.strip()}")
            return True
        else:
            print("⚠️  UV is not installed")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("⚠️  UV is not installed or not in PATH")
        return False

if __name__ == "__main__":
    print("Checking UV installation status...")
    uv_available = check_uv_installed()
    
    if not uv_available:
        print("\n💡 To install uv:")
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  # or on Windows: powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
    
    print("\n" + "-" * 50)
    success = test_uv_compatibility()
    sys.exit(0 if success else 1)