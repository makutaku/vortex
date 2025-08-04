#!/usr/bin/env python3
"""Vortex CLI main entry point.

Modern command-line interface for financial data download automation.

This refactored version uses clean dependency injection to eliminate complex
import handling and provide consistent fallback behavior.
"""

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

from . import __version__
from .error_handler import create_error_handler, handle_cli_exceptions
from .dependencies import get_dependency, is_available, get_availability_summary

def setup_logging(config_file: Optional[Path] = None, verbose: int = 0) -> None:
    """Set up logging using Vortex configuration system."""
    # Set up fallback logging first
    logging.basicConfig(
        level=logging.DEBUG if verbose > 1 else logging.INFO if verbose else logging.WARNING,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    fallback_logger = logging.getLogger("vortex.cli")
    
    # Try to use advanced configuration if available
    if not is_available('config'):
        if verbose > 0:
            fallback_logger.debug("Using fallback logging (config module not available)")
        return
    
    try:
        # Use dependency injection to get config components
        ConfigManager = get_dependency('config', 'ConfigManager')
        configure_logging_from_manager = get_dependency('config', 'configure_logging_from_manager')
        get_logger = get_dependency('config', 'get_logger')
        
        if ConfigManager and configure_logging_from_manager and get_logger:
            config_manager = ConfigManager(config_file)
            configure_logging_from_manager(config_manager, service_name="vortex-cli", version=__version__)
            
            logger = get_logger("vortex.cli")
            logger.info("Vortex CLI started", version=__version__, verbose_level=verbose)
        else:
            if verbose > 0:
                fallback_logger.debug("Config components not fully available, using fallback logging")
    
    except Exception as e:
        if verbose > 0:
            fallback_logger.debug(f"Using fallback logging configuration: {e}")

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
    
    # Configure UX based on options using dependency injection
    get_ux_func = get_dependency('ux', 'get_ux')
    ux = get_ux_func() if get_ux_func else None
    
    if ux:
        ux.set_quiet(verbose == 0 and not ctx.invoked_subcommand)
        ux.set_force_yes(dry_run)
    
    # If no command provided, show enhanced welcome
    if ctx.invoked_subcommand is None:
        show_welcome(ux)

def show_welcome(ux):
    """Show enhanced welcome message."""
    if not ux:
        # Fallback welcome message
        print(f"\n🚀 Vortex v{__version__}")
        print("Financial data download automation tool")
        print("\nGet Started: vortex download --symbol AAPL")
        print("Help: vortex --help")
        return
    
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
    
    # Show helpful tips if help system available
    try:
        from .help import get_help_system
        help_system = get_help_system()
        help_system.show_tips(2)
    except ImportError:
        pass  # Skip tips if help system unavailable

@cli.command()
@click.pass_context
def wizard(ctx: click.Context):
    """Interactive setup and command wizard."""
    # Get UX and wizard using dependency injection
    get_ux_func = get_dependency('ux', 'get_ux')
    CommandWizard = get_dependency('ux', 'CommandWizard')
    
    if not get_ux_func or not CommandWizard:
        click.echo("❌ Interactive wizard unavailable - missing dependencies.")
        click.echo("💡 Install with: pip install -e . or uv pip install -e .")
        return
    
    ux = get_ux_func()
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
            # Execute the download command if available
            commands = get_dependency('commands')
            if commands and commands.get('download'):
                ctx.invoke(commands['download'].download, **_convert_wizard_config_to_params(config))
            else:
                click.echo("❌ Download command unavailable")
    
    elif action == "Configure providers":
        config = command_wizard.run_config_wizard()
        if config.get("provider"):
            # Execute the config command if available
            commands = get_dependency('commands')
            if commands and commands.get('config'):
                ctx.invoke(commands['config'].config, provider=config["provider"], set_credentials=True)
            else:
                click.echo("❌ Config command unavailable")
    
    elif action == "View help":
        try:
            from .help import get_help_system
            help_system = get_help_system()
            help_system.show_quick_start()
        except ImportError:
            click.echo("📚 Help: vortex --help")
    
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

def register_commands():
    """Register commands using dependency injection."""
    commands = get_dependency('commands')
    
    if commands:
        # Register available commands
        if commands.get('download'):
            cli.add_command(commands['download'].download)
        if commands.get('config'):
            cli.add_command(commands['config'].config)
        if commands.get('providers'):
            cli.add_command(commands['providers'].providers)
        if commands.get('validate'):
            cli.add_command(commands['validate'].validate)
        if commands.get('help_command'):
            cli.add_command(commands['help_command'])
        if commands.get('install_completion'):
            cli.add_command(commands['install_completion'])
    else:
        # Add fallback commands that inform about missing dependencies
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
    resilience_commands = get_dependency('resilience_commands')
    if resilience_commands and resilience_commands.get('resilience'):
        cli.add_command(resilience_commands['resilience'].resilience)
        cli.add_command(resilience_commands['resilience'].resilience_status)

# Register commands when the module is imported
register_commands()

def main() -> None:
    """Main entry point for the CLI."""
    # Get dependencies for error handler
    rich_console = get_dependency('rich', 'Console')
    console = rich_console() if rich_console else None
    config_available = is_available('config')
    get_logger_func = get_dependency('config', 'get_logger') if config_available else None
    
    # Create configured error handler
    error_handler = create_error_handler(
        rich_available=bool(rich_console),
        console=console,
        config_available=config_available,
        get_logger_func=get_logger_func
    )
    
    # Use centralized error handling
    handle_cli_exceptions(error_handler, cli)

if __name__ == "__main__":
    main()