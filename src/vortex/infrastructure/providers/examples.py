"""
Examples demonstrating the enhanced provider infrastructure.

This module shows how to use the new configuration classes, builder patterns,
dependency injection, circuit breakers, and observability features.
"""

from typing import Optional
import logging

from .config import BarchartProviderConfig, YahooProviderConfig, IBKRProviderConfig
from .builders import barchart_builder, yahoo_builder, ibkr_builder
from .factory import ProviderFactory
from .metrics import get_metrics_collector, get_all_metrics


def example_basic_provider_creation():
    """Example: Basic provider creation using factory."""
    
    # Create factory
    factory = ProviderFactory()
    
    # Create providers using factory (traditional approach)
    barchart = factory.create_provider('barchart', {
        'username': 'your_username',
        'password': 'your_password'
    })
    
    yahoo = factory.create_provider('yahoo', {
        'cache_enabled': True,
        'validate_data_types': True
    })
    
    ibkr = factory.create_provider('ibkr', {
        'host': 'localhost',
        'port': 7497
    })
    
    return barchart, yahoo, ibkr


def example_configuration_classes():
    """Example: Using configuration classes for type safety."""
    
    # Create strongly-typed configurations
    barchart_config = BarchartProviderConfig(
        username='your_username',
        password='your_password',
        daily_limit=200,
        request_timeout=45,
        download_timeout=90,
        max_retries=5
    )
    
    yahoo_config = YahooProviderConfig(
        cache_enabled=True,
        cache_ttl_hours=48,
        validate_data_types=True,
        repair_data=True,
        rate_limit_delay=0.2
    )
    
    ibkr_config = IBKRProviderConfig(
        host='10.0.0.100',
        port=7497,
        connection_timeout=60,
        historical_data_timeout=180,
        use_rth_only=False,  # Include pre/post market data
        market_data_type=1   # Live data
    )
    
    # Validate configurations
    assert barchart_config.validate(), "Barchart config validation failed"
    assert yahoo_config.validate(), "Yahoo config validation failed"
    assert ibkr_config.validate(), "IBKR config validation failed"
    
    return barchart_config, yahoo_config, ibkr_config


def example_builder_pattern():
    """Example: Using fluent builder pattern for complex configuration."""
    
    # Build Barchart provider with custom settings
    barchart = (barchart_builder()
                .with_credentials('username', 'password')
                .with_timeouts(request_timeout=60, download_timeout=120)
                .with_rate_limiting(daily_limit=250, max_retries=3)
                .build())
    
    # Build Yahoo provider with custom caching
    yahoo = (yahoo_builder()
             .with_cache_settings(cache_enabled=True, cache_ttl_hours=12)
             .with_validation_settings(validate_data_types=True, repair_data=False)
             .build())
    
    # Build IBKR provider with production settings
    ibkr = (ibkr_builder()
            .with_connection_settings(host='prod-gateway', port=4002, client_id=42)
            .with_timeout_settings(connection_timeout=30, data_timeout=300)
            .with_data_settings(use_rth_only=True, market_data_type=3)
            .build())
    
    return barchart, yahoo, ibkr


def example_factory_with_builders():
    """Example: Using factory with builder functions."""
    
    factory = ProviderFactory()
    
    # Create provider using builder function
    barchart = factory.create_provider_with_builder(
        'barchart',
        lambda b: b.with_credentials('user', 'pass')
                  .with_timeouts(30, 60)
                  .with_rate_limiting(150, 3)
    )
    
    # Create provider with minimal configuration
    yahoo = factory.create_provider_with_builder('yahoo')
    
    # Create provider with complex builder configuration
    ibkr = factory.create_provider_with_builder(
        'ibkr',
        lambda b: b.with_connection_settings('localhost', 7497)
                  .with_timeout_settings(45, 120)
    )
    
    return barchart, yahoo, ibkr


def example_dependency_injection():
    """Example: Advanced dependency injection."""
    
    # Create custom dependencies
    class CustomBarchartAuth:
        def __init__(self, username, password):
            self.username = username
            self.password = password
            
        def login(self):
            print(f"Custom auth for {self.username}")
            
        def logout(self):
            print("Custom logout")
    
    class CustomYahooCache:
        def configure_cache(self, cache_dir):
            print(f"Custom cache configured: {cache_dir}")
            
        def clear_cache(self):
            print("Custom cache cleared")
    
    # Inject custom dependencies
    barchart = (barchart_builder()
                .with_credentials('user', 'pass')
                .with_auth_handler(CustomBarchartAuth('user', 'pass'))
                .build())
    
    yahoo = (yahoo_builder()
             .with_cache_manager(CustomYahooCache())
             .build())
    
    return barchart, yahoo


def example_observability_and_metrics():
    """Example: Using observability and metrics features."""
    
    # Create providers
    barchart = (barchart_builder()
                .with_credentials('user', 'pass')
                .build())
    
    # Use provider and check metrics
    try:
        # This would normally fetch real data
        # data = barchart.fetch_historical_data(instrument, period, start, end)
        pass
    except Exception as e:
        logging.error(f"Fetch failed: {e}")
    
    # Get health status with metrics
    health = barchart.get_health_status()
    print(f"Provider health: {health['health_score']:.1f}")
    print(f"Circuit breaker state: {health['circuit_breaker']['state']}")
    print(f"Total operations: {health['metrics']['total_operations']}")
    print(f"Success rate: {health['metrics']['success_rate']:.1f}%")
    
    # Get active operations
    active_ops = barchart.get_active_operations()
    print(f"Active operations: {len(active_ops)}")
    
    # Get metrics for specific provider
    metrics = barchart.get_metrics()
    print(f"Average duration: {metrics.average_duration_ms:.1f}ms")
    print(f"Error counts: {metrics.error_counts}")
    
    return health, active_ops, metrics


def example_global_metrics():
    """Example: Using global metrics collection."""
    
    # Get metrics for all providers
    all_metrics = get_all_metrics()
    
    for provider_name, metrics in all_metrics.items():
        print(f"\n=== {provider_name.upper()} METRICS ===")
        print(f"Total operations: {metrics.total_operations}")
        print(f"Success rate: {metrics.success_rate:.1f}%")
        print(f"Average duration: {metrics.average_duration_ms:.1f}ms")
        print(f"Performance distribution: {metrics.performance_buckets}")
        print(f"Recent errors: {metrics.error_counts}")
    
    # Get metrics collector for specific provider
    barchart_collector = get_metrics_collector('barchart')
    health_score = barchart_collector.get_health_score()
    print(f"\nBarchart health score: {health_score:.1f}/100")
    
    return all_metrics


def example_error_handling_and_resilience():
    """Example: Demonstrating error handling and resilience features."""
    
    # Create provider with custom circuit breaker settings
    from .config import CircuitBreakerConfig
    
    cb_config = CircuitBreakerConfig(
        failure_threshold=5,  # Open after 5 failures
        recovery_timeout=120, # Wait 2 minutes before trying again
        success_threshold=3   # Need 3 successes to close
    )
    
    barchart = (barchart_builder()
                .with_credentials('user', 'pass')
                .with_circuit_breaker_config(cb_config)
                .build())
    
    # The provider will automatically:
    # 1. Use circuit breaker to prevent cascade failures
    # 2. Track all operations with correlation IDs
    # 3. Collect comprehensive metrics
    # 4. Apply standardized error handling
    # 5. Validate all fetched data consistently
    
    return barchart


def example_complete_workflow():
    """Example: Complete workflow showing all features."""
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # 1. Create providers with advanced configuration
    logger.info("Creating providers with enhanced configuration...")
    
    providers = {
        'barchart': barchart_builder()
            .with_credentials('demo_user', 'demo_pass')
            .with_timeouts(30, 90)
            .with_rate_limiting(150, 3)
            .build(),
            
        'yahoo': yahoo_builder()
            .with_cache_settings(cache_enabled=True, cache_ttl_hours=24)
            .with_validation_settings(validate_data_types=True, repair_data=True)
            .build(),
            
        'ibkr': ibkr_builder()
            .with_connection_settings('localhost', 7497)
            .with_timeout_settings(60, 180)
            .build()
    }
    
    # 2. Check provider health before operations
    logger.info("Checking provider health...")
    for name, provider in providers.items():
        health = provider.get_health_status()
        logger.info(f"{name}: Health={health['health_score']:.1f}, "
                   f"CB={health['circuit_breaker']['state']}")
    
    # 3. Simulate operations (would be real data fetching)
    logger.info("Simulating operations...")
    for name, provider in providers.items():
        try:
            # Simulate successful operation
            with provider._metrics_collector.track_operation('test_operation', symbol='TEST'):
                import time
                time.sleep(0.1)  # Simulate work
                logger.info(f"Completed test operation for {name}")
        except Exception as e:
            logger.error(f"Operation failed for {name}: {e}")
    
    # 4. Review final metrics
    logger.info("Final metrics summary:")
    all_metrics = get_all_metrics()
    
    for provider_name, metrics in all_metrics.items():
        logger.info(f"{provider_name}: {metrics.total_operations} ops, "
                   f"{metrics.success_rate:.1f}% success, "
                   f"{metrics.average_duration_ms:.1f}ms avg")
    
    return providers, all_metrics


if __name__ == "__main__":
    """Run examples to demonstrate enhanced provider infrastructure."""
    
    print("=== Enhanced Provider Infrastructure Examples ===\n")
    
    print("1. Configuration Classes:")
    configs = example_configuration_classes()
    print(f"Created {len(configs)} validated configurations\n")
    
    print("2. Builder Pattern:")
    providers = example_builder_pattern()
    print(f"Built {len(providers)} providers with fluent interface\n")
    
    print("3. Factory with Builders:")
    factory_providers = example_factory_with_builders()
    print(f"Created {len(factory_providers)} providers via factory\n")
    
    print("4. Complete Workflow:")
    workflow_result = example_complete_workflow()
    print("Completed full workflow demonstration\n")
    
    print("=== All Examples Completed Successfully ===")