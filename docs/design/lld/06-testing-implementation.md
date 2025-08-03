# Testing Implementation Details

**Version:** 1.0  
**Date:** 2025-01-08  
**Related:** [Testing Strategy](../hld/testing-strategy.md)

## 1. Testing Framework Implementation

### 1.1 Base Test Classes
```python
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from datetime import datetime, timedelta
import logging

class BCUtilsTestCase(unittest.TestCase):
    """Base test case for BC-Utils with common setup and utilities"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.test_data_dir = self.temp_dir / "test_data"
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure test logging
        logging.disable(logging.CRITICAL)
        
        # Create sample test data
        self.sample_data = self._create_sample_data()
        
    def tearDown(self):
        """Clean up test fixtures"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        logging.disable(logging.NOTSET)
        
    def _create_sample_data(self) -> pd.DataFrame:
        """Create sample financial data for testing"""
        dates = pd.date_range('2024-01-01', periods=30, freq='D')
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': [100.0 + i * 0.5 for i in range(30)],
            'high': [101.0 + i * 0.5 for i in range(30)],
            'low': [99.0 + i * 0.5 for i in range(30)],
            'close': [100.5 + i * 0.5 for i in range(30)],
            'volume': [1000 + i * 10 for i in range(30)],
            'symbol': ['TEST'] * 30,
            'provider': ['test'] * 30
        })
        
    def assert_dataframe_equal(self, df1: pd.DataFrame, df2: pd.DataFrame, 
                              ignore_index: bool = True):
        """Assert two DataFrames are equal with better error messages"""
        try:
            if ignore_index:
                df1 = df1.reset_index(drop=True)
                df2 = df2.reset_index(drop=True)
            pd.testing.assert_frame_equal(df1, df2)
        except AssertionError as e:
            self.fail(f"DataFrames are not equal:\n{e}")
```

### 1.2 Mock Provider Implementation
```python
class MockDataProvider:
    """Mock data provider for testing"""
    
    def __init__(self, name: str = "mock", return_data: pd.DataFrame = None):
        self.name = name
        self.authenticated = False
        self.return_data = return_data
        self.call_history = []
        self.rate_limit_calls = 0
        self.max_calls = 100
        
    def authenticate(self, credentials: dict) -> bool:
        """Mock authentication"""
        self.call_history.append(('authenticate', credentials))
        self.authenticated = credentials.get('username') == 'test_user'
        return self.authenticated
        
    def get_data(self, instrument, date_range) -> pd.DataFrame:
        """Mock data retrieval"""
        self.call_history.append(('get_data', instrument.symbol, date_range))
        
        if not self.authenticated:
            raise AuthenticationError("Not authenticated")
            
        if self.rate_limit_calls >= self.max_calls:
            raise RateLimitError("Rate limit exceeded")
            
        self.rate_limit_calls += 1
        
        if self.return_data is not None:
            return self.return_data.copy()
        
        # Generate mock data
        return self._generate_mock_data(instrument, date_range)
        
    def _generate_mock_data(self, instrument, date_range) -> pd.DataFrame:
        """Generate deterministic mock data"""
        days = (date_range.end - date_range.start).days + 1
        dates = pd.date_range(date_range.start, periods=days, freq='D')
        
        base_price = 100.0
        data = []
        
        for i, date in enumerate(dates):
            price = base_price + i * 0.1
            data.append({
                'timestamp': date,
                'open': price,
                'high': price + 1.0,
                'low': price - 1.0,
                'close': price + 0.5,
                'volume': 1000 + i * 10,
                'symbol': instrument.symbol,
                'provider': self.name
            })
            
        return pd.DataFrame(data)
        
    def get_supported_instruments(self) -> list:
        """Mock supported instruments"""
        return ['stock', 'future', 'forex']
        
    def get_rate_limits(self) -> dict:
        """Mock rate limit status"""
        return {
            'daily': self.max_calls,
            'remaining': self.max_calls - self.rate_limit_calls
        }
```

## 2. Provider Testing Implementation

### 2.1 Provider Interface Tests
```python
class TestDataProviderInterface(BCUtilsTestCase):
    """Test data provider interface compliance"""
    
    def test_provider_interface_compliance(self):
        """Test that all providers implement required interface"""
        from bcutils.data_providers.data_provider import DataProvider
        from bcutils.data_providers.barchart_provider import BarchartDataProvider
        from bcutils.data_providers.yahoo_provider import YahooDataProvider
        
        providers = [BarchartDataProvider, YahooDataProvider]
        
        for provider_class in providers:
            with self.subTest(provider=provider_class.__name__):
                # Check inheritance
                self.assertTrue(issubclass(provider_class, DataProvider))
                
                # Check required methods exist
                required_methods = [
                    'authenticate', 'get_data', 'get_supported_instruments'
                ]
                for method in required_methods:
                    self.assertTrue(hasattr(provider_class, method))
    
    def test_provider_authentication_flow(self):
        """Test provider authentication workflow"""
        provider = MockDataProvider()
        
        # Test failed authentication
        result = provider.authenticate({'username': 'wrong', 'password': 'wrong'})
        self.assertFalse(result)
        self.assertFalse(provider.authenticated)
        
        # Test successful authentication
        result = provider.authenticate({'username': 'test_user', 'password': 'test_pass'})
        self.assertTrue(result)
        self.assertTrue(provider.authenticated)
    
    def test_provider_rate_limiting(self):
        """Test provider rate limiting behavior"""
        provider = MockDataProvider()
        provider.max_calls = 2
        provider.authenticate({'username': 'test_user', 'password': 'test_pass'})
        
        # Create test instrument and date range
        instrument = Mock()
        instrument.symbol = 'TEST'
        date_range = Mock()
        date_range.start = datetime(2024, 1, 1)
        date_range.end = datetime(2024, 1, 2)
        
        # First two calls should succeed
        provider.get_data(instrument, date_range)
        provider.get_data(instrument, date_range)
        
        # Third call should raise rate limit error
        with self.assertRaises(RateLimitError):
            provider.get_data(instrument, date_range)
```

### 2.2 Provider Integration Tests
```python
class TestProviderIntegration(BCUtilsTestCase):
    """Integration tests for data providers"""
    
    @patch('requests.Session')
    def test_barchart_provider_integration(self, mock_session):
        """Test Barchart provider integration"""
        # Mock HTTP responses
        mock_response = Mock()
        mock_response.text = self._get_sample_csv_data()
        mock_response.status_code = 200
        mock_session.return_value.get.return_value = mock_response
        
        # Create provider instance
        from bcutils.data_providers.barchart_provider import BarchartDataProvider
        provider = BarchartDataProvider({'daily_limit': 150})
        
        # Test data retrieval
        instrument = Mock()
        instrument.symbol = 'GCZ24'
        date_range = Mock()
        date_range.start = datetime(2024, 1, 1)
        date_range.end = datetime(2024, 1, 31)
        
        # Should require authentication first
        with self.assertRaises(AuthenticationError):
            provider.get_data(instrument, date_range)
    
    def _get_sample_csv_data(self) -> str:
        """Get sample CSV data for testing"""
        return """timestamp,open,high,low,close,volume
2024-01-01,100.0,101.0,99.0,100.5,1000
2024-01-02,100.5,101.5,99.5,101.0,1100
2024-01-03,101.0,102.0,100.0,101.5,1200"""
```

## 3. Storage Testing Implementation

### 3.1 Storage Interface Tests
```python
class TestStorageInterface(BCUtilsTestCase):
    """Test storage interface implementations"""
    
    def test_csv_storage_operations(self):
        """Test CSV storage save/load operations"""
        from bcutils.data_storage.csv_storage import CsvStorage
        
        storage = CsvStorage(str(self.test_data_dir))
        
        # Test save operation
        test_file = "test_data.csv"
        result = storage.save(self.sample_data, test_file)
        
        self.assertTrue(result.success)
        self.assertEqual(result.row_count, len(self.sample_data))
        self.assertTrue(storage.exists(test_file))
        
        # Test load operation
        loaded_data = storage.load(test_file)
        self.assert_dataframe_equal(self.sample_data, loaded_data)
        
        # Test delete operation
        self.assertTrue(storage.delete(test_file))
        self.assertFalse(storage.exists(test_file))
    
    def test_parquet_storage_operations(self):
        """Test Parquet storage save/load operations"""
        from bcutils.data_storage.parquet_storage import ParquetStorage
        
        storage = ParquetStorage(str(self.test_data_dir))
        
        # Test save operation
        test_file = "test_data.parquet"
        result = storage.save(self.sample_data, test_file)
        
        self.assertTrue(result.success)
        self.assertEqual(result.row_count, len(self.sample_data))
        
        # Test load operation
        loaded_data = storage.load(test_file)
        self.assert_dataframe_equal(self.sample_data, loaded_data)
    
    def test_storage_deduplication(self):
        """Test data deduplication functionality"""
        from bcutils.data_storage.deduplicator import DataDeduplicator
        
        # Create duplicate data
        duplicate_data = pd.concat([self.sample_data, self.sample_data.head(5)])
        
        deduplicator = DataDeduplicator()
        result = deduplicator.deduplicate_data(duplicate_data)
        
        # Should have same length as original (duplicates removed)
        self.assertEqual(len(result), len(self.sample_data))
        
        # Should be sorted by timestamp
        self.assertTrue(result['timestamp'].is_monotonic_increasing)
```

### 3.2 Storage Performance Tests
```python
class TestStoragePerformance(BCUtilsTestCase):
    """Performance tests for storage operations"""
    
    def test_large_dataset_performance(self):
        """Test storage performance with large datasets"""
        import time
        from bcutils.data_storage.csv_storage import CsvStorage
        
        # Create large dataset
        large_data = self._create_large_dataset(10000)
        storage = CsvStorage(str(self.test_data_dir))
        
        # Time save operation
        start_time = time.time()
        result = storage.save(large_data, "large_data.csv")
        save_time = time.time() - start_time
        
        self.assertTrue(result.success)
        self.assertLess(save_time, 10.0)  # Should complete within 10 seconds
        
        # Time load operation
        start_time = time.time()
        loaded_data = storage.load("large_data.csv")
        load_time = time.time() - start_time
        
        self.assertEqual(len(loaded_data), 10000)
        self.assertLess(load_time, 5.0)  # Should load within 5 seconds
    
    def _create_large_dataset(self, size: int) -> pd.DataFrame:
        """Create large dataset for performance testing"""
        dates = pd.date_range('2020-01-01', periods=size, freq='D')
        
        return pd.DataFrame({
            'timestamp': dates,
            'open': [100.0 + i * 0.01 for i in range(size)],
            'high': [101.0 + i * 0.01 for i in range(size)],
            'low': [99.0 + i * 0.01 for i in range(size)],
            'close': [100.5 + i * 0.01 for i in range(size)],
            'volume': [1000 + i for i in range(size)],
            'symbol': ['PERF'] * size,
            'provider': ['test'] * size
        })
```

## 4. Integration Testing Implementation

### 4.1 End-to-End Workflow Tests
```python
class TestEndToEndWorkflow(BCUtilsTestCase):
    """End-to-end workflow integration tests"""
    
    def test_complete_download_workflow(self):
        """Test complete download workflow from provider to storage"""
        from bcutils.downloaders.updating_downloader import UpdatingDownloader
        from bcutils.data_storage.csv_storage import CsvStorage
        
        # Setup components
        storage = CsvStorage(str(self.test_data_dir))
        provider = MockDataProvider(return_data=self.sample_data)
        downloader = UpdatingDownloader(storage, provider)
        
        # Create test configuration
        config = Mock()
        config.instrument_config = {
            'symbol': 'TEST',
            'type': 'stock'
        }
        config.start_date = datetime(2024, 1, 1)
        config.end_date = datetime(2024, 1, 31)
        config.provider = 'mock'
        
        # Execute workflow
        result = downloader.download_instrument_data(config)
        
        # Verify results
        self.assertTrue(result)
        self.assertTrue(len(provider.call_history) > 0)
        
        # Check that data was saved
        saved_files = storage.list_files()
        self.assertGreater(len(saved_files), 0)
    
    def test_error_recovery_workflow(self):
        """Test error recovery in download workflow"""
        from bcutils.downloaders.updating_downloader import UpdatingDownloader
        from bcutils.data_storage.csv_storage import CsvStorage
        
        # Setup components with failing provider
        storage = CsvStorage(str(self.test_data_dir))
        provider = MockDataProvider()
        provider.max_calls = 0  # Force immediate rate limit
        
        downloader = UpdatingDownloader(storage, provider)
        
        # Create test configuration
        config = Mock()
        config.instrument_config = {'symbol': 'TEST', 'type': 'stock'}
        config.start_date = datetime(2024, 1, 1)
        config.end_date = datetime(2024, 1, 31)
        
        # Execute workflow - should handle errors gracefully
        result = downloader.download_instrument_data(config)
        
        # Should fail but not crash
        self.assertFalse(result)
```

## 5. Security Testing Implementation

### 5.1 Input Validation Tests
```python
class TestSecurityValidation(BCUtilsTestCase):
    """Security validation tests"""
    
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks"""
        from bcutils.security.validator import ConfigurationValidator
        
        validator = ConfigurationValidator()
        
        # Test malicious paths
        malicious_configs = [
            {'download_directory': '../../../etc/passwd'},
            {'download_directory': '../../sensitive_data'},
            {'download_directory': '/etc/shadow'},
        ]
        
        for config in malicious_configs:
            with self.subTest(config=config):
                errors = validator.validate_configuration(config)
                self.assertGreater(len(errors), 0)
    
    def test_command_injection_protection(self):
        """Test protection against command injection"""
        from bcutils.security.validator import ConfigurationValidator
        
        validator = ConfigurationValidator()
        
        # Test malicious commands
        malicious_configs = [
            {'provider': {'host': 'localhost; rm -rf /'}},
            {'provider': {'host': '$(cat /etc/passwd)'}},
            {'provider': {'host': '`whoami`'}},
        ]
        
        for config in malicious_configs:
            with self.subTest(config=config):
                errors = validator.validate_configuration(config)
                self.assertGreater(len(errors), 0)
    
    def test_data_sanitization(self):
        """Test data sanitization functionality"""
        from bcutils.security.sanitizer import DataSanitizer
        
        sanitizer = DataSanitizer()
        
        # Create malicious data
        malicious_data = pd.DataFrame({
            'timestamp': ['2024-01-01'],
            'open': [100.0],
            'high': [101.0],
            'low': [99.0],
            'close': [100.5],
            'volume': [1000],
            'symbol': ['<script>alert("xss")</script>'],
            'provider': ['test; DROP TABLE users;']
        })
        
        sanitized = sanitizer.sanitize_dataframe(malicious_data)
        
        # Check that malicious content was removed
        self.assertNotIn('<script>', sanitized['symbol'].iloc[0])
        self.assertNotIn('DROP TABLE', sanitized['provider'].iloc[0])
```

## 6. Test Data Management

### 6.1 Test Data Factory
```python
class TestDataFactory:
    """Factory for creating test data scenarios"""
    
    @staticmethod
    def create_stock_data(symbol: str = "AAPL", days: int = 30) -> pd.DataFrame:
        """Create realistic stock price data"""
        dates = pd.date_range('2024-01-01', periods=days, freq='D')
        
        # Generate realistic price movements
        import random
        base_price = 150.0
        prices = []
        
        for i, date in enumerate(dates):
            # Random walk with trend
            change = random.gauss(0, 1) * 0.02  # 2% daily volatility
            base_price *= (1 + change)
            
            daily_range = base_price * 0.03  # 3% daily range
            open_price = base_price + random.gauss(0, daily_range/4)
            close_price = base_price + random.gauss(0, daily_range/4)
            high_price = max(open_price, close_price) + random.uniform(0, daily_range/2)
            low_price = min(open_price, close_price) - random.uniform(0, daily_range/2)
            
            prices.append({
                'timestamp': date,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': random.randint(1000000, 10000000),
                'symbol': symbol,
                'provider': 'test'
            })
        
        return pd.DataFrame(prices)
    
    @staticmethod
    def create_futures_data(symbol: str = "GCZ24", days: int = 30) -> pd.DataFrame:
        """Create realistic futures price data"""
        return TestDataFactory.create_stock_data(symbol, days)
```

## 7. Test Runner Configuration

### 7.1 Test Suite Configuration
```python
def create_test_suite():
    """Create comprehensive test suite"""
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestDataProviderInterface,
        TestProviderIntegration,
        TestStorageInterface,
        TestStoragePerformance,
        TestEndToEndWorkflow,
        TestSecurityValidation
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite

def run_tests(verbosity: int = 2):
    """Run all tests with specified verbosity"""
    suite = create_test_suite()
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
```

## Related Documents

- **[Component Implementation](01-component-implementation.md)** - Component testing integration
- **[Provider Implementation](03-provider-implementation.md)** - Provider testing details
- **[Storage Implementation](04-storage-implementation.md)** - Storage testing details
- **[Security Implementation](05-security-implementation.md)** - Security testing details

---

**Implementation Level:** Low-Level Design  
**Last Updated:** 2025-01-08  
**Reviewers:** QA Lead, Senior Developer