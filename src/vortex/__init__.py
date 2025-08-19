"""
Vortex: Financial Data Download Automation Tool

A Python library for downloading historic futures contract prices from multiple data providers
including Barchart.com, Yahoo Finance, and Interactive Brokers.

Architecture Overview:
- Models: Domain models for financial instruments and data structures
- Services: Business services for downloading and processing data
- Providers: External data provider integrations (Barchart, Yahoo, IBKR)
- Storage: Data persistence and retrieval implementations
- CLI: Command-line interface and user interaction
- Shared: Cross-cutting concerns like logging, exceptions, and resilience
"""

__version__ = "0.1.4"

# Public API exports
try:
    # Core domain models
    from .models import Instrument, Future, Stock, Forex, PriceSeries
    
    # Services 
    from .services import UpdatingDownloader, BackfillDownloader, DownloadJob
    
    # Infrastructure interfaces
    from .infrastructure.providers.base import DataProvider
    from .infrastructure.storage.data_storage import DataStorage
    
    # Configuration and exceptions
    from .exceptions import VortexError
    from .core.config import VortexConfig
except ImportError:
    # Gracefully handle missing dependencies for CLI-only usage
    pass

__all__ = [
    "Instrument",
    "Future", 
    "Stock",
    "Forex",
    "PriceSeries",
    "UpdatingDownloader",
    "BackfillDownloader", 
    "DownloadJob",
    "DataProvider",
    "DataStorage",
    "VortexError",
    "VortexConfig",
]