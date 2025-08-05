"""
Vortex: Financial Data Download Automation Tool

A Python library for downloading historic futures contract prices from multiple data providers
including Barchart.com, Yahoo Finance, and Interactive Brokers.

Architecture Overview:
- Core: Domain models, business services, and application logic
- Infrastructure: External data providers, storage, and third-party integrations  
- Application: User interfaces (CLI) and workflow orchestration
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
Instrument = _import_with_fallback('vortex.core.models.instruments', 'Instrument')
Future = _import_with_fallback('vortex.core.models.instruments', 'Future')
Stock = _import_with_fallback('vortex.core.models.instruments', 'Stock')
Forex = _import_with_fallback('vortex.core.models.instruments', 'Forex')
PriceSeries = _import_with_fallback('vortex.core.models.instruments', 'PriceSeries')

UpdatingDownloader = _import_with_fallback('vortex.core.services.downloaders', 'UpdatingDownloader')
BackfillDownloader = _import_with_fallback('vortex.core.services.downloaders', 'BackfillDownloader')
DownloadJob = _import_with_fallback('vortex.core.services.downloaders', 'DownloadJob')

DataProvider = _import_with_fallback('vortex.infrastructure.providers.data_providers', 'DataProvider')
DataStorage = _import_with_fallback('vortex.infrastructure.storage.data_storage', 'DataStorage')

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