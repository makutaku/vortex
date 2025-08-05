# Testing Infrastructure

## Overview

Comprehensive testing infrastructure for Vortex with pytest, coverage reporting, and mock implementations.

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and pytest configuration
├── test_config.py        # Configuration system tests
├── test_downloader.py    # Downloader integration tests (updated)
├── test_cli.py          # CLI command tests
├── test_exceptions.py   # Exception handling tests
└── test_mocks.py        # Mock implementations and tests
```

## Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run specific test class
pytest tests/test_config.py::TestVortexConfig

# Run specific test
pytest tests/test_config.py::TestVortexConfig::test_default_config
```

### Test Categories
```bash
# Run only unit tests
pytest -m unit

# Run only integration tests  
pytest -m integration

# Run tests that don't require network
pytest -m "not network"

# Run tests that don't require credentials
pytest -m "not credentials"

# Skip slow tests
pytest -m "not slow"
```

### Coverage Reporting
```bash
# Run with coverage (configured in pyproject.toml)
pytest --cov=src/vortex

# Generate HTML coverage report
pytest --cov=src/vortex --cov-report=html

# Coverage reports are saved to htmlcov/
```

## Test Fixtures

### Configuration Fixtures
- `temp_dir` - Temporary directory for tests
- `config_dir` - Temporary config directory
- `config_file` - Temporary config file path
- `config_manager` - ConfigManager instance
- `vortex_config` - Sample VortexConfig instance
- `sample_config_data` - Sample configuration data

### Mock Fixtures
- `mock_data_provider` - Mock data provider
- `mock_failing_provider` - Provider that fails on specific symbol
- `mock_slow_provider` - Provider with artificial delay
- `mock_storage` - Mock file storage
- `mock_failing_storage` - Storage that fails on save

### Environment Fixtures
- `clean_environment` - Clean environment variables
- `skip_if_no_network` - Skip if no network connection
- `skip_if_no_credentials` - Skip if no test credentials

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **Configuration System**: VortexConfig, ConfigManager, validation
- **Exception Handling**: All exception classes and inheritance
- **Data Providers**: Basic provider creation and configuration
- **CLI Commands**: Command parsing and option handling (mocked)
- **Mock Components**: Mock implementations work correctly

### Integration Tests (`@pytest.mark.integration`)  
- **Downloader Flow**: End-to-end download process
- **Configuration Loading**: File and environment variable integration
- **CLI Workflow**: Complete CLI command execution

### Network Tests (`@pytest.mark.network`)
- Tests requiring internet connection
- Actual provider API calls
- Automatically marked based on test name patterns

### Credential Tests (`@pytest.mark.credentials`)
- Tests requiring valid provider credentials
- Uses environment variables: `VORTEX_BARCHART_USERNAME`, `VORTEX_BARCHART_PASSWORD`
- Automatically skipped if credentials not available

## Mock Implementations

### MockDataProvider
```python 
# Create provider that fails on specific symbol
provider = MockDataProvider(fail_on_symbol="FAIL")

# Create provider with artificial delay
provider = MockDataProvider(delay=0.5)

# Track download statistics
assert provider.download_count == 3
assert "AAPL" in provider.downloaded_symbols
```

### MockFileStorage
```python
# Create storage that fails on save
storage = MockFileStorage(fail_on_save=True)

# Track storage operations
assert storage.save_count == 5
assert storage.load_count == 2
```

## Test Configuration

### pytest.ini Options (in pyproject.toml)
```toml
[tool.pytest.ini_options]
addopts = [
    "-ra",                    # Show reason for all outcomes
    "--strict-markers",       # Strict marker usage
    "--cov=src/vortex",      # Coverage for vortex package
    "--cov-report=term-missing", # Show missing lines
    "--cov-fail-under=80",   # Fail if coverage < 80%
]
testpaths = ["tests"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests", 
    "slow: Slow tests",
    "network: Tests requiring network",
    "credentials: Tests requiring credentials",
]
```

### Coverage Configuration
- **Source**: `src/vortex`
- **Omit**: Test files, `__init__.py`, CLI entry point
- **Target**: 80% minimum coverage
- **Reports**: Terminal, HTML (`htmlcov/`), XML

## Dependencies

### Required for Testing
```toml
test = [
    "pytest>=6.2",
    "pytest-cov",         # Coverage reporting
    "pytest-mock",        # Mocking utilities
    "pytest-asyncio",     # Async test support
    "freezegun",          # Time freezing for tests
]
```

### Optional (for CLI tests)
- `click` - CLI framework (already required)
- `rich` - Terminal formatting (already required)

## Best Practices

### Test Organization
- One test file per module/component
- Group related tests in classes
- Use descriptive test names
- Mark tests appropriately (unit/integration/slow/network/credentials)

### Fixtures
- Use fixtures for common setup
- Keep fixtures focused and reusable
- Use `clean_environment` for environment-dependent tests
- Use temporary directories for file operations

### Mocking
- Mock external dependencies (network, file system)
- Use real objects for unit tests when possible
- Test both success and failure scenarios
- Track mock call statistics for verification

### Coverage
- Aim for 80%+ coverage
- Focus on critical business logic
- Don't test trivial code (getters/setters)
- Test error paths and edge cases

## Continuous Integration

Ready for CI/CD integration:
```yaml
# Example GitHub Actions step
- name: Run tests
  run: |
    pip install -e ".[test]"
    pytest
```

The testing infrastructure provides:
- ✅ **Comprehensive test coverage** for all major components
- ✅ **Mock implementations** for reliable, fast testing
- ✅ **Flexible test execution** with markers and categories
- ✅ **Coverage reporting** with configurable thresholds
- ✅ **CI/CD ready** configuration
- ✅ **Environment isolation** for reliable test execution