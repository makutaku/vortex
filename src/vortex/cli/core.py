"""
Core CLI functionality and main command group.

Provides the main CLI group definition and command registration.
"""

from pathlib import Path
from typing import Optional

import click

# Import version safely
try:
    from . import __version__
except ImportError:
    __version__ = "unknown"

from .setup import setup_logging
from .welcome import show_welcome
from .wizard import wizard_command
from .error_handlers import handle_cli_errors

# Try to import UX - if it fails, create a dummy
try:
    from .ux import get_ux
except ImportError:
    def get_ux():
        class DummyUX:
            def set_quiet(self, quiet): pass
            def set_force_yes(self, force): pass
        return DummyUX()

# Command imports - these might fail due to missing dependencies
try:
    from .commands import download, config, providers, validate
    from .help import help as help_command
    from .completion import install_completion
    COMMANDS_AVAILABLE = True
except ImportError as e:
    # Create dummy commands if imports fail
    COMMANDS_AVAILABLE = False
    
    # Create basic command structure to prevent CLI from crashing
    import click
    
    @click.command()
    def dummy_command():
        """Command not available due to missing dependencies."""
        click.echo("This command is not available due to missing dependencies.")
        click.echo("Please install required packages: pip install -e .")
    
    # Create dummy modules
    class DummyModule:
        def __init__(self):
            self.download = dummy_command
            self.config = dummy_command
            self.providers = dummy_command
            self.validate = dummy_command
    
    download = DummyModule()
    config = DummyModule()
    providers = DummyModule()
    validate = DummyModule()
    help_command = dummy_command
    install_completion = dummy_command

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

# Optional resilience commands
try:
    from .commands import resilience
    RESILIENCE_COMMANDS_AVAILABLE = True
except ImportError:
    RESILIENCE_COMMANDS_AVAILABLE = False
    resilience = None


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


# Add wizard command
@cli.command()
@click.pass_context  
def wizard(ctx: click.Context):
    """Interactive setup and command wizard."""
    return wizard_command(ctx)


# Register commands at module level (like original code)
if COMMANDS_AVAILABLE:
    cli.add_command(download.download)
    cli.add_command(config.config)
    cli.add_command(providers.providers)
    cli.add_command(help_command)
    cli.add_command(install_completion)
    cli.add_command(validate.validate)
else:
    # Add dummy commands with helpful error messages
    cli.add_command(download.download, name="download")
    cli.add_command(config.config, name="config")
    cli.add_command(providers.providers, name="providers")
    cli.add_command(help_command, name="help")
    cli.add_command(install_completion, name="install-completion")
    cli.add_command(validate.validate, name="validate")

# Add resilience commands if available
if RESILIENCE_COMMANDS_AVAILABLE and resilience:
    cli.add_command(resilience.resilience)
    cli.add_command(resilience.resilience_status)


@handle_cli_errors
def main() -> None:
    """Main entry point for the CLI with error handling."""
    # Execute CLI (commands already registered at module level)
    cli()