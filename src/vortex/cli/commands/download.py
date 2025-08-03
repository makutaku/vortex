"""Download command implementation."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...data_providers.bc_data_provider import BarchartDataProvider
from ...data_providers.ib_data_provider import IbkrDataProvider
from ...data_providers.yf_data_provider import YahooDataProvider
from ...data_storage.csv_storage import CsvStorage
from ...data_storage.parquet_storage import ParquetStorage
from ...downloaders.updating_downloader import UpdatingDownloader
from ...exceptions import (
    CLIError, MissingArgumentError, InvalidCommandError,
    ConfigurationError, DataProviderError, DataStorageError
)
from ...initialization.config_utils import InstrumentConfig
from ...config import ConfigManager
from ...logging_integration import get_module_logger, get_module_performance_logger
from ..utils.instrument_parser import parse_instruments
from ..ux import get_ux, enhanced_error_handler, validate_symbols
from ..completion import complete_provider, complete_symbol, complete_symbols_file, complete_assets_file, complete_date

console = Console()
ux = get_ux()
logger = get_module_logger()
perf_logger = get_module_performance_logger()


def load_config_instruments(assets_file_path: Path) -> List[str]:
    """Load instrument symbols from assets JSON file."""
    try:
        instrument_configs = InstrumentConfig.load_from_json(str(assets_file_path))
        return list(instrument_configs.keys())
    except Exception as e:
        console.print(f"[red]Error loading assets file '{assets_file_path}': {e}[/red]")
        raise click.Abort()


def get_default_assets_file(provider: str) -> Path:
    """Get the default assets file for the given provider.
    
    This returns the default assets that ship with Vortex.
    Users can override by specifying --assets with their own file.
    """
    # Try provider-specific default file first
    provider_file = Path(f"assets/{provider}.json")
    if provider_file.exists():
        return provider_file
    
    # Fall back to general default
    default_file = Path("assets/default.json")
    if default_file.exists():
        return default_file
    
    # If nothing exists, return the expected provider file (will cause error with helpful message)
    return provider_file

@click.command()
@enhanced_error_handler
@click.option(
    "--provider", "-p",
    type=click.Choice(["barchart", "yahoo", "ibkr"], case_sensitive=False),
    required=True,
    help="Data provider to use",
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
        vortex download -p yahoo -s AAPL -s GOOGL
        vortex download -p barchart -s GCM25 --start-date 2024-01-01  
        vortex download -p yahoo --symbols-file symbols.txt
        vortex download -p yahoo --assets /path/to/my-assets.json
        vortex download -p yahoo -s MSFT --yes  # Skip confirmation
        
    \b
    Default Assets:
        When no symbols are specified, Vortex loads default instruments from:
        - assets/yahoo.json - Default instruments for Yahoo Finance
        - assets/barchart.json - Default instruments for Barchart.com  
        - assets/ibkr.json - Default instruments for Interactive Brokers
        - assets/default.json - General fallback
        
        Use --assets to provide your own custom assets file.
        
    \b
    Installation:
        # Fast installation with uv (recommended)
        uv pip install -e .
        
        # Run without installation
        uv run vortex download --help
    """
    # Get configuration
    config_manager = ConfigManager(ctx.obj.get('config_file'))
    
    # Set defaults
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    if not output_dir:
        output_dir = Path("./data")
    
    # Parse and validate symbols
    if assets:
        # Load instruments from user-specified assets file
        symbols = load_config_instruments(assets)
        ux.print_success(f"Loaded {len(symbols)} instruments from {assets}")
    else:
        symbols = parse_instruments(symbol, symbols_file)
        if not symbols:
            # No symbols specified - try to load default assets for this provider
            try:
                default_assets_file = get_default_assets_file(provider)
                symbols = load_config_instruments(default_assets_file)
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
    
    # Get download configuration
    download_config = get_download_config(
        config_manager=config_manager,
        output_dir=output_dir,
        backup=backup,
        force=force
    )
    
    success_count = 0
    
    with ux.progress(f"Downloading {len(symbols)} symbols") as progress:
        for i, symbol in enumerate(symbols, 1):
            progress.update(i - 1, len(symbols), f"Downloading {symbol} ({i}/{len(symbols)})")
            
            logger.info(f"Starting download for {symbol}", symbol=symbol, provider=provider)
            
            try:
                logger.info(f"Starting download for {symbol}", symbol=symbol, provider=provider)
                
                # Create downloader based on provider
                downloader = create_downloader(provider, download_config)
                
                # Create a simple instrument (assume stock for now)
                from ...instruments.stock import Stock
                from ...instruments.period import Period
                from ...downloaders.download_job import DownloadJob
                
                instrument = Stock(id=symbol, symbol=symbol)
                
                # Ensure dates are timezone-aware (use UTC if naive)
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
                
                job = DownloadJob(
                    data_provider=downloader.data_provider,
                    data_storage=downloader.data_storage,
                    instrument=instrument,
                    period=Period.Daily,
                    start_date=start_date,
                    end_date=end_date
                )
                
                # Process the download job
                downloader._process_job(job)
                
                progress.update(i, len(symbols), f"✓ {symbol} completed ({i}/{len(symbols)})")
                success_count += 1
                
            except Exception as e:
                progress.update(i, len(symbols), f"✗ {symbol} failed ({i}/{len(symbols)})")
                logger.error(f"Failed to download {symbol}: {e}", symbol=symbol, error=str(e))
    
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
    """Create the appropriate downloader for the provider."""
    
    vortex_config = download_config['vortex_config']
    output_dir = download_config['output_dir']
    backup = download_config['backup']
    force = download_config['force']
    
    # Create storage objects
    data_storage = CsvStorage(str(output_dir), False)  # dry_run handled at CLI level
    backup_data_storage = ParquetStorage(str(output_dir), False) if backup else None
    
    # Create provider-specific data provider
    if provider == "barchart":
        barchart_config = vortex_config.providers.barchart
        data_provider = BarchartDataProvider(
            username=barchart_config.username,
            password=barchart_config.password,
            daily_download_limit=barchart_config.daily_limit
        )
    elif provider == "yahoo":
        data_provider = YahooDataProvider()
    elif provider == "ibkr":
        ibkr_config = vortex_config.providers.ibkr
        data_provider = IbkrDataProvider(
            ipaddress=ibkr_config.host, 
            port=str(ibkr_config.port)
        )
    else:
        raise ValueError(f"Unknown provider: {provider}")
    
    # Create and return the downloader
    return UpdatingDownloader(
        data_storage, 
        data_provider, 
        backup_data_storage,
        force_backup=force, 
        random_sleep_in_sec=vortex_config.general.random_sleep_max,
        dry_run=vortex_config.general.dry_run
    )