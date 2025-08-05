"""
Instrument configuration and management.

This module provides utilities for configuring and managing financial instruments
including futures, stocks, and forex pairs.
"""

from .config import InstrumentConfig, InstrumentType, DEFAULT_CONTRACT_DURATION_IN_DAYS

__all__ = [
    'InstrumentConfig',
    'InstrumentType', 
    'DEFAULT_CONTRACT_DURATION_IN_DAYS',
]