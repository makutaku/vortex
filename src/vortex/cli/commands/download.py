"""Download command implementation.

Refactored to use focused modules following single responsibility principle."""

import time
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List, Dict, Any

import click
from rich.console import Console

# Focused module imports
from .symbol_resolver import resolve_symbols_and_configs
from .download_executor import DownloadExecutor, show_download_summary

# Core imports
from vortex.core.config import ConfigManager
from ..utils.config_utils import (
    get_or_create_config_manager, 
    ensure_provider_configured,
    get_default_date_range
)
from vortex.exceptions import CLIError
from ..completion import complete_provider, complete_symbol, complete_symbols_file, complete_assets_file, complete_date
from ..ux import enhanced_error_handler

console = Console()


@dataclass
class DownloadConfig:
    """Configuration for download command."""
    provider: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    output_dir: Path
    mode: str = 'updating'
    backup_enabled: bool = True
    force_backup: bool = False
    random_sleep: int = 0
    dry_run: bool = False
    download_config: Dict[str, Any] = None


# Note: load_config_instruments functionality moved to symbol_resolver.py

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
    # Setup
    config_manager = get_or_create_config_manager(ctx.obj.get('config_file'))
    
    # Resolve provider (use default if not specified)
    if provider is None:
        provider = config_manager.get_default_provider()
        console.print(f"Using default provider: {provider}")
    
    # Ensure provider is configured
    ensure_provider_configured(config_manager, provider)
    
    # Set defaults for dates and output directory
    if start_date is None or end_date is None:
        default_start, default_end = get_default_date_range(provider)
        start_date = start_date or default_start
        end_date = end_date or default_end
    
    if output_dir is None:
        output_dir = Path('./data')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Resolve symbols and configurations using extracted module
    try:
        symbols_list, instrument_configs = resolve_symbols_and_configs(
            provider=provider,
            symbols=list(symbol) if symbol else None,
            assets_file=assets
        )
    except CLIError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise click.Abort()
    
    # Validate inputs
    if not symbols_list:
        console.print("[red]No symbols to download[/red]")
        raise click.Abort()
    
    # Show summary and get confirmation
    _show_download_summary(provider, symbols_list, start_date, end_date, output_dir, backup, force)
    if not yes and not click.confirm("Proceed with download?", default=True):
        console.print("[yellow]Download cancelled[/yellow]")
        return
    
    # Create download configuration
    download_config = DownloadConfig(
        provider=provider,
        symbols=symbols_list,
        start_date=start_date,
        end_date=end_date,
        output_dir=output_dir,
        backup_enabled=backup,
        force_backup=force,
        dry_run=ctx.obj.get('dry_run', False),
        download_config=config_manager.get_provider_config(provider)
    )
    
    # Execute download using extracted module
    executor = DownloadExecutor(download_config)
    start_time = time.time()
    
    try:
        successful_jobs = executor.execute_downloads(symbols_list, instrument_configs)
        end_time = time.time()
        
        # Show results
        total_jobs = len(symbols_list)  # Simplified - each symbol is one job
        failed_jobs = total_jobs - successful_jobs
        show_download_summary(start_time, end_time, total_jobs, successful_jobs, failed_jobs)
        
        if successful_jobs > 0:
            console.print(f"[green]✅ Download completed: {successful_jobs}/{total_jobs} successful[/green]")
        else:
            console.print(f"[red]❌ Download failed: No data downloaded[/red]")
            raise click.Abort()
            
    except KeyboardInterrupt:
        console.print("[yellow]Download interrupted by user[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]Download failed: {e}[/red]")
        raise click.Abort()


def _show_download_summary(provider: str, symbols: List[str], start_date: datetime, 
                          end_date: datetime, output_dir: Path, backup: bool, force: bool) -> None:
    """Display download summary before execution."""
    console.print(f"\n[bold]📊 Download Summary[/bold]")
    console.print(f"Provider: {provider}")
    console.print(f"Symbols: {', '.join(symbols[:5])}{' ...' if len(symbols) > 5 else ''} ({len(symbols)} total)")
    console.print(f"Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    console.print(f"Output Directory: {output_dir}")
    console.print(f"Backup: {'Yes' if backup else 'No'}")
    console.print(f"Force Redownload: {'Yes' if force else 'No'}")
    console.print()

# Note: All other helper functions moved to focused modules:
# - Symbol resolution: symbol_resolver.py
# - Job creation: job_creator.py  
# - Download execution: download_executor.py