#!/usr/bin/env python3
"""BC-Utils CLI main entry point.

Modern command-line interface for financial data download automation.
"""

import sys
from pathlib import Path
from typing import Optional

import click
import logging

try:
    from rich.console import Console
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

from . import __version__
from .commands import download, config, providers, validate

def setup_logging(verbose: int = 0) -> None:
    """Set up logging with rich handler if available."""
    level = logging.WARNING
    if verbose == 1:
        level = logging.INFO
    elif verbose >= 2:
        level = logging.DEBUG
    
    if RICH_AVAILABLE and console:
        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=console, rich_tracebacks=True)]
        )
    else:
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="bcutils")
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Configuration file path"
)
@click.option(
    "--verbose", "-v",
    count=True,
    help="Increase verbosity (-v for INFO, -vv for DEBUG)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be done without making changes"
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], verbose: int, dry_run: bool) -> None:
    """BC-Utils: Financial data download automation tool.
    
    A professional command-line tool for downloading and managing 
    financial market data from multiple providers including Barchart, 
    Yahoo Finance, and Interactive Brokers.
    
    Examples:
        bcutils download --provider barchart --symbol GC
        bcutils config --set-credentials barchart
        bcutils providers --test
        
    Installation (uv recommended):
        curl -LsSf https://astral.sh/uv/install.sh | sh
        uv pip install -e .
        
    Quick Start:
        bcutils config --provider barchart --set-credentials
        bcutils download --provider barchart --symbol GC
    """
    # Set up logging first
    setup_logging(verbose)
    
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store global options in context
    ctx.obj['config_file'] = config
    ctx.obj['verbose'] = verbose
    ctx.obj['dry_run'] = dry_run
    
    # If no command provided, show help
    if ctx.invoked_subcommand is None:
        if RICH_AVAILABLE and console:
            console.print(f"[bold green]BC-Utils v{__version__}[/bold green]")
            console.print("\nFinancial data download automation tool\n")
            console.print("Use [bold]bcutils --help[/bold] to see available commands")
            console.print("Use [bold]bcutils COMMAND --help[/bold] for command-specific help")
            console.print("\n[dim]Quick start:[/dim]")
            console.print("  [cyan]bcutils download --help[/cyan]")
            console.print("  [cyan]bcutils config --help[/cyan]")
        else:
            print(f"BC-Utils v{__version__}")
            print("\nFinancial data download automation tool\n")
            print("Use 'bcutils --help' to see available commands")
            print("Use 'bcutils COMMAND --help' for command-specific help")
            print("\nQuick start:")
            print("  bcutils config --provider barchart --set-credentials")
            print("  bcutils download --provider barchart --symbol GC")
            print("\nInstall with uv (10x faster):")
            print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
            print("  uv pip install -e .")

# Add command groups
cli.add_command(download.download)
cli.add_command(config.config)
cli.add_command(providers.providers)
cli.add_command(validate.validate)

def main() -> None:
    """Main entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        if RICH_AVAILABLE and console:
            console.print("\n[yellow]Operation cancelled by user[/yellow]")
        else:
            print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        if RICH_AVAILABLE and console:
            console.print(f"[red]Error: {e}[/red]")
        else:
            print(f"Error: {e}")
        logging.exception("Unexpected error occurred")
        sys.exit(1)

if __name__ == "__main__":
    main()