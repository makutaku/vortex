#!/usr/bin/env python3
"""Vortex CLI main entry point.

Modern command-line interface for financial data download automation.
"""

import sys
from pathlib import Path
from typing import Optional

import click

from ..exceptions import VortexError, CLIError
from ..config import ConfigManager
from ..logging_integration import configure_logging_from_manager, get_logger, run_health_checks

try:
    from rich.console import Console
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

from . import __version__
from .commands import download, config, providers, validate

def setup_logging(config_file: Optional[Path] = None, verbose: int = 0) -> None:
    """Set up logging using Vortex configuration system."""
    try:
        # Load configuration and set up logging
        config_manager = ConfigManager(config_file)
        configure_logging_from_manager(config_manager, service_name="vortex-cli", version=__version__)
        
        # Get logger for CLI
        logger = get_logger("vortex.cli")
        logger.info("Vortex CLI started", version=__version__, verbose_level=verbose)
        
    except Exception as e:
        # Fallback to basic logging if configuration fails
        import logging
        logging.basicConfig(
            level=logging.DEBUG if verbose > 1 else logging.INFO if verbose else logging.WARNING,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        logger = logging.getLogger("vortex.cli")
        logger.warning(f"Failed to configure logging from config: {e}")
        logger.info(f"Using fallback logging configuration")

@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="vortex")
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
    """Vortex: Financial data download automation tool.
    
    A professional command-line tool for downloading and managing 
    financial market data from multiple providers including Barchart, 
    Yahoo Finance, and Interactive Brokers.
    
    \b
    Examples:
        vortex download --provider barchart --symbol GC
        vortex config --set-credentials barchart
        vortex providers --test
        
    \b
    Installation (uv recommended):
        curl -LsSf https://astral.sh/uv/install.sh | sh
        uv pip install -e .
        
    \b
    Quick Start:
        vortex config --provider barchart --set-credentials
        vortex download --provider barchart --symbol GC
    """
    # Set up logging first
    setup_logging(config, verbose)
    
    # Ensure context object exists
    ctx.ensure_object(dict)
    
    # Store global options in context
    ctx.obj['config_file'] = config
    ctx.obj['verbose'] = verbose
    ctx.obj['dry_run'] = dry_run
    
    # If no command provided, show help
    if ctx.invoked_subcommand is None:
        if RICH_AVAILABLE and console:
            console.print(f"[bold green]Vortex v{__version__}[/bold green]")
            console.print("\nFinancial data download automation tool\n")
            console.print("Use [bold]vortex --help[/bold] to see available commands")
            console.print("Use [bold]vortex COMMAND --help[/bold] for command-specific help")
            console.print("\n[dim]Quick start:[/dim]")
            console.print("  [cyan]vortex download --help[/cyan]")
            console.print("  [cyan]vortex config --help[/cyan]")
        else:
            print(f"Vortex v{__version__}")
            print("\nFinancial data download automation tool\n")
            print("Use 'vortex --help' to see available commands")
            print("Use 'vortex COMMAND --help' for command-specific help")
            print("\nQuick start:")
            print("  vortex config --provider barchart --set-credentials")
            print("  vortex download --provider barchart --symbol GC")
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
    except VortexError as e:
        # Handle our custom exceptions with proper formatting
        if RICH_AVAILABLE and console:
            console.print(f"[red]Error: {e}[/red]")
        else:
            print(f"Error: {e}")
        
        # Log the exception details for debugging
        if e.error_code:
            logging.error(f"Vortex error ({e.error_code}): {e.message}")
        else:
            logging.error(f"Vortex error: {e.message}")
        
        sys.exit(1)
    except Exception as e:
        # Handle unexpected exceptions
        if RICH_AVAILABLE and console:
            console.print(f"[red]Unexpected error: {e}[/red]")
            console.print("[yellow]This may be a bug. Please report it at: https://github.com/makutaku/vortex/issues[/yellow]")
        else:
            print(f"Unexpected error: {e}")
            print("This may be a bug. Please report it at: https://github.com/makutaku/vortex/issues")
        
        logging.exception("Unexpected error occurred")
        sys.exit(1)

if __name__ == "__main__":
    main()