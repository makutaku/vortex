"""
Interactive Brokers data provider components.

This package contains the IBKR TWS/Gateway data provider implementation.
"""

from .provider import IbkrDataProvider
from .column_mapping import IbkrColumnMapping
from vortex.models.column_registry import register_provider_column_mapping

# Auto-register column mapping when module is imported
register_provider_column_mapping(IbkrColumnMapping())

__all__ = ['IbkrDataProvider']