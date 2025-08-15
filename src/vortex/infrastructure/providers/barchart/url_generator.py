"""
Barchart URL generation strategies.

Extracted from BarchartProvider to implement single responsibility principle.
Handles URL generation for different instrument types.
"""

from functools import singledispatchmethod

from vortex.models.forex import Forex
from vortex.models.future import Future
from vortex.models.stock import Stock
from vortex.core.constants import ProviderConstants


class BarchartURLGenerator:
    """Handles URL generation for different instrument types."""
    
    @singledispatchmethod
    def get_historical_quote_url(self, instrument) -> str:
        """Get historical quote URL for an instrument (generic fallback)."""
        # Fallback for unknown types
        return f"{ProviderConstants.Barchart.BASE_URL}/quotes/{str(instrument)}/historical-quotes"
    
    @get_historical_quote_url.register
    def _(self, future: Future) -> str:
        """Get historical quote URL for futures."""
        return f"{ProviderConstants.Barchart.BASE_URL}/futures/quotes/{future.id}/historical-quotes"
    
    @get_historical_quote_url.register  
    def _(self, stock: Stock) -> str:
        """Get historical quote URL for stocks."""
        return f"{ProviderConstants.Barchart.BASE_URL}/stocks/quotes/{stock.id}/historical-quotes"
    
    @get_historical_quote_url.register
    def _(self, forex: Forex) -> str:
        """Get historical quote URL for forex."""
        return f"{ProviderConstants.Barchart.BASE_URL}/forex/quotes/{forex.id}/historical-quotes"