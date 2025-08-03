"""Download command implementation."""

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...bc_utils import create_barchart_downloader, create_yahoo_downloader, create_ibkr_downloader
from ...initialization.session_config import SessionConfig
from ...initialization.config_utils import InstrumentConfig
from ..utils.config_manager import ConfigManager
from ..utils.instrument_parser import parse_instruments

console = Console()
logger = logging.getLogger(__name__)


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
@click.option(
    "--provider", "-p",
    type=click.Choice(["barchart", "yahoo", "ibkr"], case_sensitive=False),
    required=True,
    help="Data provider to use"
)
@click.option(
    "--symbol", "-s",
    multiple=True,
    help="Symbol(s) to download (can be used multiple times)"
)
@click.option(
    "--symbols-file",
    type=click.Path(exists=True, path_type=Path),
    help="File containing symbols (one per line)"
)
@click.option(
    "--assets", "--assets-file",
    type=click.Path(exists=True, path_type=Path),
    help="Custom assets file with instruments to download"
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date (YYYY-MM-DD). Default: 30 days ago"
)
@click.option(
    "--end-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date (YYYY-MM-DD). Default: today"
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
    
    # Parse symbols
    if assets:
        # Load instruments from user-specified assets file
        symbols = load_config_instruments(assets)
        console.print(f"[green]Loaded {len(symbols)} instruments from {assets}[/green]")
    else:
        symbols = parse_instruments(symbol, symbols_file)
        if not symbols:
            # No symbols specified - try to load default assets for this provider
            try:
                default_assets_file = get_default_assets_file(provider)
                symbols = load_config_instruments(default_assets_file)
                console.print(f"[green]Loaded {len(symbols)} instruments from default {default_assets_file}[/green]")
            except:
                console.print("[red]Error: No symbols specified. Use --symbol, --symbols-file, or --assets[/red]")
                raise click.Abort()
    
    # Validate date range
    if start_date >= end_date:
        console.print("[red]Error: Start date must be before end date[/red]")
        raise click.Abort()
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Show download summary
    show_download_summary(provider, symbols, start_date, end_date, output_dir, backup, force)
    
    if not yes and not click.confirm("Proceed with download?"):
        console.print("[yellow]Download cancelled[/yellow]")
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
        
        console.print(f"[green]✓ Download completed! {success_count}/{len(symbols)} symbols successful[/green]")
        
    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        logger.exception("Download error")
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
    
    # Create session config
    config = create_session_config(
        config_manager=config_manager,
        provider=provider,
        output_dir=output_dir,
        backup=backup,
        force=force,
        chunk_size=chunk_size
    )
    
    # Create downloader
    downloader = create_downloader(provider, config)
    
    success_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        for symbol in symbols:
            task = progress.add_task(f"Downloading {symbol}...", total=None)
            
            try:
                logger.info(f"Downloading {symbol} from {provider}")
                
                # Create downloader based on provider
                if provider == "yahoo":
                    downloader = create_yahoo_downloader(config)
                elif provider == "barchart":
                    downloader = create_barchart_downloader(config)
                elif provider == "ibkr":
                    downloader = create_ibkr_downloader(config)
                else:
                    raise ValueError(f"Unknown provider: {provider}")
                
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
                
                progress.update(task, description=f"✓ {symbol} completed")
                success_count += 1
                
            except Exception as e:
                progress.update(task, description=f"✗ {symbol} failed: {e}")
                logger.error(f"Failed to download {symbol}: {e}")
    
    return success_count

def create_session_config(
    config_manager: ConfigManager,
    provider: str,
    output_dir: Path,
    backup: bool,
    force: bool,
    chunk_size: int
) -> SessionConfig:
    """Create session configuration for the download."""
    
    # Get provider-specific config
    provider_config = config_manager.get_provider_config(provider)
    
    # Create session config
    config = SessionConfig()
    config.provider_type = provider
    config.download_directory = str(output_dir)
    config.backup_data = backup
    config.force_backup = force
    config.chunk_size_days = chunk_size
    config.dry_run = False  # Handled at CLI level
    
    # Set provider-specific options
    if provider == "barchart":
        config.username = provider_config.get("username")
        config.password = provider_config.get("password")
        config.daily_download_limit = provider_config.get("daily_limit", 150)
    elif provider == "ibkr":
        config.provider_host = provider_config.get("host", "localhost")
        config.provider_port = provider_config.get("port", "7497")
    
    return config

def create_downloader(provider: str, config: SessionConfig):
    """Create the appropriate downloader for the provider."""
    
    if provider == "barchart":
        return create_barchart_downloader(config)
    elif provider == "yahoo":
        return create_yahoo_downloader(config)
    elif provider == "ibkr":
        return create_ibkr_downloader(config)
    else:
        raise ValueError(f"Unknown provider: {provider}")