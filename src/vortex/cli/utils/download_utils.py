"""
Download utilities shared across CLI commands.

This module extracts shared download logic to prevent circular dependencies
between CLI command modules.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from vortex.core.config import ConfigManager
from vortex.exceptions import CLIError, DataProviderError
from vortex.infrastructure.plugins import get_provider_registry
from vortex.infrastructure.storage.csv_storage import CsvStorage
from vortex.infrastructure.storage.parquet_storage import ParquetStorage
from vortex.models.period import Period
from vortex.services.updating_downloader import UpdatingDownloader


def load_assets_from_file(file_path: Path) -> Dict:
    """Load instrument configurations from assets JSON file.

    Args:
        file_path: Path to assets JSON file

    Returns:
        Dictionary of instrument configurations

    Raises:
        CLIError: If file cannot be loaded
    """
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise CLIError(f"Assets file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise CLIError(f"Invalid JSON in assets file: {e}")
    except Exception as e:
        raise CLIError(f"Error loading assets file: {e}")


def get_default_assets_file(provider: str) -> Optional[Path]:
    """Get the default assets file for a provider.

    Args:
        provider: Provider name

    Returns:
        Path to default assets file if exists, None otherwise
    """
    # Try provider-specific default first
    provider_file = Path(f"config/assets/{provider}.json")
    if provider_file.exists():
        return provider_file

    # Fall back to general default
    default_file = Path("config/assets/default.json")
    if default_file.exists():
        return default_file

    return None


def create_downloader_components(
    config_manager: ConfigManager, provider: str, output_dir: Path, backup_enabled: bool
) -> Tuple[Any, CsvStorage, Optional[ParquetStorage]]:
    """Create downloader and storage components.

    Args:
        config_manager: Configuration manager instance
        provider: Provider name
        output_dir: Output directory for data
        backup_enabled: Whether to enable backup storage

    Returns:
        Tuple of (data_provider, csv_storage, parquet_storage)
    """
    # Get provider configuration
    from .config_utils import get_provider_config_with_defaults

    provider_config = get_provider_config_with_defaults(config_manager, provider)

    # Create data provider through plugin system
    registry = get_provider_registry()
    try:
        data_provider = registry.create_provider(provider, provider_config)
    except Exception as e:
        raise DataProviderError(provider, f"Failed to create provider: {e}")

    # Create storage objects
    csv_storage = CsvStorage(output_dir, dry_run=False)
    parquet_storage = (
        ParquetStorage(output_dir, dry_run=False) if backup_enabled else None
    )

    return data_provider, csv_storage, parquet_storage


def create_downloader(
    data_provider: Any,
    csv_storage: CsvStorage,
    parquet_storage: Optional[ParquetStorage] = None,
) -> UpdatingDownloader:
    """Create an UpdatingDownloader instance.

    Args:
        data_provider: Data provider instance
        csv_storage: CSV storage instance
        parquet_storage: Optional Parquet storage instance

    Returns:
        Configured UpdatingDownloader
    """
    if parquet_storage:
        return UpdatingDownloader(data_provider, csv_storage, parquet_storage)
    else:
        return UpdatingDownloader(data_provider, csv_storage)


def parse_date_range(
    start_date_str: Optional[str], end_date_str: Optional[str], provider: str
) -> Tuple[datetime, datetime]:
    """Parse and validate date range strings.

    Args:
        start_date_str: Start date string (YYYY-MM-DD)
        end_date_str: End date string (YYYY-MM-DD)
        provider: Provider name for defaults

    Returns:
        Tuple of (start_date, end_date)

    Raises:
        CLIError: If date parsing fails
    """
    from .config_utils import get_default_date_range

    try:
        start_date = (
            datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else None
        )
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d") if end_date_str else None
    except ValueError as e:
        raise CLIError(f"Invalid date format: {e}. Use YYYY-MM-DD format.")

    # Apply defaults
    start_date, end_date = get_default_date_range(provider, start_date, end_date)

    # Validate range
    if start_date >= end_date:
        raise CLIError("Start date must be before end date")

    return start_date, end_date


def parse_symbols_list(
    symbols: Tuple[str, ...], symbols_file: Optional[Path]
) -> List[str]:
    """Parse symbols from command line and/or file.

    Args:
        symbols: Tuple of symbols from command line
        symbols_file: Optional path to symbols file

    Returns:
        List of unique symbols

    Raises:
        CLIError: If parsing fails
    """
    all_symbols = list(symbols)

    if symbols_file:
        try:
            with open(symbols_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        all_symbols.append(line)
        except FileNotFoundError:
            raise CLIError(f"Symbols file not found: {symbols_file}")
        except Exception as e:
            raise CLIError(f"Error reading symbols file: {e}")

    # Remove duplicates while preserving order
    unique_symbols = []
    seen = set()
    for symbol in all_symbols:
        if symbol not in seen:
            seen.add(symbol)
            unique_symbols.append(symbol)

    return unique_symbols


def validate_periods(periods_str: str) -> List[Period]:
    """Validate and parse period strings.

    Args:
        periods_str: Comma-separated period strings

    Returns:
        List of Period objects

    Raises:
        CLIError: If validation fails
    """
    periods = []
    for period_str in periods_str.split(","):
        period_str = period_str.strip()
        try:
            period = Period(period_str)
            periods.append(period)
        except ValueError:
            raise CLIError(
                f"Invalid period: {period_str}. "
                f"Valid periods include: 1m, 5m, 15m, 30m, 1h, 1d, 1W, 1M"
            )

    return periods


def count_download_jobs(symbols: List[str], instrument_configs: Dict[str, Any]) -> int:
    """Count total number of download jobs.

    Args:
        symbols: List of symbols
        instrument_configs: Instrument configurations

    Returns:
        Total number of jobs
    """
    total_jobs = 0
    for symbol in symbols:
        config = instrument_configs.get(symbol)
        if config and hasattr(config, "periods"):
            # If config has periods, count them
            periods = (
                config.periods.split(",") if isinstance(config.periods, str) else ["1d"]
            )
            total_jobs += len(periods)
        else:
            # Default to 1 job per symbol
            total_jobs += 1

    return total_jobs


def format_download_summary(
    provider: str,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    output_dir: Path,
    total_jobs: int,
) -> Dict[str, Any]:
    """Format download summary for display.

    Args:
        provider: Provider name
        symbols: List of symbols
        start_date: Start date
        end_date: End date
        output_dir: Output directory
        total_jobs: Total number of jobs

    Returns:
        Dictionary with formatted summary data
    """
    return {
        "provider": provider.upper(),
        "symbols_count": len(symbols),
        "symbols_preview": ", ".join(symbols[:5]) + ("..." if len(symbols) > 5 else ""),
        "date_range": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        "output_directory": str(output_dir),
        "total_jobs": total_jobs,
    }
