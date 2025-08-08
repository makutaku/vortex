"""
Tests for core instruments configuration functionality.

Tests InstrumentConfig class and related enums.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import json
from datetime import datetime, timedelta
import pytz

from vortex.core.instruments.config import (
    InstrumentConfig,
    InstrumentType,
    DEFAULT_CONTRACT_DURATION_IN_DAYS
)


class TestInstrumentType:
    """Test InstrumentType enum."""
    
    def test_instrument_type_values(self):
        """Test that InstrumentType has expected values."""
        assert InstrumentType.Forex == 'forex'
        assert InstrumentType.Future == 'future'
        assert InstrumentType.Stock == 'stock'
    
    def test_instrument_type_creation(self):
        """Test creating InstrumentType instances."""
        forex_type = InstrumentType('forex')
        assert forex_type == InstrumentType.Forex
        
        future_type = InstrumentType('future')
        assert future_type == InstrumentType.Future
        
        stock_type = InstrumentType('stock')
        assert stock_type == InstrumentType.Stock


class TestInstrumentConfig:
    """Test InstrumentConfig class."""
    
    def test_instrument_config_basic_initialization(self):
        """Test basic InstrumentConfig initialization."""
        config = InstrumentConfig(
            asset_class='stock',
            name='Apple Inc',
            code='AAPL'
        )
        
        assert config.name == 'Apple Inc'
        assert config.code == 'AAPL'
        assert config.asset_class == InstrumentType.Stock
        assert config.periods is None
        assert config.cycle is None
        assert config.days_count == 0  # Default for non-futures
    
    def test_instrument_config_with_all_parameters(self):
        """Test InstrumentConfig with all parameters."""
        tick_date = datetime(2024, 1, 1, tzinfo=pytz.UTC)
        start_date = datetime(2020, 1, 1, tzinfo=pytz.timezone('America/Chicago'))
        
        config = InstrumentConfig(
            asset_class='future',
            name='Gold Future',
            code='GC',
            tick_date=tick_date,
            start_date=start_date,
            periods='1d,1h',
            cycle='HMUZ',
            days_count=180
        )
        
        assert config.name == 'Gold Future'
        assert config.code == 'GC'
        assert config.asset_class == InstrumentType.Future
        assert config.cycle == 'HMUZ'
        assert config.days_count == 180
        # tick_date should be adjusted 90 days into future
        expected_tick = tick_date + timedelta(days=90)
        assert config.tick_date == expected_tick
        assert config.start_date == start_date
    
    def test_instrument_config_future_default_duration(self):
        """Test that futures get default duration."""
        config = InstrumentConfig(
            asset_class='future',
            name='Test Future',
            code='TEST'
        )
        
        assert config.days_count == DEFAULT_CONTRACT_DURATION_IN_DAYS
        assert config.asset_class == InstrumentType.Future
    
    def test_instrument_config_str_representation(self):
        """Test string representation of InstrumentConfig."""
        with patch('vortex.models.period.Period.get_periods_from_str', return_value=['1d', '1h']):
            config = InstrumentConfig(
                asset_class='stock',
                name='Apple',
                code='AAPL',
                periods='1d,1h'
            )
            
            str_repr = str(config)
            assert 'Apple' in str_repr
            assert 'AAPL' in str_repr
    
    def test_instrument_config_timezone_setup(self):
        """Test that timezone is properly set."""
        config = InstrumentConfig(
            asset_class='stock',
            name='Test',
            code='TEST'
        )
        
        assert config.tz == pytz.timezone('America/Chicago')
    
    def test_instrument_config_default_start_date(self):
        """Test default start date when not provided."""
        config = InstrumentConfig(
            asset_class='stock',
            name='Test',
            code='TEST'
        )
        
        expected_start = datetime(year=1980, month=1, day=1, tzinfo=pytz.timezone('America/Chicago'))
        assert config.start_date == expected_start
    
    def test_instrument_type_validation(self):
        """Test that invalid instrument types raise errors."""
        with pytest.raises(ValueError):
            InstrumentConfig(
                asset_class='invalid_type',
                name='Test',
                code='TEST'
            )
    
    @patch('builtins.open')
    def test_load_from_json_file_not_found(self, mock_open_func):
        """Test loading when file doesn't exist."""
        mock_open_func.side_effect = FileNotFoundError("File not found")
        
        with pytest.raises(FileNotFoundError):
            InstrumentConfig.load_from_json('nonexistent.json')
    
    @patch('json.load')
    @patch('builtins.open')
    def test_load_from_json_invalid_json(self, mock_open_func, mock_json_load):
        """Test loading with invalid JSON."""
        mock_json_load.side_effect = json.JSONDecodeError("Invalid", "doc", 0)
        
        with pytest.raises(json.JSONDecodeError):
            InstrumentConfig.load_from_json('invalid.json')


class TestDefaultConstant:
    """Test default constant values."""
    
    def test_default_contract_duration(self):
        """Test default contract duration constant."""
        assert isinstance(DEFAULT_CONTRACT_DURATION_IN_DAYS, int)
        assert DEFAULT_CONTRACT_DURATION_IN_DAYS > 0


class TestInstrumentConfigEdgeCases:
    """Test edge cases for InstrumentConfig."""
    
    def test_none_tick_date_handling(self):
        """Test handling when tick_date is None."""
        config = InstrumentConfig(
            asset_class='stock',
            name='Test',
            code='TEST',
            tick_date=None
        )
        
        assert config.tick_date is None
    
    def test_periods_string_parsing(self):
        """Test periods string is properly parsed."""
        with patch('vortex.models.period.Period.get_periods_from_str') as mock_parse:
            mock_parse.return_value = ['1d', '1h', '5m']
            
            config = InstrumentConfig(
                asset_class='stock',
                name='Test',
                code='TEST',
                periods='1d,1h,5m'
            )
            
            mock_parse.assert_called_once_with('1d,1h,5m')
            assert config.periods == ['1d', '1h', '5m']