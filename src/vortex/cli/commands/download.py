"""Download command implementation."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

# Local imports (organized by hierarchy)
from vortex.core.config import ConfigManager
from vortex.infrastructure.storage.csv_storage import CsvStorage
from vortex.infrastructure.storage.parquet_storage import ParquetStorage
from vortex.services.updating_downloader import UpdatingDownloader
from vortex.services.download_job import DownloadJob
from vortex.exceptions import (
    CLIError, MissingArgumentError, InvalidCommandError,
    ConfigurationError, DataProviderError, DataStorageError
)
from vortex.core.instruments import InstrumentConfig
from vortex.models.stock import Stock
from vortex.models.period import Period
from vortex.logging_integration import get_module_logger, get_module_performance_logger
from vortex.plugins import get_provider_registry
from ..completion import complete_provider, complete_symbol, complete_symbols_file, complete_assets_file, complete_date
from ..utils.provider_utils import get_available_providers, get_provider_config_from_vortex_config
from ..utils.instrument_parser import parse_instruments
from ..ux import get_ux, enhanced_error_handler, validate_symbols

console = Console()
ux = get_ux()
logger = get_module_logger()
perf_logger = get_module_performance_logger()


def load_config_instruments(assets_file_path: Path) -> dict:
    """Load instrument configurations from assets JSON file."""
    try:
        instrument_configs = InstrumentConfig.load_from_json(str(assets_file_path))
        return instrument_configs
    except Exception as e:
        console.print(f"[red]Error loading assets file '{assets_file_path}': {e}[/red]")
        raise click.Abort()


def get_default_assets_file(provider: str) -> Path:
    """Get the default assets file for the given provider.
    
    This returns the default assets that ship with Vortex.
    Users can override by specifying --assets with their own file.
    """
    # Try provider-specific default file first
    provider_file = Path(f"config/assets/{provider}.json")
    if provider_file.exists():
        return provider_file
    
    # Fall back to general default
    default_file = Path("config/assets/default.json")
    if default_file.exists():
        return default_file
    
    # If nothing exists, return the expected provider file (will cause error with helpful message)
    return provider_file

@click.command()
@enhanced_error_handler
@click.option(
    "--provider", "-p",
    type=str,
    default=None,
    help="Data provider to use (default: from config, yahoo if not set - free, no credentials required)",
    shell_complete=complete_provider
)
@click.option(
    "--symbol", "-s",
    multiple=True,
    help="Symbol(s) to download (can be used multiple times)",
    shell_complete=complete_symbol
)
@click.option(
    "--symbols-file",
    type=click.Path(exists=True, path_type=Path),
    help="File containing symbols (one per line)",
    shell_complete=complete_symbols_file
)
@click.option(
    "--assets", "--assets-file",
    type=click.Path(exists=True, path_type=Path),
    help="Custom assets file with instruments to download",
    shell_complete=complete_assets_file
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date (YYYY-MM-DD). Default: 30 days ago",
    shell_complete=complete_date
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date (YYYY-MM-DD). Default: today",
    shell_complete=complete_date
)
@click.option(
    "--output-dir", "-o",
    type=click.Path(path_type=Path),
    help="Output directory. Default: ./data"
)
@click.option(
    "--backup/--no-backup",
    default=False,
    help="Create Parquet backup files"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-download even if data exists"
)
@click.option(
    "--chunk-size",
    type=click.IntRange(1, 365),
    default=30,
    help="Days per download chunk (1-365)"
)
@click.option(
    "--yes", "-y",
    is_flag=True,
    help="Skip confirmation prompt"
)
@click.pass_context
def download(
    ctx: click.Context,
    provider: str,
    symbol: tuple,
    symbols_file: Optional[Path],
    assets: Optional[Path],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    output_dir: Optional[Path],
    backup: bool,
    force: bool,
    chunk_size: int,
    yes: bool,
) -> None:
    """Download financial data for specified instruments.
    
    \b
    Examples:
        vortex download -s AAPL -s GOOGL                    # Uses yahoo (default)
        vortex download --symbol TSLA MSFT --yes            # Uses yahoo (default)
        vortex download --symbols-file symbols.txt          # Uses yahoo (default)
        vortex download -p barchart -s GCM25 --start-date 2024-01-01  
        vortex download -p ibkr -s TSLA --start-date 2024-01-01
        
    \b
    Default Assets:
        When no symbols are specified, Vortex loads default instruments from:
        - config/assets/yahoo.json - Default instruments for Yahoo Finance
        - config/assets/barchart.json - Default instruments for Barchart.com  
        - config/assets/ibkr.json - Default instruments for Interactive Brokers
        - config/assets/default.json - General fallback
        
        Use --assets to provide your own custom assets file.
        
    \b
    Installation:
        # Fast installation with uv (recommended)
        uv pip install -e .
        
        # Run without installation
        uv run vortex download --help
    """
    # Get configuration manager first
    config_manager = ConfigManager(ctx.obj.get('config_file'))
    
    # Use default provider from configuration if none specified
    if provider is None:
        provider = config_manager.get_default_provider()
        ux.print_info(f"Using default provider: {provider}")
    
    # Validate provider exists in plugin registry
    try:
        registry = get_provider_registry()
        registry.get_plugin(provider)  # This will raise PluginNotFoundError if not found
    except Exception as e:
        available_providers = get_available_providers()
        ux.print_error(f"Provider '{provider}' not found")
        ux.print_info(f"Available providers: {', '.join(available_providers)}")
        ux.print_info("💡 Use 'vortex providers --list' to see all available providers")
        raise click.Abort()
    
    # Set defaults
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    if not output_dir:
        output_dir = Path("./data")
    
    # Parse and validate instruments
    instrument_configs = None
    symbols = None
    
    if assets:
        # Load instruments from user-specified assets file
        instrument_configs = load_config_instruments(assets)
        symbols = list(instrument_configs.keys())
        ux.print_success(f"Loaded {len(symbols)} instruments from {assets}")
    else:
        symbols = parse_instruments(symbol, symbols_file)
        if not symbols:
            # No symbols specified - try to load default assets for this provider
            try:
                default_assets_file = get_default_assets_file(provider)
                instrument_configs = load_config_instruments(default_assets_file)
                symbols = list(instrument_configs.keys())
                ux.print_success(f"Loaded {len(symbols)} instruments from default {default_assets_file}")
            except (FileNotFoundError, PermissionError, ValueError, KeyError) as e:
                # Specific exceptions for common file/parsing errors
                ux.print_error(f"No symbols specified and no default assets found for {provider}")
                ux.print_info("💡 Try: vortex download -p yahoo -s AAPL")
                raise MissingArgumentError(
                    "symbol", 
                    "download",
                ) from e
    
    # Validate symbols
    symbols = validate_symbols(symbols)
    if not symbols:
        ux.print_error("No valid symbols to download")
        raise click.Abort()
    
    # Validate date range
    if start_date >= end_date:
        raise InvalidCommandError(
            "download",
            f"Start date ({start_date.date()}) must be before end date ({end_date.date()})"
        )
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Show download summary
    show_download_summary(provider, symbols, start_date, end_date, output_dir, backup, force)
    
    if not yes and not ux.confirm("Proceed with download?", True):
        ux.print_warning("Download cancelled")
        return
    
    # Execute download
    try:
        success_count = execute_download(
            config_manager=config_manager,
            provider=provider,
            symbols=symbols,
            instrument_configs=instrument_configs,
            start_date=start_date,
            end_date=end_date,
            output_dir=output_dir,
            backup=backup,
            force=force,
            chunk_size=chunk_size,
            dry_run=ctx.obj.get('dry_run', False)
        )
        
        if success_count == len(symbols):
            ux.print_success(f"Download completed! All {success_count} symbols successful")
        else:
            ux.print_warning(f"Download completed with issues: {success_count}/{len(symbols)} symbols successful")
            ux.print_info(f"💡 Check logs for details on failed symbols")
        
    except Exception as e:
        ux.print_error(f"Download failed: {e}")
        logger.error("Download process failed", error=str(e))
        raise click.Abort()

def show_download_summary(
    provider: str,
    symbols: List[str],
    start_date: datetime,
    end_date: datetime,
    output_dir: Path,
    backup: bool,
    force: bool
) -> None:
    """Display download summary table."""
    table = Table(title="Download Summary")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Provider", provider.upper())
    table.add_row("Symbols", f"{len(symbols)} symbols")
    table.add_row("Date Range", f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    table.add_row("Output Directory", str(output_dir))
    table.add_row("Backup Files", "Yes" if backup else "No")
    table.add_row("Force Re-download", "Yes" if force else "No")
    
    console.print(table)
    
    # Show symbols list
    if len(symbols) <= 10:
        console.print(f"[dim]Symbols: {', '.join(symbols)}[/dim]")
    else:
        console.print(f"[dim]Symbols: {', '.join(symbols[:5])} ... and {len(symbols)-5} more[/dim]")

def execute_download(
    config_manager: ConfigManager,
    provider: str,
    symbols: List[str],
    instrument_configs: dict,
    start_date: datetime,
    end_date: datetime,
    output_dir: Path,
    backup: bool,
    force: bool,
    chunk_size: int,
    dry_run: bool
) -> int:
    """Execute the actual download process."""
    
    if dry_run:
        console.print("[yellow]DRY RUN: Would download data but no changes will be made[/yellow]")
        return len(symbols)
    
    # If no instrument configs available, create simple stock configs with daily periods
    if not instrument_configs:
        instrument_configs = {}
        for symbol in symbols:
            # Create a simple stock config with daily period for direct symbol downloads
            instrument_configs[symbol] = InstrumentConfig(
                asset_class='stock',
                name=symbol,
                code=symbol,
                periods='1d'
            )
    
    # Get download configuration
    download_config = get_download_config(
        config_manager=config_manager,
        output_dir=output_dir,
        backup=backup,
        force=force
    )
    
    # Create downloader once
    downloader = create_downloader(provider, download_config)
    
    # Count total jobs to process 
    total_jobs = 0
    for symbol in symbols:
        config = instrument_configs.get(symbol)
        if config and config.periods:
            total_jobs += len(config.periods)
        else:
            total_jobs += 1  # Default to one job (daily)
    
    success_count = 0
    job_count = 0
    
    with ux.progress(f"Downloading {total_jobs} symbol-period combinations") as progress:
        for symbol in symbols:
            config = instrument_configs.get(symbol)
            
            # Determine periods to download
            periods = []
            if config and config.periods:
                periods = config.periods
            else:
                # Fallback to daily for direct symbol input
                periods = [Period.Daily]
            
            # Create appropriate instrument object
            if config and hasattr(config, 'asset_class'):
                if config.asset_class.value == 'stock':
                    instrument = Stock(id=symbol, symbol=config.code)
                elif config.asset_class.value == 'forex':
                    from vortex.models.forex import Forex
                    instrument = Forex(id=symbol, symbol=config.code)
                else:
                    # Default to stock if unknown type
                    instrument = Stock(id=symbol, symbol=symbol)
            else:
                # Default to stock for direct symbol downloads
                instrument = Stock(id=symbol, symbol=symbol)
            
            logger.info(f"Processing {symbol} with {len(periods)} period(s): {[p.value for p in periods]}", 
                       symbol=symbol, provider=provider)
            
            # Process each period for this symbol
            for period in periods:
                job_count += 1
                progress.update(job_count - 1, total_jobs, 
                              f"Processing {symbol}|{period.value} ({job_count}/{total_jobs})")
                
                try:
                    logger.info(f"Processing {str(instrument)}|{period.value}|{start_date.strftime('%Y-%m-%d')}|{end_date.strftime('%Y-%m-%d')}", 
                               symbol=symbol, period=period.value, provider=provider)
                    
                    # Ensure dates are timezone-aware (use UTC if naive) 
                    safe_start_date = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date
                    safe_end_date = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date
                    
                    job = DownloadJob(
                        data_provider=downloader.data_provider,
                        data_storage=downloader.data_storage,
                        instrument=instrument,
                        period=period,  # Use the actual period from config
                        start_date=safe_start_date,
                        end_date=safe_end_date
                    )
                    
                    # Process the download job
                    downloader._process_job(job)
                    
                    progress.update(job_count, total_jobs, 
                                  f"✓ {symbol}|{period.value} completed ({job_count}/{total_jobs})")
                    success_count += 1
                    
                except Exception as e:
                    progress.update(job_count, total_jobs, 
                                  f"✗ {symbol}|{period.value} failed ({job_count}/{total_jobs})")
                    logger.error(f"Failed to download {symbol}|{period.value}: {e}", 
                               symbol=symbol, period=period.value, error=str(e))
    
    return success_count

def get_download_config(
    config_manager: ConfigManager,
    output_dir: Path,
    backup: bool,
    force: bool
) -> dict:
    """Get configuration for the download."""
    
    # Load full configuration
    config = config_manager.load_config()
    
    return {
        'vortex_config': config,
        'output_dir': output_dir,
        'backup': backup,
        'force': force
    }

def create_downloader(provider: str, download_config: dict):
    """Create the appropriate downloader for the provider using plugin system."""
    
    vortex_config = download_config['vortex_config']
    output_dir = download_config['output_dir']
    backup = download_config['backup']
    force = download_config['force']
    
    # Create storage objects
    data_storage = CsvStorage(str(output_dir), False)  # dry_run handled at CLI level
    backup_data_storage = ParquetStorage(str(output_dir), False) if backup else None
    
    # Create data provider using plugin system
    try:
        registry = get_provider_registry()
        
        # Get provider-specific configuration dynamically
        provider_config = get_provider_config_from_vortex_config(provider, vortex_config)
        
        # Create data provider through plugin system
        data_provider = registry.create_provider(provider, provider_config)
        
        logger.info(f"Created data provider '{provider}' using plugin system")
        
    except Exception as e:
        logger.error(f"Failed to create provider '{provider}' via plugin system: {e}")
        raise DataProviderError(provider, f"Initialization failed: {e}")
    
    # Create and return the downloader
    return UpdatingDownloader(
        data_storage, 
        data_provider, 
        backup_data_storage,
        force_backup=force, 
        random_sleep_in_sec=vortex_config.general.random_sleep_max,
        dry_run=vortex_config.general.dry_run
    )