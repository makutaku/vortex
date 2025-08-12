"""
Example demonstrating the architecture improvements for dependency injection,
provider abstraction, and configuration management.
"""

from pathlib import Path
from datetime import datetime, timedelta

from vortex.infrastructure.providers.factory import ProviderFactory
from vortex.infrastructure.config import get_config_service
from vortex.infrastructure.providers.protocol import DataProviderProtocol
from vortex.models.stock import Stock
from vortex.models.period import Period


def example_dependency_injection():
    """Example of using the new dependency injection pattern."""
    print("=== Dependency Injection Example ===\n")
    
    # 1. Get configuration service (singleton)
    config_service = get_config_service()
    
    # 2. Create provider factory with injected configuration
    factory = ProviderFactory(config_service._manager)
    
    # 3. Create providers using factory (proper dependency injection)
    yahoo_provider = factory.create_provider('yahoo')
    print(f"Created Yahoo provider: {yahoo_provider.get_name()}")
    
    # Can override configuration if needed
    barchart_override = {
        'username': 'test_user',
        'password': 'test_pass',
        'daily_limit': 250
    }
    barchart_provider = factory.create_provider('barchart', barchart_override)
    print(f"Created Barchart provider with override: {barchart_provider.get_name()}")


def example_provider_protocol():
    """Example of using the provider protocol for type safety."""
    print("\n=== Provider Protocol Example ===\n")
    
    factory = ProviderFactory()
    
    # The factory returns providers that implement DataProviderProtocol
    provider: DataProviderProtocol = factory.create_provider('yahoo')
    
    # All providers have consistent interface
    print(f"Provider name: {provider.get_name()}")
    print(f"Supported timeframes: {[str(tf) for tf in provider.get_supported_timeframes()]}")
    
    # Type-safe operations
    period = Period('1d')
    max_range = provider.get_max_range(period)
    print(f"Max range for {period}: {max_range}")


def example_configuration_service():
    """Example of using the unified configuration service."""
    print("\n=== Configuration Service Example ===\n")
    
    # Get the configuration service
    config_service = get_config_service()
    
    # Access configuration in a standardized way
    output_dir = config_service.get_output_directory()
    print(f"Output directory: {output_dir}")
    
    default_provider = config_service.get_default_provider()
    print(f"Default provider: {default_provider}")
    
    # Check provider configuration
    is_valid = config_service.validate_provider_config('barchart')
    print(f"Barchart config valid: {is_valid}")
    
    if not is_valid:
        missing = config_service.get_missing_provider_fields('barchart')
        print(f"Missing fields: {missing}")
    
    # Get provider-specific configuration
    yahoo_config = config_service.get_provider_config('yahoo')
    print(f"Yahoo config: {yahoo_config}")


def example_http_separation():
    """Example showing HTTP concerns separated from business logic."""
    print("\n=== HTTP Separation Example ===\n")
    
    # The new architecture separates HTTP client from provider logic
    from vortex.infrastructure.providers.barchart.http_client import BarchartHttpClient
    from vortex.infrastructure.providers.barchart.auth import BarchartAuth
    
    # HTTP client handles all HTTP concerns
    auth = BarchartAuth('username', 'password')
    http_client = BarchartHttpClient(auth)
    
    # Provider focuses on business logic, using the HTTP client
    # This separation makes testing easier and code more maintainable
    print("HTTP client initialized separately from provider logic")
    print("Provider can focus on data transformation and business rules")


def example_complete_workflow():
    """Complete example showing all improvements working together."""
    print("\n=== Complete Workflow Example ===\n")
    
    # 1. Setup configuration service
    config_service = get_config_service()
    
    # 2. Create factory with configuration
    factory = ProviderFactory(config_service._manager)
    
    # 3. List available providers
    providers = factory.list_providers()
    print(f"Available providers: {providers}")
    
    # 4. Get provider info
    for provider_name in providers:
        info = factory.get_provider_info(provider_name)
        print(f"\n{provider_name}:")
        print(f"  Description: {info['description']}")
        print(f"  Requires auth: {info['requires_auth']}")
        print(f"  Required config: {info.get('required_config', [])}")
    
    # 5. Create provider with proper dependency injection
    provider = factory.create_provider('yahoo')
    
    # 6. Use provider through protocol interface
    instrument = Stock('AAPL')
    period = Period('1d')
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    print(f"\nFetching {instrument.get_symbol()} data...")
    # Would actually fetch data in real usage
    # df = provider.fetch_historical_data(instrument, period, start_date, end_date)


if __name__ == '__main__':
    # Run all examples
    example_dependency_injection()
    example_provider_protocol()
    example_configuration_service()
    example_http_separation()
    example_complete_workflow()