"""
Pytest configuration and shared fixtures for Vortex tests.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

import pytest

# Import test dependencies conditionally to avoid hard dependency
try:
    from freezegun import freeze_time
except ImportError:
    freeze_time = None

from vortex.config import ConfigManager, VortexConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture  
def config_dir(temp_dir):
    """Create a temporary config directory."""
    config_dir = temp_dir / ".config" / "vortex"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def config_file(config_dir):
    """Create a temporary config file path."""
    return config_dir / "config.toml"


@pytest.fixture
def sample_config_data():
    """Sample configuration data for testing."""
    return {
        "general": {
            "output_directory": "./test_data",
            "log_level": "DEBUG", 
            "backup_enabled": True,
            "dry_run": False,
            "random_sleep_max": 5
        },
        "providers": {
            "barchart": {
                "username": "test@example.com",
                "password": "test_password",
                "daily_limit": 100
            },
            "yahoo": {
                "enabled": True
            },
            "ibkr": {
                "host": "localhost",
                "port": 7497,
                "client_id": 1,
                "timeout": 30
            }
        },
        "date_range": {
            "start_year": 2020,
            "end_year": 2024
        }
    }


@pytest.fixture
def config_manager(config_file):
    """Create a ConfigManager instance for testing."""
    return ConfigManager(config_file)


@pytest.fixture
def vortex_config(sample_config_data):
    """Create a VortexConfig instance for testing."""
    return VortexConfig(**sample_config_data)


@pytest.fixture
def mock_data_provider():
    """Mock data provider for testing."""
    provider = Mock()
    provider.download_data.return_value = [
        {"date": "2024-01-01", "open": 100.0, "high": 105.0, "low": 95.0, "close": 102.0, "volume": 1000},
        {"date": "2024-01-02", "open": 102.0, "high": 108.0, "low": 98.0, "close": 105.0, "volume": 1200},
    ]
    return provider


@pytest.fixture 
def mock_storage():
    """Mock storage for testing."""
    storage = Mock()
    storage.save.return_value = True
    storage.load.return_value = []
    return storage


@pytest.fixture
def clean_environment():
    """Ensure clean environment variables for testing."""
    # Store original environment
    original_env = {}
    
    # Environment variables that might affect tests
    env_vars = [
        "VORTEX_OUTPUT_DIR", "VORTEX_LOG_LEVEL", "VORTEX_BACKUP_ENABLED",
        "VORTEX_DRY_RUN", "VORTEX_BARCHART_USERNAME", "VORTEX_BARCHART_PASSWORD",
        "VORTEX_BARCHART_DAILY_LIMIT", "VORTEX_IBKR_HOST", "VORTEX_IBKR_PORT",
        "BCU_OUTPUT_DIR", "BCU_USERNAME", "BCU_PASSWORD", "BCU_LOGGING_LEVEL",
        "BCU_DRY_RUN", "BCU_BACKUP_DATA", "BCU_PROVIDER_HOST", "BCU_PROVIDER_PORT"
    ]
    
    for var in env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restore original environment
    for var, value in original_env.items():
        os.environ[var] = value


@pytest.fixture
def sample_instrument_data():
    """Sample instrument configuration data."""
    return {
        "futures": {
            "GC": {
                "code": "GC",
                "asset_class": "future",
                "tick_date": "2024-06-01",
                "start_date": "2020-01-01",
                "periods": "1d,4h,1h",
                "cycle": "HMUZ",
                "days_count": 360
            }
        },
        "stocks": {
            "AAPL": {
                "code": "AAPL", 
                "asset_class": "stock",
                "start_date": "2020-01-01",
                "periods": "1d"
            }
        }
    }


@pytest.fixture
def assets_file(temp_dir, sample_instrument_data):
    """Create a sample assets file for testing."""
    import json
    assets_file = temp_dir / "test_assets.json"
    with open(assets_file, 'w') as f:
        json.dump(sample_instrument_data, f)
    return assets_file


# Network-dependent fixtures
@pytest.fixture
def skip_if_no_network():
    """Skip test if no network connection available."""
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
    except OSError:
        pytest.skip("No network connection available")


@pytest.fixture  
def skip_if_no_credentials():
    """Skip test if no valid credentials are available."""
    if not (os.environ.get('VORTEX_BARCHART_USERNAME') or os.environ.get('BCU_USERNAME')):
        pytest.skip("No credentials available for testing")


# Mock time fixture
if freeze_time:
    @pytest.fixture
    def frozen_time():
        """Freeze time for deterministic testing."""
        with freeze_time("2024-01-15 12:00:00") as frozen:
            yield frozen
else:
    @pytest.fixture
    def frozen_time():
        """Placeholder when freezegun not available."""
        pytest.skip("freezegun not available")


# Pytest hooks
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests") 
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "network: Tests requiring network")
    config.addinivalue_line("markers", "credentials: Tests requiring credentials")


def pytest_collection_modifyitems(config, items):
    """Auto-mark tests based on patterns."""
    for item in items:
        # Mark network tests
        if "network" in item.name.lower() or "download" in item.name.lower():
            item.add_marker(pytest.mark.network)
        
        # Mark credential tests  
        if "credential" in item.name.lower() or "auth" in item.name.lower():
            item.add_marker(pytest.mark.credentials)
        
        # Mark slow tests
        if "slow" in item.name.lower() or "integration" in item.name.lower():
            item.add_marker(pytest.mark.slow)


# Add environment info for debugging
@pytest.fixture(scope="session", autouse=True)
def test_environment_info():
    """Print test environment information."""
    print(f"\n=== Test Environment ===")
    print(f"Python: {os.sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
    print("=" * 30)