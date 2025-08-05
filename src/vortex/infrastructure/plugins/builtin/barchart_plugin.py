"""
Barchart.com provider plugin.

Built-in plugin for Barchart.com data provider.
"""

from typing import Dict, Any, List, Type

from pydantic import BaseModel, Field, validator

from ..base import BuiltinProviderPlugin, PluginMetadata, ProviderConfigSchema
from vortex.shared.exceptions import PluginConfigurationError
from vortex.infrastructure.providers.data_providers.data_provider import DataProvider
from vortex.infrastructure.providers.data_providers.bc_data_provider import BarchartDataProvider
from vortex.logging_integration import get_module_logger

logger = get_module_logger()


class BarchartConfigSchema(ProviderConfigSchema):
    """Configuration schema for Barchart provider."""
    
    username: str = Field(..., description="Barchart.com username")
    password: str = Field(..., description="Barchart.com password", writeonly=True)
    daily_limit: int = Field(
        default=150, 
        ge=1, 
        le=1000,
        description="Daily download limit (self-imposed)"
    )
    
    @validator('username')
    def validate_username(cls, v):
        if not v or not v.strip():
            raise ValueError("Username is required")
        return v.strip()
    
    @validator('password')
    def validate_password(cls, v):
        if not v or not v.strip():
            raise ValueError("Password is required")
        return v
    
    @validator('daily_limit')
    def validate_daily_limit(cls, v):
        if v < 1:
            raise ValueError("Daily limit must be at least 1")
        if v > 1000:
            raise ValueError("Daily limit should not exceed 1000 (recommended: 150)")
        return v


class BarchartPlugin(BuiltinProviderPlugin):
    """Barchart.com data provider plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="barchart",
            display_name="Barchart.com",
            version="1.0.0",
            description="Professional market data from Barchart.com. Premium futures, stocks, and options data.",
            author="Vortex Team",
            homepage="https://www.barchart.com",
            requires_auth=True,
            supported_assets=["futures", "stocks", "options", "forex"],
            rate_limits="150 downloads/day (configurable)",
            api_documentation="https://www.barchart.com/ondemand"
        )
    
    @property
    def config_schema(self) -> Type[BaseModel]:
        return BarchartConfigSchema
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate Barchart configuration.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Validated configuration dictionary
        """
        try:
            # Use Pydantic to validate and normalize
            validated = BarchartConfigSchema(**config)
            return validated.dict()
            
        except Exception as e:
            raise PluginConfigurationError("barchart", f"Configuration validation failed: {e}")
    
    def create_provider(self, config: Dict[str, Any]) -> DataProvider:
        """
        Create Barchart data provider instance.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            BarchartDataProvider instance
        """
        try:
            logger.info("Creating Barchart provider instance")
            
            return BarchartDataProvider(
                username=config["username"],
                password=config["password"],
                daily_download_limit=config.get("daily_limit", 150)
            )
            
        except Exception as e:
            logger.error(f"Failed to create Barchart provider: {e}")
            raise PluginConfigurationError("barchart", f"Provider creation failed: {e}")
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """
        Test Barchart connection and authentication.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Create provider with minimal daily limit for testing
            test_config = config.copy()
            test_config["daily_limit"] = 1
            
            provider = BarchartDataProvider(
                username=config["username"],
                password=config["password"],
                daily_download_limit=1
            )
            
            # Test authentication by checking if we can access the download page
            # This is done during provider initialization (login)
            
            logger.info("Barchart connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Barchart connection test failed: {e}")
            return False
    
    def get_available_symbols(self, config: Dict[str, Any]) -> List[str]:
        """
        Get popular symbols available from Barchart.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            List of popular futures and stock symbols
        """
        # Return a curated list of popular Barchart symbols
        return [
            # Popular futures contracts
            "ES", "NQ", "YM", "RTY",  # Equity indices
            "GC", "SI", "HG", "PL",   # Metals
            "CL", "NG", "RB", "HO",   # Energy
            "ZC", "ZS", "ZW", "ZM",   # Agriculture
            "6E", "6B", "6J", "6A",   # Currencies
            
            # Popular stocks
            "AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "NFLX",
            
            # Popular forex pairs
            "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"
        ]
    
    def get_provider_info(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get Barchart provider runtime information.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            Dictionary with provider status information
        """
        base_info = super().get_provider_info(config)
        
        # Add Barchart-specific information
        base_info.update({
            "authentication_required": True,
            "username": config.get("username", "Not configured"),
            "daily_limit": config.get("daily_limit", 150),
            "supported_timeframes": ["1d", "1wk", "1mo", "intraday"],
            "data_quality": "Premium institutional-grade data",
            "specialties": ["Futures contracts", "Options chains", "Real-time data"],
            "api_limits": f"{config.get('daily_limit', 150)} downloads per day"
        })
        
        return base_info
    
    def get_help_text(self) -> str:
        """Get help text for configuring Barchart provider."""
        return """# Barchart.com Configuration
# Professional market data provider with premium futures, stocks, and options data

Authentication required. You need a Barchart.com account to use this provider.

Setup Instructions:
1. Create an account at https://www.barchart.com
2. Subscribe to a data plan that includes historical data access
3. Configure credentials:
   vortex config --provider barchart --set-credentials

Configuration Options:
  username (required) - Your Barchart.com username
  password (required) - Your Barchart.com password  
  daily_limit (default: 150) - Self-imposed daily download limit
  timeout (default: 30) - Request timeout in seconds
  max_retries (default: 3) - Maximum number of retries

Rate Limits: 
  - Barchart allows unlimited downloads for premium subscribers
  - daily_limit setting provides self-imposed throttling (recommended: 150)
  - Exceeding limits may result in account restrictions

Data Quality:
  - Premium institutional-grade market data
  - Extensive futures contract coverage
  - Real-time and historical data
  - Options chains and derivatives

API Documentation: https://www.barchart.com/ondemand"""