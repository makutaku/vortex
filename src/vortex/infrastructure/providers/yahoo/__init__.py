"""
Yahoo Finance data provider components.

This package contains the Yahoo Finance data provider implementation.
"""

from vortex.models.column_registry import register_provider_column_mapping

from .column_mapping import YahooColumnMapping
from .provider import YahooDataProvider

# Auto-register column mapping when module is imported
register_provider_column_mapping(YahooColumnMapping())

__all__ = ["YahooDataProvider"]
