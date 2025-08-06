import pytest

from vortex.models.stock import Stock
from vortex.models.forex import Forex
from vortex.models.instrument import Instrument


class TestStock:
    def test_stock_creation(self):
        """Test basic Stock creation."""
        stock = Stock(id='AAPL', symbol='AAPL')
        
        assert stock.id == 'AAPL'
        assert stock.symbol == 'AAPL'

    def test_stock_creation_different_id_symbol(self):
        """Test Stock creation with different id and symbol."""
        stock = Stock(id='apple_stock', symbol='AAPL')
        
        assert stock.id == 'apple_stock'
        assert stock.symbol == 'AAPL'

    def test_stock_str_representation(self):
        """Test Stock string representation."""
        stock = Stock(id='MSFT', symbol='MSFT')
        
        result = str(stock)
        assert result == 'S|MSFT|MSFT'

    def test_stock_str_with_different_id_symbol(self):
        """Test Stock string representation with different id and symbol."""
        stock = Stock(id='microsoft_stock', symbol='MSFT')
        
        result = str(stock)
        assert result == 'S|microsoft_stock|MSFT'

    def test_stock_is_dated(self):
        """Test that stocks are not dated instruments."""
        stock = Stock(id='GOOGL', symbol='GOOGL')
        
        assert stock.is_dated() is False

    def test_stock_get_code(self):
        """Test Stock get_code method returns symbol."""
        stock = Stock(id='TSLA', symbol='TSLA')
        
        assert stock.get_code() == 'TSLA'

    def test_stock_get_symbol(self):
        """Test Stock get_symbol method returns symbol."""
        stock = Stock(id='NVDA', symbol='NVDA')
        
        assert stock.get_symbol() == 'NVDA'

    def test_stock_inheritance(self):
        """Test that Stock inherits from Instrument."""
        stock = Stock(id='AMZN', symbol='AMZN')
        
        assert isinstance(stock, Instrument)
        assert isinstance(stock, Stock)

    def test_stock_with_long_symbol(self):
        """Test Stock with longer symbol names."""
        stock = Stock(id='berkshire', symbol='BRK.A')
        
        assert stock.symbol == 'BRK.A'
        assert stock.get_code() == 'BRK.A'
        assert stock.get_symbol() == 'BRK.A'
        assert str(stock) == 'S|berkshire|BRK.A'

    def test_stock_with_special_characters(self):
        """Test Stock with special characters in symbol."""
        stock = Stock(id='test_id', symbol='BRK-B')
        
        assert stock.symbol == 'BRK-B'
        assert str(stock) == 'S|test_id|BRK-B'

    def test_multiple_stocks_independence(self):
        """Test that multiple Stock instances are independent."""
        stock1 = Stock(id='AAPL', symbol='AAPL')
        stock2 = Stock(id='MSFT', symbol='MSFT')
        
        assert stock1.symbol != stock2.symbol
        assert stock1.id != stock2.id
        assert str(stock1) != str(stock2)
        
        # Both should be stocks but different instances
        assert isinstance(stock1, Stock)
        assert isinstance(stock2, Stock)
        assert stock1 is not stock2

    def test_stock_dataclass_equality(self):
        """Test Stock equality comparison (dataclass behavior)."""
        stock1 = Stock(id='AAPL', symbol='AAPL')
        stock2 = Stock(id='AAPL', symbol='AAPL')
        stock3 = Stock(id='AAPL', symbol='MSFT')
        
        assert stock1 == stock2  # Same id and symbol
        assert stock1 != stock3  # Different symbol
        assert stock2 != stock3  # Different symbol

    def test_stock_method_consistency(self):
        """Test consistency between different Stock methods."""
        stock = Stock(id='TEST', symbol='TEST_SYMBOL')
        
        # get_code and get_symbol should return the same value for stocks
        assert stock.get_code() == stock.get_symbol()
        assert stock.get_code() == stock.symbol
        assert stock.get_symbol() == stock.symbol


class TestForex:
    def test_forex_creation(self):
        """Test basic Forex creation."""
        forex = Forex(id='EURUSD', symbol='EURUSD')
        
        assert forex.id == 'EURUSD'
        assert forex.symbol == 'EURUSD'

    def test_forex_creation_different_id_symbol(self):
        """Test Forex creation with different id and symbol."""
        forex = Forex(id='euro_dollar', symbol='EURUSD')
        
        assert forex.id == 'euro_dollar'
        assert forex.symbol == 'EURUSD'

    def test_forex_str_representation(self):
        """Test Forex string representation."""
        forex = Forex(id='GBPUSD', symbol='GBPUSD')
        
        result = str(forex)
        assert result == 'C|GBPUSD|GBPUSD'

    def test_forex_str_with_different_id_symbol(self):
        """Test Forex string representation with different id and symbol."""
        forex = Forex(id='pound_dollar', symbol='GBPUSD')
        
        result = str(forex)
        assert result == 'C|pound_dollar|GBPUSD'

    def test_forex_is_dated(self):
        """Test that forex pairs are not dated instruments."""
        forex = Forex(id='USDJPY', symbol='USDJPY')
        
        assert forex.is_dated() is False

    def test_forex_get_code(self):
        """Test Forex get_code method returns symbol."""
        forex = Forex(id='AUDUSD', symbol='AUDUSD')
        
        assert forex.get_code() == 'AUDUSD'

    def test_forex_get_symbol(self):
        """Test Forex get_symbol method returns symbol."""
        forex = Forex(id='NZDUSD', symbol='NZDUSD')
        
        assert forex.get_symbol() == 'NZDUSD'

    def test_forex_inheritance(self):
        """Test that Forex inherits from Instrument."""
        forex = Forex(id='USDCAD', symbol='USDCAD')
        
        assert isinstance(forex, Instrument)
        assert isinstance(forex, Forex)

    def test_forex_with_exotic_pairs(self):
        """Test Forex with exotic currency pairs."""
        forex = Forex(id='exotic', symbol='USDTRY')
        
        assert forex.symbol == 'USDTRY'
        assert forex.get_code() == 'USDTRY'
        assert forex.get_symbol() == 'USDTRY'
        assert str(forex) == 'C|exotic|USDTRY'

    def test_forex_with_crypto_pairs(self):
        """Test Forex with cryptocurrency pairs."""
        forex = Forex(id='crypto', symbol='BTCUSD')
        
        assert forex.symbol == 'BTCUSD'
        assert str(forex) == 'C|crypto|BTCUSD'

    def test_multiple_forex_independence(self):
        """Test that multiple Forex instances are independent."""
        forex1 = Forex(id='EURUSD', symbol='EURUSD')
        forex2 = Forex(id='GBPUSD', symbol='GBPUSD')
        
        assert forex1.symbol != forex2.symbol
        assert forex1.id != forex2.id
        assert str(forex1) != str(forex2)
        
        # Both should be forex but different instances
        assert isinstance(forex1, Forex)
        assert isinstance(forex2, Forex)
        assert forex1 is not forex2

    def test_forex_dataclass_equality(self):
        """Test Forex equality comparison (dataclass behavior)."""
        forex1 = Forex(id='EURUSD', symbol='EURUSD')
        forex2 = Forex(id='EURUSD', symbol='EURUSD')
        forex3 = Forex(id='EURUSD', symbol='GBPUSD')
        
        assert forex1 == forex2  # Same id and symbol
        assert forex1 != forex3  # Different symbol
        assert forex2 != forex3  # Different symbol

    def test_forex_method_consistency(self):
        """Test consistency between different Forex methods."""
        forex = Forex(id='TEST', symbol='TEST_PAIR')
        
        # get_code and get_symbol should return the same value for forex
        assert forex.get_code() == forex.get_symbol()
        assert forex.get_code() == forex.symbol
        assert forex.get_symbol() == forex.symbol


class TestStockForexComparison:
    def test_stock_vs_forex_str_format(self):
        """Test that Stock and Forex have different string format prefixes."""
        stock = Stock(id='AAPL', symbol='AAPL')
        forex = Forex(id='EURUSD', symbol='EURUSD')
        
        stock_str = str(stock)
        forex_str = str(forex)
        
        assert stock_str.startswith('S|')
        assert forex_str.startswith('C|')
        assert stock_str != forex_str

    def test_stock_and_forex_both_not_dated(self):
        """Test that both Stock and Forex are not dated instruments."""
        stock = Stock(id='MSFT', symbol='MSFT')
        forex = Forex(id='GBPUSD', symbol='GBPUSD')
        
        assert stock.is_dated() is False
        assert forex.is_dated() is False

    def test_stock_and_forex_inheritance(self):
        """Test that both Stock and Forex inherit from Instrument."""
        stock = Stock(id='GOOGL', symbol='GOOGL')
        forex = Forex(id='USDJPY', symbol='USDJPY')
        
        assert isinstance(stock, Instrument)
        assert isinstance(forex, Instrument)
        
        # But they are different types
        assert type(stock) != type(forex)
        assert not isinstance(stock, Forex)
        assert not isinstance(forex, Stock)

    def test_stock_and_forex_method_behavior(self):
        """Test that Stock and Forex have same method signatures but different types."""
        stock = Stock(id='TSLA', symbol='TSLA')
        forex = Forex(id='AUDUSD', symbol='AUDUSD')
        
        # Both should have same methods
        assert hasattr(stock, 'is_dated')
        assert hasattr(forex, 'is_dated')
        assert hasattr(stock, 'get_code')
        assert hasattr(forex, 'get_code')
        assert hasattr(stock, 'get_symbol')
        assert hasattr(forex, 'get_symbol')
        
        # Both should behave the same way for these methods
        assert stock.is_dated() == forex.is_dated()  # Both False
        assert stock.get_code() == stock.symbol
        assert forex.get_code() == forex.symbol

    def test_instrument_interface_compliance(self):
        """Test that both Stock and Forex comply with Instrument interface."""
        stock = Stock(id='NVDA', symbol='NVDA')
        forex = Forex(id='EURGBP', symbol='EURGBP')
        
        instruments = [stock, forex]
        
        for instrument in instruments:
            # All instruments should have these methods
            assert hasattr(instrument, 'is_dated')
            assert hasattr(instrument, 'get_code')
            assert hasattr(instrument, 'get_symbol')
            assert hasattr(instrument, '__str__')
            
            # All should have id attribute
            assert hasattr(instrument, 'id')
            assert instrument.id is not None
            
            # All methods should be callable
            assert callable(instrument.is_dated)
            assert callable(instrument.get_code)
            assert callable(instrument.get_symbol)