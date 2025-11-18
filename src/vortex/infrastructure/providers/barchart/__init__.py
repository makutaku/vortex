"""
Barchart data provider components.

This package contains modular components for the Barchart data provider:
- auth: Authentication and session management
- client: HTTP client and request handling
- parser: Data parsing and conversion utilities
- provider: Main BarchartDataProvider class
"""

from vortex.models.column_registry import register_provider_column_mapping

from .column_mapping import BarchartColumnMapping
from .provider import BarchartDataProvider

# Auto-register column mapping when module is imported
register_provider_column_mapping(BarchartColumnMapping())

__all__ = ["BarchartDataProvider"]
