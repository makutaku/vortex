"""
Download job creation logic for download commands.

Extracted from download.py to implement single responsibility principle.
Handles creation of download jobs for different instrument types and periods.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

from vortex.models.future import Future
from vortex.models.stock import Stock
from vortex.models.forex import Forex
from vortex.models.period import Period


def get_periods_for_symbol(config) -> List:
    """Get periods for symbol based on configuration."""
    if hasattr(config, 'periods') and config.periods:
        # If config has periods, parse them
        if isinstance(config.periods, str):
            return [Period(config.periods)]
        elif isinstance(config.periods, list):
            return [Period(p) for p in config.periods]
    
    # Default to daily
    return [Period('1d')]


def create_jobs_using_downloader_logic(downloader, symbol: str, config, periods: List, 
                                     start_date: datetime, end_date: datetime):
    """Create download jobs using downloader's logic for instrument type detection."""
    import pytz
    
    # Get timezone from config or use default
    if hasattr(config, 'timezone') and config.timezone:
        tz = pytz.timezone(config.timezone)
    else:
        tz = pytz.UTC
    
    # Try to determine instrument type from symbol or config
    if hasattr(config, 'asset_class') and config.asset_class:
        if config.asset_class.lower() in ['future', 'futures']:
            return _create_futures_jobs(downloader, symbol, config, periods, start_date, end_date, tz)
        else:
            # For stocks, forex, or other types
            return _create_simple_instrument_jobs(downloader, symbol, config, periods, start_date, end_date, tz)
    else:
        # No asset class specified, try to infer or default to simple instrument
        return _create_simple_instrument_jobs(downloader, symbol, config, periods, start_date, end_date, tz)


def _create_futures_jobs(downloader, symbol: str, config, periods: List, 
                        start_date: datetime, end_date: datetime, tz):
    """Create jobs for futures instruments with contract-specific logic."""
    jobs = []
    
    # Create Future instrument
    future = Future(
        symbol=symbol,
        exchange=getattr(config, 'exchange', 'CME'),  # Default exchange
        cycle=getattr(config, 'cycle', None),
        tick_date=getattr(config, 'tick_date', None)
    )
    
    for period in periods:
        try:
            # Use downloader's job creation logic
            instrument_jobs = downloader.create_jobs(future, period, start_date, end_date)
            jobs.extend(instrument_jobs)
            logging.debug(f"Created {len(instrument_jobs)} futures jobs for {symbol} {period}")
        except Exception as e:
            logging.warning(f"Failed to create futures jobs for {symbol} {period}: {e}")
            continue
    
    return jobs


def _create_simple_instrument_jobs(downloader, symbol: str, config, periods: List, 
                                  start_date: datetime, end_date: datetime, tz):
    """Create jobs for simple instruments (stocks, forex, etc.)."""
    jobs = []
    
    # Create appropriate instrument based on config
    instrument = _create_instrument_from_config(symbol, config)
    
    for period in periods:
        try:
            # Use downloader's job creation logic
            instrument_jobs = downloader.create_jobs(instrument, period, start_date, end_date)
            jobs.extend(instrument_jobs)
            logging.debug(f"Created {len(instrument_jobs)} jobs for {symbol} {period}")
        except Exception as e:
            logging.warning(f"Failed to create jobs for {symbol} {period}: {e}")
            continue
    
    return jobs


def _create_instrument_from_config(symbol: str, config):
    """Create appropriate instrument instance based on configuration."""
    if hasattr(config, 'asset_class') and config.asset_class:
        asset_class = config.asset_class.lower()
        
        if asset_class in ['stock', 'stocks', 'equity']:
            return Stock(
                symbol=symbol,
                exchange=getattr(config, 'exchange', 'NASDAQ'),
                tick_date=getattr(config, 'tick_date', None)
            )
        elif asset_class in ['forex', 'fx', 'currency']:
            return Forex(
                symbol=symbol,
                exchange=getattr(config, 'exchange', 'FX'),
                tick_date=getattr(config, 'tick_date', None)
            )
        elif asset_class in ['future', 'futures']:
            return Future(
                symbol=symbol,
                exchange=getattr(config, 'exchange', 'CME'),
                cycle=getattr(config, 'cycle', None),
                tick_date=getattr(config, 'tick_date', None)
            )
    
    # Default to Stock if no asset class specified
    return Stock(
        symbol=symbol,
        exchange='NASDAQ',
        tick_date=None
    )


def _to_timezone_aware(dt: datetime, tz):
    """Convert datetime to timezone-aware if needed."""
    import pytz
    
    if dt.tzinfo is None:
        if isinstance(tz, str):
            tz = pytz.timezone(tz)
        return tz.localize(dt)
    return dt