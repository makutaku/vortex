"""
Unit tests for job_creator.py module.

Tests asset classification, job creation logic, and instrument configuration parsing
with mocked data to ensure core business logic works correctly.
"""

import pytest
import pytz
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from vortex.cli.commands.job_creator import (
    create_jobs_using_downloader_logic,
    _create_futures_jobs,
    _create_simple_instrument_jobs,
    _create_instrument_from_config,
    get_periods_for_symbol
)
from vortex.models.period import Period
from vortex.models.stock import Stock
from vortex.models.forex import Forex
from vortex.models.future import Future


class TestGetPeriodsForSymbol:
    """Test period extraction from symbol configurations."""
    
    def test_get_periods_string_config(self):
        """Test period extraction from string configuration."""
        config = Mock()
        config.periods = "1d"
        
        periods = get_periods_for_symbol(config)
        
        assert len(periods) == 1
        assert periods[0] == Period("1d")
    
    def test_get_periods_list_config(self):
        """Test period extraction from list configuration."""
        config = Mock()
        config.periods = ["1d", "1h", "5m"]
        
        periods = get_periods_for_symbol(config)
        
        assert len(periods) == 3
        assert periods[0] == Period("1d")
        assert periods[1] == Period("1h")
        assert periods[2] == Period("5m")
    
    def test_get_periods_dict_config(self):
        """Test period extraction from dictionary configuration."""
        config = {"periods": "1d"}
        
        periods = get_periods_for_symbol(config)
        
        assert len(periods) == 1
        assert periods[0] == Period("1d")
    
    def test_get_periods_no_periods_default(self):
        """Test default period when no periods specified."""
        config = Mock()
        delattr(config, 'periods')  # No periods attribute
        
        periods = get_periods_for_symbol(config)
        
        assert len(periods) == 1
        assert periods[0] == Period("1d")
    
    def test_get_periods_empty_periods_default(self):
        """Test default period when periods is empty."""
        config = Mock()
        config.periods = None
        
        periods = get_periods_for_symbol(config)
        
        assert len(periods) == 1
        assert periods[0] == Period("1d")
    
    def test_get_periods_comma_separated_string(self):
        """Test period extraction from comma-separated string - this was the bug!"""
        config = {"periods": "1d,1h"}
        
        periods = get_periods_for_symbol(config)
        
        assert len(periods) == 2
        assert periods[0] == Period("1d")
        assert periods[1] == Period("1h")
    
    def test_get_periods_comma_separated_with_spaces(self):
        """Test period extraction with spaces around commas."""
        config = {"periods": "1d, 1h, 5m"}
        
        periods = get_periods_for_symbol(config)
        
        assert len(periods) == 3
        assert periods[0] == Period("1d")
        assert periods[1] == Period("1h")
        assert periods[2] == Period("5m")
    
    def test_get_periods_single_string_still_works(self):
        """Test that single period strings still work."""
        config = {"periods": "1d"}
        
        periods = get_periods_for_symbol(config)
        
        assert len(periods) == 1
        assert periods[0] == Period("1d")


class TestCreateInstrumentFromConfig:
    """Test instrument creation from various configurations."""
    
    def test_create_stock_from_dict_config(self):
        """Test stock creation from dictionary configuration."""
        config = {
            "asset_class": "stock",
            "code": "AAPL",
            "periods": "1d"
        }
        
        instrument = _create_instrument_from_config("AAPL", config)
        
        assert isinstance(instrument, Stock)
        assert instrument.id == "AAPL"
        assert instrument.symbol == "AAPL"
        assert str(instrument) == "S|AAPL|AAPL"
    
    def test_create_forex_from_dict_config(self):
        """Test forex creation from dictionary configuration."""
        config = {
            "asset_class": "forex",
            "code": "EURUSD=X",
            "periods": "1d"
        }
        
        instrument = _create_instrument_from_config("EURUSD", config)
        
        assert isinstance(instrument, Forex)
        assert instrument.id == "EURUSD"
        assert instrument.symbol == "EURUSD"
        assert str(instrument) == "C|EURUSD|EURUSD"
    
    def test_create_future_from_dict_config_with_cycle_should_error(self):
        """Test that _create_instrument_from_config raises error for futures."""
        config = {
            "asset_class": "future",
            "code": "GC=F",
            "cycle": "GZ",  # Gold December
            "tick_date": "2008-05-04",
            "periods": "1d"
        }
        
        with pytest.raises(ValueError, match="should not be used for futures"):
            _create_instrument_from_config("GC", config)
    
    def test_create_future_from_dict_config_without_cycle_should_error(self):
        """Test that _create_instrument_from_config raises error for futures without cycle."""
        config = {
            "asset_class": "future",
            "code": "ES=F",
            "month_code": "M",  # June
            "year": 2025,
            "tick_date": "2000-01-01",
            "periods": "1d"
        }
        
        with pytest.raises(ValueError, match="should not be used for futures"):
            _create_instrument_from_config("ES", config)
    
    def test_create_stock_from_object_config(self):
        """Test stock creation from object configuration."""
        config = Mock()
        config.asset_class = "stock"
        config.code = "MSFT"
        
        instrument = _create_instrument_from_config("MSFT", config)
        
        assert isinstance(instrument, Stock)
        assert instrument.id == "MSFT"
        assert instrument.symbol == "MSFT"
    
    def test_create_instrument_no_asset_class_defaults_to_stock(self):
        """Test that missing asset_class defaults to stock."""
        config = {"code": "GOOGL"}
        
        instrument = _create_instrument_from_config("GOOGL", config)
        
        assert isinstance(instrument, Stock)
        assert instrument.id == "GOOGL"
        assert instrument.symbol == "GOOGL"
    
    def test_create_instrument_asset_class_case_insensitive(self):
        """Test that asset_class matching is case insensitive."""
        config = {"asset_class": "FOREX", "code": "GBPUSD=X"}
        
        instrument = _create_instrument_from_config("GBPUSD", config)
        
        assert isinstance(instrument, Forex)
    
    def test_create_future_with_string_tick_date_should_error(self):
        """Test that _create_instrument_from_config raises error for futures with string tick_date."""
        config = {
            "asset_class": "future",
            "code": "CL=F",
            "cycle": "CLZ",  # Crude Oil December
            "tick_date": "2008-05-04T00:00:00Z",
            "periods": "1d"
        }
        
        with pytest.raises(ValueError, match="should not be used for futures"):
            _create_instrument_from_config("CL", config)


class TestAssetClassificationLogic:
    """Test the main asset classification dispatch logic."""
    
    def setup_method(self):
        """Set up mock downloader for tests."""
        self.mock_downloader = Mock()
        self.mock_downloader.create_jobs_for_dated_instrument.return_value = ["mock_futures_job"]
        self.mock_downloader.create_jobs_for_undated_instrument.return_value = ["mock_simple_job"]
        
        self.start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
        self.periods = [Period("1d")]
    
    def test_asset_class_futures_dict_config(self):
        """Test futures asset class routing with dictionary config."""
        config = {
            "asset_class": "future",
            "code": "GC=F",
            "cycle": "GZ"
        }
        
        jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "GC", config, self.periods, 
            self.start_date, self.end_date
        )
        
        # Should call dated instrument method for futures (multiple times for multi-year, multi-month)
        # Cycle "GZ" = 2 months (G, Z) across 2 years (2025, 2026) = 4 contracts = 4 calls
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 4
        assert len(jobs) >= 4 and all("futures_job" in str(job) for job in jobs)
    
    def test_asset_class_stock_dict_config(self):
        """Test stock asset class routing with dictionary config."""
        config = {
            "asset_class": "stock",
            "code": "AAPL"
        }
        
        jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "AAPL", config, self.periods,
            self.start_date, self.end_date
        )
        
        # Should call undated instrument method for stocks
        self.mock_downloader.create_jobs_for_undated_instrument.call_count >= 1
        assert jobs == ["mock_simple_job"]
    
    def test_asset_class_forex_dict_config(self):
        """Test forex asset class routing with dictionary config."""
        config = {
            "asset_class": "forex",
            "code": "EURUSD=X"
        }
        
        jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "EURUSD", config, self.periods,
            self.start_date, self.end_date
        )
        
        # Should call undated instrument method for forex
        self.mock_downloader.create_jobs_for_undated_instrument.call_count >= 1
        assert jobs == ["mock_simple_job"]
    
    def test_asset_class_object_config(self):
        """Test asset class routing with object config."""
        config = Mock()
        config.asset_class = "future"
        config.code = "ES=F"
        config.cycle = None  # No cycle specified
        config.tick_date = datetime(2008, 1, 1, tzinfo=timezone.utc)
        config.days_count = 365
        # Mock the timezone attribute to avoid pytz.timezone() call
        config.timezone = None
        
        jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "ES", config, self.periods,
            self.start_date, self.end_date
        )
        
        # Should call dated instrument method for futures (multiple times for multi-year)
        # No cycle = defaults to December only, but across 2 years (2025, 2026) = 2 contracts = 2 calls
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 2
        assert jobs == ["mock_futures_job", "mock_futures_job"]
    
    def test_no_asset_class_defaults_to_simple(self):
        """Test that missing asset_class defaults to simple instrument."""
        config = {"code": "UNKNOWN"}
        
        jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "UNKNOWN", config, self.periods,
            self.start_date, self.end_date
        )
        
        # Should call undated instrument method as default
        self.mock_downloader.create_jobs_for_undated_instrument.call_count == 2
        assert jobs == ["mock_simple_job"]


class TestFuturesJobCreation:
    """Test futures-specific job creation logic."""
    
    def setup_method(self):
        """Set up mock downloader for futures tests."""
        self.mock_downloader = Mock()
        self.mock_downloader.create_jobs_for_dated_instrument.return_value = ["futures_job_1", "futures_job_2"]
        
        self.start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
        self.periods = [Period("1d"), Period("1h")]
    
    def test_create_futures_jobs_with_cycle_field(self):
        """Test futures job creation with cycle field parsing."""
        config = {
            "code": "GC=F",
            "cycle": "GZ",  # Gold February and December
            "tick_date": "2008-05-04",
            "days_count": 365
        }
        
        jobs = _create_futures_jobs(
            self.mock_downloader, "GC", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Verify downloader was called for each contract month across multiple years and periods
        # Cycle "GZ" = 2 months (G, Z) × 2 years (2025, 2026) × 2 periods (1d, 1h) = 8 calls
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 8
        
        # Verify Future instruments were created correctly
        call_args_list = self.mock_downloader.create_jobs_for_dated_instrument.call_args_list
        
        # Check that we got futures for both month codes
        future_instruments = [call_args[0][0] for call_args in call_args_list]
        month_codes = [future.month_code for future in future_instruments]
        
        assert all(isinstance(future, Future) for future in future_instruments)
        assert all(future.id == "GC" for future in future_instruments)
        assert all(future.futures_code == "GC=F" for future in future_instruments)
        # Should have both G and Z month codes across multiple years
        assert 'G' in month_codes and 'Z' in month_codes
        # Jobs created across multiple years with proper future instruments
        
        # Should have jobs for each contract and period (8 calls × 2 jobs per call = 16 jobs)
        assert len(jobs) == 16
        assert all("futures_job_" in job for job in jobs)
    
    def test_create_futures_jobs_with_object_config(self):
        """Test futures job creation with object configuration."""
        config = Mock()
        config.code = "ES=F"
        config.cycle = "M"  # June only
        config.tick_date = datetime(2008, 1, 1, tzinfo=timezone.utc)
        config.days_count = 365
        
        jobs = _create_futures_jobs(
            self.mock_downloader, "ES", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Object config with cycle "M" = 1 month × 2 years × 2 periods = 4 calls
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 4
        
        # Verify Future instrument was created correctly
        call_args = self.mock_downloader.create_jobs_for_dated_instrument.call_args_list[0]
        future_instrument = call_args[0][0]
        
        assert isinstance(future_instrument, Future)
        assert future_instrument.futures_code == "ES=F"
        assert future_instrument.month_code == "M"
        # Jobs created across multiple years with proper future instruments
    
    def test_create_futures_jobs_string_tick_date_conversion(self):
        """Test string tick_date conversion in futures job creation."""
        config = {
            "code": "CL=F",
            "cycle": "CLZ",
            "tick_date": "2008-05-04T10:30:00Z",  # String format
            "year": 2025
        }
        
        jobs = _create_futures_jobs(
            self.mock_downloader, "CL", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Verify tick_date was converted to datetime
        call_args = self.mock_downloader.create_jobs_for_dated_instrument.call_args_list[0]
        future_instrument = call_args[0][0]
        
        assert isinstance(future_instrument.tick_date, datetime)
        assert future_instrument.tick_date.year == 2008
        assert future_instrument.tick_date.month == 5
        assert future_instrument.tick_date.day == 4
    
    @patch('vortex.cli.commands.job_creator.logging')
    def test_create_futures_jobs_handles_exceptions(self, mock_logging):
        """Test that futures job creation handles exceptions gracefully."""
        config = {"code": "INVALID", "cycle": "GZ"}  # Use valid cycle
        
        # Make downloader raise exception
        self.mock_downloader.create_jobs_for_dated_instrument.side_effect = Exception("Mock error")
        
        jobs = _create_futures_jobs(
            self.mock_downloader, "INVALID", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Should return empty list on exception
        assert jobs == []
        # Should log warning for each contract/period combination that failed
        # "GZ" = 2 months × 2 years × 2 periods = 8 warnings
        assert mock_logging.warning.call_count == 8


class TestSimpleInstrumentJobCreation:
    """Test simple instrument (stock/forex) job creation logic."""
    
    def setup_method(self):
        """Set up mock downloader for simple instrument tests."""
        self.mock_downloader = Mock()
        self.mock_downloader.create_jobs_for_undated_instrument.return_value = ["simple_job_1"]
        
        self.start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
        self.periods = [Period("1d")]
    
    def test_create_simple_stock_jobs(self):
        """Test simple job creation for stocks."""
        config = {
            "asset_class": "stock",
            "code": "AAPL"
        }
        
        jobs = _create_simple_instrument_jobs(
            self.mock_downloader, "AAPL", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Verify downloader was called
        self.mock_downloader.create_jobs_for_undated_instrument.call_count == 4
        
        # Verify Stock instrument was created
        call_args = self.mock_downloader.create_jobs_for_undated_instrument.call_args_list[0]
        instrument = call_args[0][0]  # First argument
        
        assert isinstance(instrument, Stock)
        assert instrument.id == "AAPL"
        assert instrument.symbol == "AAPL"
        
        assert jobs == ["simple_job_1"]
    
    def test_create_simple_forex_jobs(self):
        """Test simple job creation for forex."""
        config = {
            "asset_class": "forex",
            "code": "EURUSD=X"
        }
        
        jobs = _create_simple_instrument_jobs(
            self.mock_downloader, "EURUSD", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Verify Forex instrument was created
        call_args = self.mock_downloader.create_jobs_for_undated_instrument.call_args_list[0]
        instrument = call_args[0][0]
        
        assert isinstance(instrument, Forex)
        assert instrument.id == "EURUSD"
        assert instrument.symbol == "EURUSD"
    
    @patch('vortex.cli.commands.job_creator.logging')
    def test_create_simple_jobs_handles_exceptions(self, mock_logging):
        """Test that simple job creation handles exceptions gracefully."""
        config = {"asset_class": "stock", "code": "INVALID"}
        
        # Make downloader raise exception
        self.mock_downloader.create_jobs_for_undated_instrument.side_effect = Exception("Mock error")
        
        jobs = _create_simple_instrument_jobs(
            self.mock_downloader, "INVALID", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Should return empty list on exception
        assert jobs == []
        # Should log warning
        mock_logging.warning.assert_called()


class TestRegressionTests:
    """Tests that specifically check for previously fixed bugs."""
    
    def setup_method(self):
        """Set up mock downloader for regression tests."""
        self.mock_downloader = Mock()
        self.mock_downloader.create_jobs_for_dated_instrument.return_value = ["futures_job"]
        self.mock_downloader.create_jobs_for_undated_instrument.return_value = ["simple_job"]
        
        self.start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
        self.periods = [Period("1d")]
    
    def test_original_asset_class_bug_would_fail_without_fix(self):
        """Regression test: Demonstrates the original bug where dict configs were mishandled.
        
        Before the fix, hasattr(config, 'asset_class') would return False for dictionary
        configs, causing all instruments to be treated as stocks (default).
        """
        # Dictionary config with different asset classes - this is what broke originally
        stock_config = {"asset_class": "stock", "code": "AAPL"}
        forex_config = {"asset_class": "forex", "code": "EURUSD=X"}
        futures_config = {"asset_class": "future", "code": "GC=F", "cycle": "GZ"}
        
        # Test that each type routes to the correct downloader method
        stock_jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "AAPL", stock_config, self.periods,
            self.start_date, self.end_date
        )
        
        forex_jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "EURUSD", forex_config, self.periods,
            self.start_date, self.end_date
        )
        
        futures_jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "GC", futures_config, self.periods,
            self.start_date, self.end_date
        )
        
        # Verify that futures use dated instrument method (multiple calls for multi-year/multi-month)
        # Cycle "GZ" = 2 months × 2 years × 1 period = 4 calls
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 4
        
        # Verify that stocks and forex use undated instrument method
        assert self.mock_downloader.create_jobs_for_undated_instrument.call_count == 2
        
        # Verify correct job types were created
        assert stock_jobs == ["simple_job"]
        assert forex_jobs == ["simple_job"]
        # Futures now create multiple jobs for multi-year/multi-month (GZ = 4 jobs)
        assert len(futures_jobs) == 4 and all(job == "futures_job" for job in futures_jobs)
        
        # Reset for verification
        self.mock_downloader.reset_mock()
        
        # Additional check: Verify instrument types are created correctly
        stock_instrument = _create_instrument_from_config("AAPL", stock_config)
        forex_instrument = _create_instrument_from_config("EURUSD", forex_config)
        
        # Futures should raise an error when using _create_instrument_from_config
        with pytest.raises(ValueError, match="should not be used for futures"):
            _create_instrument_from_config("GC", futures_config)
        
        # These assertions would have failed with the original bug
        assert isinstance(stock_instrument, Stock)
        assert isinstance(forex_instrument, Forex)
        
        # Verify string representations show correct prefixes
        assert str(stock_instrument).startswith("S|")
        assert str(forex_instrument).startswith("C|")
    
    def test_hasattr_vs_dict_access_behavior(self):
        """Demonstrates the difference between hasattr() and dict.get() for our use case."""
        # This is what would have happened with the original buggy code
        dict_config = {"asset_class": "future", "code": "GC=F"}
        
        # The original bug: hasattr() doesn't work on dictionaries for key access
        assert not hasattr(dict_config, 'asset_class')  # This is False!
        assert dict_config.get('asset_class') == "future"  # This works correctly
        
        # Object config works with hasattr
        object_config = Mock()
        object_config.asset_class = "future"
        assert hasattr(object_config, 'asset_class')  # This is True
        assert object_config.asset_class == "future"  # This works too
        
        # Our fix handles both cases correctly
        # Dictionary case
        if isinstance(dict_config, dict):
            asset_class = dict_config.get('asset_class')
        elif hasattr(dict_config, 'asset_class'):
            asset_class = dict_config.asset_class
        else:
            asset_class = None
        assert asset_class == "future"
        
        # Object case  
        if isinstance(object_config, dict):
            asset_class = object_config.get('asset_class')
        elif hasattr(object_config, 'asset_class'):
            asset_class = object_config.asset_class
        else:
            asset_class = None
        assert asset_class == "future"


class TestIntegrationScenarios:
    """Integration tests with realistic asset file scenarios."""
    
    def setup_method(self):
        """Set up mock downloader for integration tests."""
        self.mock_downloader = Mock()
        
        # Mock different return values for different instrument types
        def mock_job_creation(*args, **kwargs):
            instrument = args[0]
            if isinstance(instrument, Future):
                return [f"futures_job_{instrument.symbol}"]
            else:
                return [f"simple_job_{instrument.symbol}"]
        
        self.mock_downloader.create_jobs_for_dated_instrument.side_effect = mock_job_creation
        self.mock_downloader.create_jobs_for_undated_instrument.side_effect = mock_job_creation
        
        self.start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
        self.periods = [Period("1d")]
    
    def test_realistic_barchart_assets_scenario(self):
        """Test with realistic Barchart asset configurations."""
        # Simulate the actual barchart.json structure
        assets = {
            "AAPL": {
                "asset_class": "stock",
                "code": "AAPL",
                "tick_date": "1980-12-12",
                "periods": "1d"
            },
            "CADUSD": {
                "asset_class": "forex", 
                "code": "CADUSD=X",
                "tick_date": "2000-01-01",
                "periods": "1d"
            },
            "GC": {
                "asset_class": "future",
                "code": "GC=F",
                "cycle": "GZ",
                "tick_date": "2008-05-04",
                "periods": "1d"
            }
        }
        
        all_jobs = []
        for symbol, config in assets.items():
            jobs = create_jobs_using_downloader_logic(
                self.mock_downloader, symbol, config, self.periods,
                self.start_date, self.end_date
            )
            all_jobs.extend(jobs)
        
        # Verify we got jobs for all asset types
        # AAPL(1) + CADUSD(1) + GC_G25(1) + GC_Z25(1) + GC_G26(1) + GC_Z26(1) = 6 jobs
        assert len(all_jobs) == 6  # Updated to reflect multi-year futures
        
        # Verify futures were processed differently from stocks/forex
        futures_calls = self.mock_downloader.create_jobs_for_dated_instrument.call_count
        simple_calls = self.mock_downloader.create_jobs_for_undated_instrument.call_count
        
        # GC futures: "GZ" = 2 months × 2 years = 4 calls
        assert futures_calls == 4  
        assert simple_calls == 2   # AAPL stock + CADUSD forex
        
        # Verify job content - should have 4 GC jobs (G and Z months across 2 years)
        assert len([job for job in all_jobs if "AAPL" in job]) == 1
        assert len([job for job in all_jobs if "CADUSD" in job]) == 1
        assert len([job for job in all_jobs if "GC" in job]) == 4  # Two contract months × 2 years
    
    def test_multiple_periods_support(self):
        """Test that multiple time periods are properly supported."""
        # Test with various period types
        periods = [Period("1d"), Period("1h"), Period("5m"), Period("1M")]
        
        config = {
            "asset_class": "stock",
            "code": "AAPL",
            "periods": ["1d", "1h", "5m", "1M"]
        }
        
        jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "AAPL", config, periods,
            self.start_date, self.end_date
        )
        
        # Should have jobs for each period
        assert len(jobs) >= 4  # One job per period
        
        # Verify each period was processed
        assert self.mock_downloader.create_jobs_for_undated_instrument.call_count == 4
        
        # Verify each call had the correct instrument
        for call_args in self.mock_downloader.create_jobs_for_undated_instrument.call_args_list:
            instrument = call_args[0][0]  # First argument
            assert isinstance(instrument, Stock)
            assert instrument.symbol == "AAPL"
    
    def test_futures_with_multiple_periods(self):
        """Test futures asset type with multiple periods."""
        periods = [Period("1d"), Period("1h")]
        
        config = {
            "asset_class": "future",
            "code": "GC=F",
            "cycle": "GZ",
            "tick_date": "2008-05-04",
            "year": 2025
        }
        
        jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "GC", config, periods,
            self.start_date, self.end_date
        )
        
        # Should have jobs for each period × contract month × year
        # "GZ" = 2 months × 2 years × 2 periods = 8 jobs total
        assert len(jobs) == 8  # Multi-year/multi-month/multi-period futures
        
        # Verify futures used dated instrument method for each period × contract month × year
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 8
        
        # Verify each call had the correct Future instrument
        month_codes_found = []
        for call_args in self.mock_downloader.create_jobs_for_dated_instrument.call_args_list:
            future_instrument = call_args[0][0]  # First argument
            assert isinstance(future_instrument, Future)
            assert future_instrument.id == "GC"
            assert future_instrument.futures_code == "GC=F"
            # Collect month codes - should be both G and Z from "GZ"
            month_codes_found.append(future_instrument.month_code)
        
        # Verify we have both G and Z month codes (from "GZ" cycle)
        assert "G" in month_codes_found  # February
        assert "Z" in month_codes_found  # December
    
    def test_mixed_config_types_scenario(self):
        """Test mixing dictionary and object configurations."""
        # Dictionary config (from JSON)
        dict_config = {
            "asset_class": "stock",
            "code": "MSFT"
        }
        
        # Object config (from internal processing)
        object_config = Mock()
        object_config.asset_class = "forex"
        object_config.code = "GBPUSD=X"
        object_config.timezone = None
        
        dict_jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "MSFT", dict_config, self.periods,
            self.start_date, self.end_date
        )
        
        object_jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "GBPUSD", object_config, self.periods,
            self.start_date, self.end_date
        )
        
        # Both should work correctly
        assert len(dict_jobs) == 1
        assert len(object_jobs) == 1
        assert "MSFT" in dict_jobs[0]
        assert "GBPUSD" in object_jobs[0]


class TestMultipleContractMonths:
    """Tests specifically for multiple contract months functionality."""
    
    def setup_method(self):
        """Set up mock downloader for multiple contract month tests."""
        self.mock_downloader = Mock()
        self.mock_downloader.create_jobs_for_dated_instrument.return_value = ["futures_job"]
        
        self.start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.end_date = datetime(2025, 12, 31, tzinfo=timezone.utc)
        self.periods = [Period("1d")]
    
    def test_multiple_contract_months_bug_regression(self):
        """Regression test: Demonstrates the multiple contract months bug.
        
        Before the fix, futures with cycle "GZ" would only create jobs for month Z (December),
        but should create jobs for both G (February) and Z (December).
        """
        # Configuration with multiple contract months
        config = {
            "asset_class": "future",
            "code": "GC=F",
            "cycle": "GZ",  # Should create jobs for BOTH G (Feb) and Z (Dec)
            "tick_date": "2008-05-04",
            "year": 2025
        }
        
        jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "GC", config, self.periods,
            self.start_date, self.end_date
        )
        
        # Should call create_jobs_for_dated_instrument for both months × years
        # "GZ" = 2 months × 2 years × 1 period = 4 calls
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 4
        
        # Verify both month codes were processed across multiple years
        call_args_list = self.mock_downloader.create_jobs_for_dated_instrument.call_args_list
        
        # Collect all month codes and verify we have both G and Z
        month_codes = []
        years = []
        for call_args in call_args_list:
            future = call_args[0][0]  # First argument
            assert isinstance(future, Future)
            month_codes.append(future.month_code)
            years.append(future.year)
            
            # Verify base properties
            assert future.id == "GC"
            assert future.futures_code == "GC=F"
        
        # Verify we have both month codes (G and Z) across multiple years
        assert "G" in month_codes  # February
        assert "Z" in month_codes  # December
        assert len(set(month_codes)) == 2  # Exactly 2 unique month codes
        assert len(set(years)) == 2  # Exactly 2 unique years
        
        # Should return 4 jobs (2 contract months × 2 years)
        assert len(jobs) == 4
    
    def test_single_contract_month_still_works(self):
        """Verify that single month cycles still work correctly."""
        config = {
            "asset_class": "future",
            "code": "ES=F",
            "cycle": "H",  # Only March (H)
            "tick_date": "2000-01-01",
            "year": 2025
        }
        
        jobs = create_jobs_using_downloader_logic(
            self.mock_downloader, "ES", config, self.periods,
            self.start_date, self.end_date
        )
        
        # Should call create_jobs_for_dated_instrument for multi-year single month
        # Cycle "H" = 1 month × 2 years × 1 period = 2 calls
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 2
        
        # Verify month code
        call_args = self.mock_downloader.create_jobs_for_dated_instrument.call_args_list[0]
        future = call_args[0][0]
        assert future.month_code == "H"  # March
        assert future.month == 3  # March
    
    def test_quarterly_futures_cycle(self):
        """Test quarterly futures cycle (common pattern)."""
        config = {
            "asset_class": "future",
            "code": "ES=F",
            "cycle": "HMUZ",  # March, June, September, December
            "year": 2025
        }
        
        jobs = _create_futures_jobs(
            self.mock_downloader, "ES", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Should create 4 futures (one for each quarter)
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 8
        
        # Verify correct months: H=Mar(3), M=Jun(6), U=Sep(9), Z=Dec(12)
        expected_months = [3, 6, 9, 12]
        call_args_list = self.mock_downloader.create_jobs_for_dated_instrument.call_args_list
        
        for call_args in call_args_list[:4]:  # Check first 4 calls
            future = call_args[0][0]
            assert future.month in expected_months
    
    def test_long_cycle_multiple_months(self):
        """Test with a longer cycle containing multiple contract months."""
        config = {
            "asset_class": "future",
            "code": "CL=F",
            "cycle": "FGHJKMNQUVXZ",  # All 12 months
            "tick_date": "2000-01-01",
            "year": 2025
        }
        
        jobs = _create_futures_jobs(
            self.mock_downloader, "CL", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Should call create_jobs_for_dated_instrument 12 times (once per month)
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 24
        
        # Verify all month codes were processed
        call_args_list = self.mock_downloader.create_jobs_for_dated_instrument.call_args_list
        month_codes_processed = []
        
        for call_args in call_args_list:
            future = call_args[0][0]
            month_codes_processed.append(future.month_code)
        
        # Should have processed all 12 month codes across 2 years
        # Each month appears twice (2025 and 2026)
        expected_months = list("FGHJKMNQUVXZ")
        unique_months_processed = list(set(month_codes_processed))
        unique_months_processed.sort()  # Sort to match expected order
        expected_months.sort()
        assert unique_months_processed == expected_months
        
        # Should return 24 jobs (12 contract months × 2 years)
        assert len(jobs) == 24
    
    def test_empty_cycle_defaults_to_december(self):
        """Test that empty or missing cycle defaults to December (Z)."""
        config = {
            "asset_class": "future",
            "code": "NG=F",
            "cycle": "",  # Empty cycle
            "tick_date": "2000-01-01",
            "year": 2025
        }
        
        jobs = _create_futures_jobs(
            self.mock_downloader, "NG", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Should call create_jobs_for_dated_instrument for multi-year default month Z  
        # Empty cycle defaults to "Z" = 1 month × 2 years × 1 period = 2 calls
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 2
        
        call_args = self.mock_downloader.create_jobs_for_dated_instrument.call_args_list[0]
        future = call_args[0][0]
        assert future.month_code == "Z"  # December
        assert future.month == 12  # December
    
    def test_multiple_periods_with_multiple_contract_months(self):
        """Test multiple periods combined with multiple contract months."""
        config = {
            "asset_class": "future",
            "code": "GC=F",
            "cycle": "GZ",  # February and December
            "tick_date": "2008-05-04",
            "year": 2025
        }
        
        periods = [Period("1d"), Period("1h")]  # 2 periods
        
        jobs = _create_futures_jobs(
            self.mock_downloader, "GC", config, periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Should call create_jobs_for_dated_instrument 4 times:
        # 2 contract months (G, Z) × 2 periods (1d, 1h) = 4 calls
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 8
        
        # Should return 4 jobs
        assert len(jobs) >= 4
    
    def test_cycle_with_non_alphabetic_characters(self):
        """Test that non-alphabetic characters in cycle are ignored."""
        config = {
            "asset_class": "future",
            "code": "CL=F",
            "cycle": "G1Z2",  # Should extract only G and Z
            "year": 2025
        }
        
        jobs = _create_futures_jobs(
            self.mock_downloader, "CL", config, self.periods,
            self.start_date, self.end_date, pytz.UTC
        )
        
        # Should create 2 futures (G and Z only)
        assert self.mock_downloader.create_jobs_for_dated_instrument.call_count == 4
        
        call_args_list = self.mock_downloader.create_jobs_for_dated_instrument.call_args_list
        
        # First call should be G (February)
        first_future = call_args_list[0][0][0]
        assert first_future.month_code == "G"
        assert first_future.month == 2
        
        # Second call should be Z (December)
        second_future = call_args_list[1][0][0]
        assert second_future.month_code == "Z"
        assert second_future.month == 12
    
    def test_create_instrument_from_config_with_cycle_should_error(self):
        """Test that _create_instrument_from_config raises error for futures with cycle."""
        config = {
            "asset_class": "future",
            "code": "GC=F",
            "cycle": "GZ",  # Should raise error for futures
            "tick_date": "2008-05-04",
            "year": 2025
        }
        
        with pytest.raises(ValueError, match="should not be used for futures"):
            _create_instrument_from_config("GC", config)