"""Simple test command without external dependencies."""

import click

@click.command()
def simple_test():
    """Test command to verify CLI structure."""
    print("✓ CLI is working correctly!")
    print("Install full dependencies to use all features:")
    print("  pip install click rich tomli tomli-w")