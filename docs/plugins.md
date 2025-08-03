# Vortex Plugin System

The Vortex plugin system provides a modular, extensible architecture for data providers. This allows easy integration of new data sources and third-party providers without modifying core Vortex code.

## Architecture Overview

The plugin system consists of several key components:

- **ProviderPlugin**: Abstract base class that all plugins must implement
- **ProviderRegistry**: Central registry for discovering and managing plugins  
- **PluginMetadata**: Descriptive information about each plugin
- **Configuration Schemas**: Pydantic models for validating plugin configurations

## Built-in Providers

Vortex ships with three built-in provider plugins:

### Yahoo Finance (`yahoo`)
- **Authentication**: None required
- **Data Types**: Stocks, ETFs, indices, forex
- **Rate Limits**: Unlimited (with reasonable usage)
- **Specialties**: Free market data, wide symbol coverage

### Barchart.com (`barchart`)  
- **Authentication**: Username/password required
- **Data Types**: Futures, stocks, options, forex
- **Rate Limits**: 150 downloads/day (configurable)
- **Specialties**: Premium futures data, institutional-grade quality

### Interactive Brokers (`ibkr`)
- **Authentication**: TWS/Gateway connection required  
- **Data Types**: All asset classes (stocks, futures, options, forex, bonds, funds)
- **Rate Limits**: Real-time connection limits
- **Specialties**: Global markets, professional trading platform

## Using Plugins

### List Available Providers

```bash
# List all available providers
vortex providers --list

# Get detailed information about a provider
vortex providers --info yahoo
```

### Configure Providers

```bash
# Configure Barchart credentials
vortex config --provider barchart --set-credentials

# Configure IBKR connection
vortex config --provider ibkr --set-credentials
```

### Test Provider Connections

```bash
# Test a specific provider
vortex providers --test yahoo

# Test all providers
vortex providers --test all
```

### Download Data

```bash
# Download using specific provider
vortex download --provider yahoo --symbol AAPL
vortex download --provider barchart --symbol GC
vortex download --provider ibkr --symbol TSLA
```

## Developing Custom Plugins

### Plugin Structure

Create a new plugin by inheriting from `ProviderPlugin`:

```python
from typing import Dict, Any, Type
from pydantic import BaseModel, Field

from vortex.plugins.base import ProviderPlugin, PluginMetadata
from vortex.data_providers.data_provider import DataProvider

class MyProviderConfigSchema(BaseModel):
    """Configuration schema for your provider."""
    api_key: str = Field(..., description="API key for authentication")
    base_url: str = Field(default="https://api.example.com", description="API base URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")

class MyCustomProvider(DataProvider):
    """Your custom data provider implementation."""
    
    def __init__(self, api_key: str, base_url: str, timeout: int = 30):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
    
    def get_name(self) -> str:
        return "MyCustomProvider"
    
    # Implement other required DataProvider methods...

class MyProviderPlugin(ProviderPlugin):
    """Plugin for My Custom Provider."""
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="mycustom",
            display_name="My Custom Provider",
            version="1.0.0",
            description="Custom financial data provider",
            author="Your Name",
            homepage="https://example.com",
            requires_auth=True,
            supported_assets=["stocks", "crypto"],
            rate_limits="1000/hour",
            api_documentation="https://api.example.com/docs"
        )
    
    @property
    def config_schema(self) -> Type[BaseModel]:
        return MyProviderConfigSchema
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration using Pydantic."""
        validated = MyProviderConfigSchema(**config)
        return validated.dict()
    
    def create_provider(self, config: Dict[str, Any]) -> DataProvider:
        """Create provider instance."""
        return MyCustomProvider(
            api_key=config["api_key"],
            base_url=config["base_url"],
            timeout=config["timeout"]
        )
    
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """Test provider connection."""
        try:
            provider = self.create_provider(config)
            # Test connection logic here
            return True
        except Exception:
            return False
```

### Plugin Installation

#### Method 1: Package Installation

Create a Python package and install it:

```bash
# Create package structure
mkdir vortex-mycustom-plugin
cd vortex-mycustom-plugin

# Create setup.py
cat > setup.py << EOF
from setuptools import setup, find_packages

setup(
    name="vortex-mycustom-plugin",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["vortex"],
    entry_points={
        "vortex_plugins": [
            "mycustom = mycustom_plugin:MyProviderPlugin"
        ]
    }
)
EOF

# Install the plugin
pip install -e .
```

#### Method 2: Directory Installation

Place your plugin file in one of these directories:

- `~/.vortex/plugins/` (user plugins)
- `./vortex_plugins/` (project plugins)  
- `/opt/vortex/plugins/` (system plugins)

Example:

```bash
mkdir -p ~/.vortex/plugins
cp my_provider_plugin.py ~/.vortex/plugins/
```

### Plugin Registration

Plugins are automatically discovered and registered when Vortex starts. You can also manually register plugins:

```python
from vortex.plugins import get_provider_registry

# Get the global registry
registry = get_provider_registry()

# Register your plugin
plugin = MyProviderPlugin()
registry.register_plugin(plugin)
```

## Configuration Management

### Plugin Configuration

Each plugin defines its configuration schema using Pydantic models. This enables:

- **Type validation**: Ensure correct data types
- **Required fields**: Mark mandatory configuration options
- **Default values**: Provide sensible defaults
- **Documentation**: Self-documenting configuration options

Example configuration schema:

```python
from pydantic import BaseModel, Field, validator

class AdvancedConfigSchema(BaseModel):
    api_key: str = Field(..., description="API key for authentication")
    rate_limit: int = Field(default=100, ge=1, le=1000, description="Requests per minute")
    regions: List[str] = Field(default=["US"], description="Supported regions")
    
    @validator('api_key')
    def validate_api_key(cls, v):
        if not v.startswith('ak_'):
            raise ValueError('API key must start with ak_')
        return v
    
    @validator('regions')
    def validate_regions(cls, v):
        valid_regions = ['US', 'EU', 'ASIA']
        for region in v:
            if region not in valid_regions:
                raise ValueError(f'Invalid region: {region}')
        return v
```

### Environment Variables

Plugin configurations can be set via environment variables:

```bash
# Set configuration via environment
export VORTEX_MYCUSTOM_API_KEY="your-api-key"
export VORTEX_MYCUSTOM_RATE_LIMIT="200"

# Vortex will automatically pick up these settings
vortex download --provider mycustom --symbol BTCUSD
```

### Configuration Files

Plugin settings are stored in the main Vortex configuration file:

```toml
# ~/.config/vortex/config.toml
[providers.mycustom]
api_key = "your-api-key-here"
base_url = "https://api.example.com"
rate_limit = 150
regions = ["US", "EU"]
```

## Testing Plugins

### Unit Testing

Test your plugin components individually:

```python
import pytest
from your_plugin import MyProviderPlugin

def test_plugin_metadata():
    plugin = MyProviderPlugin()
    assert plugin.metadata.name == "mycustom"
    assert plugin.metadata.requires_auth == True

def test_config_validation():
    plugin = MyProviderPlugin()
    
    # Valid config
    config = {"api_key": "ak_test123", "rate_limit": 100}
    validated = plugin.validate_config(config)
    assert validated["api_key"] == "ak_test123"
    
    # Invalid config
    with pytest.raises(ValidationError):
        plugin.validate_config({"api_key": ""})

def test_provider_creation():
    plugin = MyProviderPlugin()
    config = {"api_key": "ak_test123"}
    
    provider = plugin.create_provider(config)
    assert provider.get_name() == "MyCustomProvider"
```

### Integration Testing

Test your plugin with the Vortex system:

```python
from vortex.plugins import get_provider_registry

def test_plugin_integration():
    registry = get_provider_registry()
    plugin = MyProviderPlugin()
    registry.register_plugin(plugin)
    
    # Test plugin is registered
    assert "mycustom" in registry.list_plugins()
    
    # Test provider creation through registry
    config = {"api_key": "ak_test123"}
    provider = registry.create_provider("mycustom", config)
    assert provider is not None
```

### CLI Testing

Test your plugin through the Vortex CLI:

```bash
# Test plugin registration
vortex providers --list | grep MYCUSTOM

# Test connection
vortex providers --test mycustom

# Test data download
vortex download --provider mycustom --symbol TEST --dry-run
```

## Best Practices

### Error Handling

Implement robust error handling in your plugin:

```python
from vortex.plugins.exceptions import PluginConfigurationError

def create_provider(self, config: Dict[str, Any]) -> DataProvider:
    try:
        return MyCustomProvider(**config)
    except Exception as e:
        raise PluginConfigurationError(
            plugin_name=self.metadata.name,
            config_error=f"Failed to create provider: {e}"
        )
```

### Logging

Use Vortex's logging system for consistent log output:

```python
from vortex.logging_integration import get_module_logger

logger = get_module_logger()

def test_connection(self, config: Dict[str, Any]) -> bool:
    try:
        provider = self.create_provider(config)
        # Test connection...
        logger.info(f"Connection test successful for {self.metadata.name}")
        return True
    except Exception as e:
        logger.error(f"Connection test failed for {self.metadata.name}: {e}")
        return False
```

### Rate Limiting

Respect provider rate limits and implement appropriate throttling:

```python
import time
from datetime import datetime, timedelta

class RateLimitedProvider(DataProvider):
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.request_times = []
    
    def _check_rate_limit(self):
        now = datetime.now()
        # Remove requests older than 1 minute
        self.request_times = [
            t for t in self.request_times 
            if now - t < timedelta(minutes=1)
        ]
        
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0]).seconds
            logger.info(f"Rate limit reached, sleeping for {sleep_time} seconds")
            time.sleep(sleep_time)
        
        self.request_times.append(now)
```

### Documentation

Provide comprehensive help text for your plugin:

```python
def get_help_text(self) -> str:
    return \"\"\"# My Custom Provider Configuration
# Custom financial data provider with advanced features

Authentication:
  API key required. Get yours at https://example.com/api-keys

Setup Instructions:
1. Sign up for an account at https://example.com
2. Generate an API key in your dashboard
3. Configure Vortex:
   vortex config --provider mycustom --set-credentials

Configuration Options:
  api_key (required) - Your API authentication key
  base_url (optional) - API base URL [default: https://api.example.com]
  rate_limit (optional) - Requests per minute [default: 100]
  regions (optional) - Supported regions [default: ["US"]]

Supported Assets:
  - Stocks (NYSE, NASDAQ)
  - Cryptocurrency pairs
  - Foreign exchange (major pairs)

Rate Limits:
  - Free tier: 100 requests/minute
  - Pro tier: 1000 requests/minute
  
API Documentation: https://api.example.com/docs\"\"\"
```

## Troubleshooting

### Plugin Not Found

If your plugin isn't being discovered:

1. Check plugin is in the correct directory
2. Verify plugin class inherits from `ProviderPlugin`
3. Ensure plugin file doesn't start with underscore
4. Check Vortex logs for loading errors

### Configuration Errors

For configuration validation issues:

1. Review your Pydantic schema definition
2. Check required fields are provided
3. Verify data types match schema
4. Test configuration validation separately

### Connection Failures

If provider connections fail:

1. Test API credentials manually
2. Check network connectivity
3. Verify API endpoints are correct
4. Review rate limiting settings

### Performance Issues

For slow plugin performance:

1. Implement connection pooling
2. Add response caching
3. Use async/await for I/O operations
4. Monitor and log performance metrics

## Examples

See the built-in plugins for complete examples:

- **Yahoo Finance Plugin**: `src/vortex/plugins/builtin/yahoo_plugin.py`
- **Barchart Plugin**: `src/vortex/plugins/builtin/barchart_plugin.py`  
- **IBKR Plugin**: `src/vortex/plugins/builtin/ibkr_plugin.py`

## API Reference

For detailed API documentation, see:

- `vortex.plugins.base.ProviderPlugin` - Base plugin interface
- `vortex.plugins.registry.ProviderRegistry` - Plugin registry
- `vortex.plugins.exceptions` - Plugin-specific exceptions
- `vortex.data_providers.data_provider.DataProvider` - Data provider interface