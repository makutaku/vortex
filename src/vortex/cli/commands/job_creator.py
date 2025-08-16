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
    # Handle both dict and object configs
    periods = None
    if isinstance(config, dict):
        periods = config.get('periods')
    elif hasattr(config, 'periods'):
        periods = config.periods
    
    if periods:
        # If config has periods, parse them
        if isinstance(periods, str):
            # Split comma-separated string periods
            period_strings = [p.strip() for p in periods.split(',')]
            return [Period(p) for p in period_strings if p]
        elif isinstance(periods, list):
            return [Period(p) for p in periods]
    
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
    
    # Extract contract configuration - handle both dict and object configs
    if isinstance(config, dict):
        futures_code = config.get('code', symbol)
        cycle = config.get('cycle', '')
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
        cycle = getattr(config, 'cycle', '')
        tick_date = getattr(config, 'tick_date', datetime.now(tz))
        days_count = getattr(config, 'days_count', 365)
    
    # Parse cycle field to get all contract months (roll_cycle)
    # e.g., "GZ" = ['G', 'Z'] (February and December)
    roll_cycle = []
    if cycle:
        # Treat cycle as a string of month codes
        roll_cycle = [char for char in cycle if char.isalpha()]
    
    # If no cycle specified, default to December
    if not roll_cycle:
        roll_cycle = ['Z']
    
    # Generate all year/month combinations within date range (like original system)
    from vortex.utils.utils import generate_year_month_tuples
    from datetime import timedelta
    
    # Add days_count to end date to include contracts that may expire in the future
    # but have prices today
    future_end_date = end_date + timedelta(days=days_count)
    year_month_gen = generate_year_month_tuples(start_date, future_end_date)
    
    # Create jobs for each year/month combination that matches our roll cycle
    for year, month in year_month_gen:
        month_code = Future.get_code_for_month(month)
        if month_code in roll_cycle:
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
                    logging.debug(f"Created {len(instrument_jobs)} futures jobs for {symbol}{month_code}{Future.get_code_for_year(year)} {period}")
                except Exception as e:
                    logging.warning(f"Failed to create futures jobs for {symbol}{month_code}{Future.get_code_for_year(year)} {period}: {e}")
                    continue
    
    logging.info(f"Created {len(jobs)} total futures jobs for {symbol} across multiple years and {len(roll_cycle)} contract months: {roll_cycle}")
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
            # Show instrument type to help debug classification issues
            instrument_type = instrument.__class__.__name__.lower()
            logging.debug(f"Created {len(instrument_jobs)} {instrument_type} jobs for {symbol} {period}")
        except Exception as e:
            logging.warning(f"Failed to create jobs for {symbol} {period}: {e}")
            continue
    
    # Add summary logging for non-futures instruments like futures have
    if jobs and hasattr(jobs[0], 'instrument'):
        instrument_type = jobs[0].instrument.__class__.__name__.lower()
        total_periods = len(set(job.period for job in jobs))
        logging.info(f"Created {len(jobs)} total {instrument_type} jobs for {symbol} across {total_periods} periods")
    
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
            # ERROR: This method should NOT be used for futures!
            # Futures should use _create_futures_jobs() to properly handle all contract months.
            raise ValueError(
                f"_create_instrument_from_config should not be used for futures. "
                f"Use _create_futures_jobs() instead to properly handle all contract months in cycle."
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