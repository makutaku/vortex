#!/usr/bin/env python3
"""Vortex CLI main entry point.

Modern command-line interface for financial data download automation.

This is the restored main CLI module that maintains the original structure
while keeping the benefits of the refactored components for logging and exceptions.
"""

import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from ..exceptions import (
    VortexError, CLIError, ConfigurationError, DataProviderError,
    DataStorageError, InstrumentError, AuthenticationError,
    ConnectionError as VortexConnectionError, PermissionError as VortexPermissionError
)

# Optional imports with fallbacks
try:
    from ..config import ConfigManager
    from ..logging_integration import configure_logging_from_manager, get_logger, run_health_checks
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False

# Optional resilience imports
try:
    from ..resilience.correlation import CorrelationIdManager, with_correlation
    from ..resilience.circuit_breaker import get_circuit_breaker_stats
    from ..resilience.recovery import ErrorRecoveryManager
    RESILIENCE_IMPORTS_AVAILABLE = True
except ImportError:
    RESILIENCE_IMPORTS_AVAILABLE = False
    # Dummy implementations to prevent errors
    def with_correlation(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    
    class CorrelationIdManager:
        @staticmethod
        def get_current_id():
            return None

try:
    from rich.console import Console
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

from . import __version__
from .error_handler import create_error_handler, handle_cli_exceptions

# Lazy import command modules to avoid dependency issues
def _import_commands():
    """Lazy import of command modules."""
    try:
        from .commands import download, config, providers, validate
        from .help import help as help_command
        from .completion import install_completion
        return download, config, providers, validate, help_command, install_completion, True
    except ImportError as e:
        return None, None, None, None, None, None, False

def _import_ux():
    """Lazy import of UX module."""
    try:
        from .ux import get_ux, CommandWizard
        return get_ux, CommandWizard, True
    except ImportError:
        # Fallback UX implementation
        def get_ux():
            class DummyUX:
                def set_quiet(self, quiet): pass
                def set_force_yes(self, force): pass
                def print_panel(self, text, title="", style=""):
                    print(f"\n{title}\n{text}\n")
            return DummyUX()
        
        class DummyWizard:
            def __init__(self, ux): pass
            def run_download_wizard(self): return {}
            def run_config_wizard(self): return {}
        
        return get_ux, DummyWizard, False

# Optional resilience commands
def _import_resilience():
    try:
        from .commands import resilience
        return resilience, True
    except ImportError:
        return None, False

# Get UX functions
get_ux, CommandWizard, UX_AVAILABLE = _import_ux()

def setup_logging(config_file: Optional[Path] = None, verbose: int = 0) -> None:
    """Set up logging using Vortex configuration system."""
    # Set up fallback logging first to avoid missing log messages
    import logging
    logging.basicConfig(
        level=logging.DEBUG if verbose > 1 else logging.INFO if verbose else logging.WARNING,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    fallback_logger = logging.getLogger("vortex.cli")
    
    if not CONFIG_AVAILABLE:
        if verbose > 0:
            fallback_logger.debug("Using fallback logging (config module not available)")
        return
    
    try:
        # Try to load configuration and set up advanced logging
        config_manager = ConfigManager(config_file)
        configure_logging_from_manager(config_manager, service_name="vortex-cli", version=__version__)
        
        # Get logger for CLI - this will use advanced logging if successful
        logger = get_logger("vortex.cli")
        logger.info("Vortex CLI started", version=__version__, verbose_level=verbose)
        
    except Exception as e:
        # Continue with fallback logging - no warning needed as this is expected in containers
        if verbose > 0:  # Only show warning in verbose mode
            fallback_logger.debug(f"Using fallback logging configuration (advanced config not available: {e})")

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
        vortex download --symbol AAPL GOOGL              # Uses yahoo (free, default)
        vortex download -s TSLA --start-date 2024-01-01  # Uses yahoo (free, default)
        vortex download -p barchart --symbol GC          # Premium data (requires subscription)
        vortex providers --test
        
    \b
    Installation (uv recommended):
        curl -LsSf https://astral.sh/uv/install.sh | sh
        uv pip install -e .
        
    \b
    Quick Start (Free Data):
        vortex download --symbol AAPL                     # No setup required!
        vortex download -s TSLA MSFT GOOGL --yes         # Download multiple stocks
        
    \b
    Premium Data Setup:
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
        "**Get Started Instantly (No Setup Required!):**\n"
        "• `vortex download --symbol AAPL` - Download Apple stock data\n"
        "• `vortex download -s TSLA MSFT` - Download multiple stocks\n"
        "• `vortex download -s GOOGL --start-date 2024-01-01` - Historical data\n\n"
        "**Other Commands:**\n"
        "• `vortex wizard` - Interactive setup wizard\n"
        "• `vortex providers --list` - Show all data providers\n"
        "• `vortex help quickstart` - Quick start guide",
        title="Welcome to Vortex - Free Data Ready!",
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

# Lazy command registration function
def _register_commands():
    """Register commands with lazy loading."""
    download, config, providers, validate, help_command, install_completion, commands_available = _import_commands()
    
    if commands_available:
        cli.add_command(download.download)
        cli.add_command(config.config)
        cli.add_command(providers.providers)
        cli.add_command(help_command)
        cli.add_command(install_completion)
        cli.add_command(validate.validate)
    else:
        # Add dummy commands that inform about missing dependencies
        @cli.command()
        def download():
            """Download financial data (requires dependencies)."""
            click.echo("❌ Download command unavailable - missing dependencies.")
            click.echo("💡 Install with: pip install -e . or uv pip install -e .")
        
        @cli.command()
        def config():
            """Configure providers (requires dependencies)."""
            click.echo("❌ Config command unavailable - missing dependencies.")
            click.echo("💡 Install with: pip install -e . or uv pip install -e .")
            
        @cli.command()
        def providers():
            """Manage data providers (requires dependencies)."""
            click.echo("❌ Providers command unavailable - missing dependencies.")
            click.echo("💡 Install with: pip install -e . or uv pip install -e .")
        
        @cli.command()
        def validate():
            """Validate data (requires dependencies)."""
            click.echo("❌ Validate command unavailable - missing dependencies.")
            click.echo("💡 Install with: pip install -e . or uv pip install -e .")
    
    # Add resilience commands if available
    resilience, resilience_available = _import_resilience()
    if resilience_available:
        cli.add_command(resilience.resilience)
        cli.add_command(resilience.resilience_status)

# Register commands when the module is imported
_register_commands()

def main() -> None:
    """Main entry point for the CLI."""
    # Create configured error handler
    error_handler = create_error_handler(
        rich_available=RICH_AVAILABLE,
        console=console,
        config_available=CONFIG_AVAILABLE,
        get_logger_func=get_logger if CONFIG_AVAILABLE else None
    )
    
    # Use centralized error handling
    handle_cli_exceptions(error_handler, cli)

if __name__ == "__main__":
    main()