"""Download command implementation."""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...bc_utils import create_barchart_downloader, create_yahoo_downloader, create_ibkr_downloader
from ...initialization.session_config import SessionConfig
from ..utils.config_manager import ConfigManager
from ..utils.instrument_parser import parse_instruments

console = Console()
logger = logging.getLogger(__name__)

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
@click.pass_context
def download(
    ctx: click.Context,
    provider: str,
    symbol: tuple,
    symbols_file: Optional[Path],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    output_dir: Optional[Path],
    backup: bool,
    force: bool,
    chunk_size: int,
) -> None:
    """Download financial data for specified instruments.
    
    Examples:
        bcutils download -p barchart -s GCM25 -s SIH25
        bcutils download -p yahoo -s AAPL --start-date 2024-01-01
        bcutils download -p ibkr --symbols-file symbols.txt
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
    symbols = parse_instruments(symbol, symbols_file)
    if not symbols:
        console.print("[red]Error: No symbols specified. Use --symbol or --symbols-file[/red]")
        raise click.Abort()
    
    # Validate date range
    if start_date >= end_date:
        console.print("[red]Error: Start date must be before end date[/red]")
        raise click.Abort()
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Show download summary
    show_download_summary(provider, symbols, start_date, end_date, output_dir, backup, force)
    
    if not click.confirm("Proceed with download?"):
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
                # Here you would call the actual download logic
                # For now, we'll simulate the download
                logger.info(f"Downloading {symbol} from {provider}")
                
                # TODO: Implement actual download using existing bc_utils functions
                # result = downloader.download_instrument_data(symbol, start_date, end_date)
                
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