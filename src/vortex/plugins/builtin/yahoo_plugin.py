"""
Yahoo Finance provider plugin.

Built-in plugin for Yahoo Finance data provider.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Type

from pydantic import BaseModel, Field

from ..base import BuiltinProviderPlugin, PluginMetadata, ProviderConfigSchema
from ..exceptions import PluginConfigurationError
from ...data_providers.data_provider import DataProvider
from ...data_providers.yf_data_provider import YahooDataProvider
from ...instruments.stock import Stock
from ...instruments.period import Period
from ...logging_integration import get_module_logger

logger = get_module_logger()


class YahooConfigSchema(ProviderConfigSchema):
    """Configuration schema for Yahoo Finance provider."""
    
    # Yahoo Finance doesn't require authentication
    # Base configuration is sufficient
    pass


class YahooFinancePlugin(BuiltinProviderPlugin):
    """Yahoo Finance data provider plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="yahoo",
            display_name="Yahoo Finance",
            version="1.0.0",
            description="Free stock market data from Yahoo Finance. Supports stocks, ETFs, indices, and forex.",
            author="Vortex Team",
            homepage="https://finance.yahoo.com",
            requires_auth=False,
            supported_assets=["stocks", "etfs", "indices", "forex"],
            rate_limits="Unlimited (with reasonable usage)",
            api_documentation="https://python-yfinance.readthedocs.io/"
        )
    
    @property
    def config_schema(self) -> Type[BaseModel]:
        return YahooConfigSchema
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate Yahoo Finance configuration.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Validated configuration dictionary
        """
        try:
            # Use Pydantic to validate and normalize
            validated = YahooConfigSchema(**config)
            return validated.dict()
            
        except Exception as e:
            raise PluginConfigurationError("yahoo", f"Configuration validation failed: {e}")
    
    def create_provider(self, config: Dict[str, Any]) -> DataProvider:
        """
        Create Yahoo Finance data provider instance.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            YahooDataProvider instance
        """
        try:
            logger.info("Creating Yahoo Finance provider instance")
            return YahooDataProvider()
            
        except Exception as e:
            logger.error(f"Failed to create Yahoo Finance provider: {e}")
            raise PluginConfigurationError("yahoo", f"Provider creation failed: {e}")
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """
        Test Yahoo Finance connection.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Test by fetching a simple quote
            provider = self.create_provider(config)
            
            # Try to fetch data for a well-known symbol (test connectivity)
            test_instrument = Stock(id="AAPL", symbol="AAPL")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=5)
            
            result = provider.fetch_historical_data(
                test_instrument, 
                Period.Daily, 
                start_date, 
                end_date
            )
            
            # Consider successful if we get any data
            success = result is not None and len(result) > 0
            
            if success:
                logger.info("Yahoo Finance connection test successful")
            else:
                logger.warning("Yahoo Finance connection test failed - no data returned")
            
            return success
            
        except Exception as e:
            logger.error(f"Yahoo Finance connection test failed: {e}")
            return False
    
    def get_available_symbols(self, config: Dict[str, Any]) -> List[str]:
        """
        Get popular symbols available from Yahoo Finance.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            List of popular symbols
        """
        # Return a curated list of popular symbols
        return [
            # Major US stocks
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "NFLX",
            "BRKB", "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL",
            
            # Major ETFs
            "SPY", "QQQ", "IWM", "VTI", "VOO", "VEA", "VWO", "AGG", "BND",
            
            # Major indices
            "^GSPC", "^IXIC", "^DJI", "^RUT", "^VIX",
            
            # Popular forex pairs (if supported)
            "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", "USDCAD=X"
        ]
    
    def get_provider_info(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get Yahoo Finance provider runtime information.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            Dictionary with provider status information
        """
        base_info = super().get_provider_info(config)
        
        # Add Yahoo-specific information
        base_info.update({
            "authentication_required": False,
            "supported_timeframes": ["1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"],
            "data_delay": "Real-time for most symbols",
            "historical_data_range": "Up to several decades for major symbols",
            "api_limits": "Rate limited but generally permissive"
        })
        
        return base_info