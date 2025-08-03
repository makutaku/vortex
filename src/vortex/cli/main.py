#!/usr/bin/env python3
"""Vortex CLI main entry point.

Modern command-line interface for financial data download automation.
"""

import sys
from datetime import datetime
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
from .help import help as help_command
from .ux import get_ux, CommandWizard
from .completion import install_completion

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
    
    # Configure UX based on options
    ux = get_ux()
    ux.set_quiet(verbose == 0 and not ctx.invoked_subcommand)
    ux.set_force_yes(dry_run)
    
    # If no command provided, show enhanced welcome
    if ctx.invoked_subcommand is None:
        show_welcome(ux)

def show_welcome(ux):
    """Show enhanced welcome message."""
    ux.print_panel(
        f"🚀 **Vortex v{__version__}**\n\n"
        "Financial data download automation tool\n\n"
        "**Quick Commands:**\n"
        "• `vortex wizard` - Interactive setup wizard\n"
        "• `vortex help quickstart` - Quick start guide\n"
        "• `vortex download --help` - Download command help\n"
        "• `vortex config --help` - Configuration help",
        title="Welcome to Vortex",
        style="green"
    )
    
    # Show helpful tips
    from .help import get_help_system
    help_system = get_help_system()
    help_system.show_tips(2)


@cli.command()
@click.pass_context
def wizard(ctx: click.Context):
    """Interactive setup and command wizard."""
    ux = get_ux()
    command_wizard = CommandWizard(ux)
    
    ux.print_panel(
        "🧙 **Vortex Wizard**\n\n"
        "Choose what you'd like to do:",
        title="Interactive Setup",
        style="magenta"
    )
    
    action = ux.choice(
        "What would you like to set up?",
        ["Download data", "Configure providers", "View help", "Exit"],
        "Download data"
    )
    
    if action == "Download data":
        config = command_wizard.run_download_wizard()
        if config.get("execute"):
            # Execute the download command
            from .commands.download import download
            ctx.invoke(download, **_convert_wizard_config_to_params(config))
    
    elif action == "Configure providers":
        config = command_wizard.run_config_wizard()
        if config.get("provider"):
            # Execute the config command
            from .commands.config import config as config_cmd
            ctx.invoke(config_cmd, provider=config["provider"], set_credentials=True)
    
    elif action == "View help":
        from .help import get_help_system
        help_system = get_help_system()
        help_system.show_quick_start()
    
    else:
        ux.print("👋 Goodbye!")


def _convert_wizard_config_to_params(config: dict) -> dict:
    """Convert wizard config to CLI parameters."""
    params = {
        "provider": config.get("provider"),
        "symbol": config.get("symbols", []),
        "symbols_file": Path(config["symbols_file"]) if config.get("symbols_file") else None,
        "assets": None,
        "start_date": datetime.fromisoformat(config["start_date"]) if config.get("start_date") else None,
        "end_date": datetime.fromisoformat(config["end_date"]) if config.get("end_date") else None,
        "output_dir": None,
        "backup": config.get("backup", False),
        "force": config.get("force", False),
        "chunk_size": 30,
        "yes": True  # Skip confirmation in wizard mode
    }
    return {k: v for k, v in params.items() if v is not None}


# Add command groups
cli.add_command(download.download)
cli.add_command(config.config)
cli.add_command(providers.providers)
cli.add_command(help_command)
cli.add_command(install_completion)
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