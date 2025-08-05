"""
Interactive Brokers (IBKR) provider plugin.

Built-in plugin for Interactive Brokers data provider via TWS/Gateway.
"""

from typing import Dict, Any, List, Type

from pydantic import BaseModel, Field, validator

from ..base import BuiltinProviderPlugin, PluginMetadata, ProviderConfigSchema
from vortex.shared.exceptions import PluginConfigurationError
from vortex.infrastructure.providers.data_providers.data_provider import DataProvider
from vortex.infrastructure.providers.data_providers.ib_data_provider import IbkrDataProvider
from vortex.logging_integration import get_module_logger

logger = get_module_logger()


class IbkrConfigSchema(ProviderConfigSchema):
    """Configuration schema for IBKR provider."""
    
    host: str = Field(
        default="localhost", 
        description="TWS/Gateway host address"
    )
    port: int = Field(
        default=7497, 
        ge=1000, 
        le=65535,
        description="TWS/Gateway port (7497 for TWS, 4001 for Gateway)"
    )
    client_id: int = Field(
        default=1, 
        ge=0, 
        le=999,
        description="Client ID for connection (0-999)"
    )
    connect_timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Connection timeout in seconds"
    )
    
    @validator('host')
    def validate_host(cls, v):
        if not v or not v.strip():
            raise ValueError("Host is required")
        return v.strip()
    
    @validator('port')
    def validate_port(cls, v):
        if v < 1000 or v > 65535:
            raise ValueError("Port must be between 1000 and 65535")
        # Common TWS/Gateway ports
        if v not in [7497, 7496, 4001, 4002]:
            logger.warning(f"Port {v} is not a standard TWS/Gateway port. "
                         "Common ports: 7497 (TWS), 4001 (Gateway)")
        return v
    
    @validator('client_id')
    def validate_client_id(cls, v):
        if v < 0 or v > 999:
            raise ValueError("Client ID must be between 0 and 999")
        return v


class IbkrPlugin(BuiltinProviderPlugin):
    """Interactive Brokers data provider plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="ibkr",
            display_name="Interactive Brokers",
            version="1.0.0",
            description="Professional trading platform with comprehensive market data. Requires TWS or Gateway.",
            author="Vortex Team",
            homepage="https://www.interactivebrokers.com",
            requires_auth=True,
            supported_assets=["stocks", "futures", "options", "forex", "bonds", "funds"],
            rate_limits="Real-time connection limits apply",
            api_documentation="https://interactivebrokers.github.io/tws-api/"
        )
    
    @property
    def config_schema(self) -> Type[BaseModel]:
        return IbkrConfigSchema
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate IBKR configuration.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Validated configuration dictionary
        """
        try:
            # Use Pydantic to validate and normalize
            validated = IbkrConfigSchema(**config)
            return validated.dict()
            
        except Exception as e:
            raise PluginConfigurationError("ibkr", f"Configuration validation failed: {e}")
    
    def create_provider(self, config: Dict[str, Any]) -> DataProvider:
        """
        Create IBKR data provider instance.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            IbkrDataProvider instance
        """
        try:
            logger.info("Creating IBKR provider instance")
            
            return IbkrDataProvider(
                ipaddress=config["host"],
                port=str(config["port"]),
                client_id=config.get("client_id", 1)
            )
            
        except Exception as e:
            logger.error(f"Failed to create IBKR provider: {e}")
            raise PluginConfigurationError("ibkr", f"Provider creation failed: {e}")
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """
        Test IBKR connection to TWS/Gateway.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create provider and test connection
            provider = IbkrDataProvider(
                ipaddress=config["host"],
                port=str(config["port"]),
                client_id=config.get("client_id", 1)
            )
            
            # Test by trying to establish connection
            # The IbkrDataProvider will attempt connection during initialization
            
            logger.info("IBKR connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"IBKR connection test failed: {e}")
            return False
    
    def get_available_symbols(self, config: Dict[str, Any]) -> List[str]:
        """
        Get popular symbols available from IBKR.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            List of popular symbols across all asset classes
        """
        # Return a curated list of popular IBKR symbols
        return [
            # Major US stocks
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "NFLX",
            "BRKB", "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL",
            
            # Major ETFs
            "SPY", "QQQ", "IWM", "VTI", "VOO", "VEA", "VWO", "AGG", "BND",
            
            # Futures (ES, NQ, etc. with proper IBKR symbols)
            "ES", "NQ", "YM", "RTY",  # E-mini futures
            "GC", "SI", "CL", "NG",   # Commodities
            
            # Forex pairs
            "EUR.USD", "GBP.USD", "USD.JPY", "USD.CHF", "AUD.USD", "USD.CAD",
            
            # International stocks
            "ASML", "NESN", "TSMC", "BHP", "RIO"
        ]
    
    def get_provider_info(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get IBKR provider runtime information.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            Dictionary with provider status information
        """
        base_info = super().get_provider_info(config)
        
        # Add IBKR-specific information
        base_info.update({
            "authentication_required": True,
            "connection_type": "TWS/Gateway API",
            "host": config.get("host", "localhost"),
            "port": config.get("port", 7497),
            "client_id": config.get("client_id", 1),
            "supported_timeframes": ["1 sec", "5 secs", "10 secs", "15 secs", "30 secs", 
                                   "1 min", "2 mins", "3 mins", "5 mins", "10 mins", "15 mins", "20 mins", "30 mins",
                                   "1 hour", "2 hours", "3 hours", "4 hours", "8 hours", "1 day", "1 week", "1 month"],
            "data_quality": "Professional institutional-grade real-time data",
            "global_coverage": "200+ markets worldwide",
            "asset_classes": ["Stocks", "Options", "Futures", "Forex", "Bonds", "Funds", "Warrants", "Commodities"],
            "api_limits": "Real-time connection and market data subscription limits apply"
        })
        
        return base_info
    
    def get_help_text(self) -> str:
        """Get help text for configuring IBKR provider."""
        return """# Interactive Brokers (IBKR) Configuration
# Professional trading platform with comprehensive global market data

Requirements:
1. Interactive Brokers account with market data subscriptions
2. TWS (Trader Workstation) or IB Gateway running
3. API connections enabled in TWS/Gateway settings

Setup Instructions:
1. Install and run TWS or IB Gateway
2. Enable API connections in TWS/Gateway:
   - In TWS: File -> Global Configuration -> API -> Settings
   - Check "Enable ActiveX and Socket Clients"
   - Add your client ID to trusted clients
3. Configure connection:
   vortex config --provider ibkr --set-credentials

Configuration Options:
  host (default: localhost) - TWS/Gateway host address
  port (default: 7497) - TWS/Gateway port
    - 7497: TWS (paper trading)
    - 7496: TWS (live trading) 
    - 4001: IB Gateway (paper trading)
    - 4002: IB Gateway (live trading)
  client_id (default: 1) - Unique client identifier (0-999)
  connect_timeout (default: 10) - Connection timeout in seconds
  timeout (default: 30) - Request timeout in seconds
  max_retries (default: 3) - Maximum number of retries

Connection Types:
  - TWS (Trader Workstation): Full trading platform with GUI
  - IB Gateway: Headless API server for automated trading

Data Access:
  - Real-time market data (subscription required)
  - Historical data (included with account)
  - Global market coverage (200+ markets)
  - All asset classes supported

Market Data Subscriptions:
  - US Securities Snapshot and Futures Value Bundle: Most US data
  - European Market Data: European exchanges
  - Asian Market Data: Asian exchanges
  - Forex: Currency pairs (often included)

Troubleshooting:
  - Ensure TWS/Gateway is running and API is enabled
  - Check firewall settings allow connections on specified port
  - Verify client_id is not already in use
  - Check market data subscriptions for required symbols

API Documentation: https://interactivebrokers.github.io/tws-api/"""