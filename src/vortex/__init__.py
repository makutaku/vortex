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

__version__ = "0.1.3"

# Public API exports for backward compatibility
# These imports are optional to allow CLI usage without full dependencies
def _import_with_fallback(module_path, name, fallback=None):
    """Import with fallback to avoid dependency issues."""
    try:
        module = __import__(module_path, fromlist=[name])
        return getattr(module, name)
    except ImportError:
        return fallback

# Core imports with fallbacks
Instrument = _import_with_fallback('vortex.models', 'Instrument')
Future = _import_with_fallback('vortex.models', 'Future')
Stock = _import_with_fallback('vortex.models', 'Stock')
Forex = _import_with_fallback('vortex.models', 'Forex')
PriceSeries = _import_with_fallback('vortex.models', 'PriceSeries')

UpdatingDownloader = _import_with_fallback('vortex.services', 'UpdatingDownloader')
BackfillDownloader = _import_with_fallback('vortex.services', 'BackfillDownloader')
DownloadJob = _import_with_fallback('vortex.services', 'DownloadJob')

DataProvider = _import_with_fallback('vortex.providers', 'DataProvider')
DataStorage = _import_with_fallback('vortex.storage', 'DataStorage')

VortexError = _import_with_fallback('vortex.shared.exceptions', 'VortexError')
VortexConfig = _import_with_fallback('vortex.config', 'VortexConfig')

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