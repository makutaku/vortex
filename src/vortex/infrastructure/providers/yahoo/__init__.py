"""
Yahoo Finance data provider components.

This package contains the Yahoo Finance data provider implementation.
"""

from .provider import YahooDataProvider
from .column_mapping import YahooColumnMapping
from vortex.models.column_registry import register_provider_column_mapping

# Auto-register column mapping when module is imported
register_provider_column_mapping(YahooColumnMapping())

__all__ = ['YahooDataProvider']