"""
Download job creation logic for download commands.

Extracted from download.py to implement single responsibility principle.
Handles creation of download jobs for different instrument types and periods.
"""

import logging
from datetime import datetime, timezone
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
    # Handle both dict and object configs
    asset_class = None
    if isinstance(config, dict):
        asset_class = config.get('asset_class')
    elif hasattr(config, 'asset_class'):
        asset_class = config.asset_class
    
    if asset_class:
        if asset_class.lower() in ['future', 'futures']:
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
    
    # Create Future instrument - handle both dict and object configs
    if isinstance(config, dict):
        futures_code = config.get('code', symbol)
        
        # Handle cycle field (e.g., "GZ" = Gold, December)
        cycle = config.get('cycle', '')
        if cycle and len(cycle) >= 2:
            # Extract month code from cycle (last character)
            month_code = cycle[-1]  # 'Z' from 'GZ'
        else:
            month_code = config.get('month_code', 'Z')  # Default to December
        
        year = config.get('year', datetime.now().year)
        tick_date = config.get('tick_date', datetime.now(tz))
        days_count = config.get('days_count', 365)
        
        # Convert tick_date string to datetime if needed
        if isinstance(tick_date, str):
            try:
                tick_date = datetime.fromisoformat(tick_date.replace('Z', '+00:00'))
                if tick_date.tzinfo is None:
                    tick_date = tz.localize(tick_date)
            except ValueError:
                tick_date = datetime.now(tz)
    else:
        futures_code = getattr(config, 'code', symbol)
        year = getattr(config, 'year', datetime.now().year)
        month_code = getattr(config, 'month_code', 'Z')  # Default to December
        tick_date = getattr(config, 'tick_date', datetime.now(tz))
        days_count = getattr(config, 'days_count', 365)
    
    future = Future(
        id=symbol,
        futures_code=futures_code,
        year=year,
        month_code=month_code,
        tick_date=tick_date,
        days_count=days_count
    )
    
    for period in periods:
        try:
            # Use downloader's job creation logic for dated instruments (futures)
            # Ensure dates are timezone-aware
            tz_start_date = _to_timezone_aware(start_date, tz)
            tz_end_date = _to_timezone_aware(end_date, tz)
            instrument_jobs = downloader.create_jobs_for_dated_instrument(future, [period], tz_start_date, tz_end_date, tz)
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
            # Use downloader's job creation logic for undated instruments
            # Ensure dates are timezone-aware
            tz_start_date = _to_timezone_aware(start_date, tz)
            tz_end_date = _to_timezone_aware(end_date, tz)
            instrument_jobs = downloader.create_jobs_for_undated_instrument(
                instrument, tz_start_date, tz_end_date, [period], None
            )
            jobs.extend(instrument_jobs)
            logging.debug(f"Created {len(instrument_jobs)} jobs for {symbol} {period}")
        except Exception as e:
            logging.warning(f"Failed to create jobs for {symbol} {period}: {e}")
            continue
    
    return jobs


def _create_instrument_from_config(symbol: str, config):
    """Create appropriate instrument instance based on configuration."""
    # Handle both dict and object configs
    asset_class = None
    if isinstance(config, dict):
        asset_class = config.get('asset_class')
    elif hasattr(config, 'asset_class'):
        asset_class = config.asset_class
    
    if asset_class:
        asset_class = asset_class.lower()
        
        if asset_class in ['stock', 'stocks', 'equity']:
            return Stock(
                id=symbol,
                symbol=symbol
            )
        elif asset_class in ['forex', 'fx', 'currency']:
            return Forex(
                id=symbol,
                symbol=symbol
            )
        elif asset_class in ['future', 'futures']:
            # Future needs specific parameters - use dict-safe getters
            if isinstance(config, dict):
                futures_code = config.get('code', symbol)
                
                # Handle cycle field (e.g., "GZ" = Gold, December)
                cycle = config.get('cycle', '')
                if cycle and len(cycle) >= 2:
                    # Extract month code from cycle (last character)
                    month_code = cycle[-1]  # 'Z' from 'GZ'
                else:
                    month_code = config.get('month_code', 'Z')  # Default to December
                
                year = config.get('year', datetime.now().year)
                tick_date = config.get('tick_date', datetime.now(timezone.utc))
                days_count = config.get('days_count', 365)
                
                # Convert tick_date string to datetime if needed
                if isinstance(tick_date, str):
                    try:
                        tick_date = datetime.fromisoformat(tick_date.replace('Z', '+00:00'))
                        if tick_date.tzinfo is None:
                            tick_date = tick_date.replace(tzinfo=timezone.utc)
                    except ValueError:
                        tick_date = datetime.now(timezone.utc)
            else:
                futures_code = getattr(config, 'code', symbol)
                year = getattr(config, 'year', datetime.now().year)
                month_code = getattr(config, 'month_code', 'Z')  # Default to December
                tick_date = getattr(config, 'tick_date', datetime.now(timezone.utc))
                days_count = getattr(config, 'days_count', 365)
            
            return Future(
                id=symbol,
                futures_code=futures_code,
                year=year,
                month_code=month_code,
                tick_date=tick_date,
                days_count=days_count
            )
    
    # Default to Stock if no asset class specified
    return Stock(
        id=symbol,
        symbol=symbol
    )


def _to_timezone_aware(dt: datetime, tz):
    """Convert datetime to timezone-aware if needed."""
    import pytz
    
    if dt.tzinfo is None:
        if isinstance(tz, str):
            tz = pytz.timezone(tz)
        return tz.localize(dt)
    return dt