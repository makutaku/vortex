"""
Centralized error handling for the CLI.

Provides consistent error display and logging across all CLI commands.
"""

import logging
import sys

from ..exceptions import (
    VortexError, CLIError, ConfigurationError, DataProviderError,
    DataStorageError, InstrumentError, AuthenticationError,
    ConnectionError as VortexConnectionError, PermissionError as VortexPermissionError
)
from ..logging_integration import get_logger

try:
    from rich.console import Console
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None


def handle_cli_errors(func):
    """Decorator to handle all CLI errors with proper formatting and exit codes."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            _handle_keyboard_interrupt()
        except AuthenticationError as e:
            _handle_authentication_error(e)
        except ConfigurationError as e:
            _handle_configuration_error(e)
        except VortexConnectionError as e:
            _handle_connection_error(e)
        except VortexPermissionError as e:
            _handle_permission_error(e)
        except DataStorageError as e:
            _handle_storage_error(e)
        except DataProviderError as e:
            _handle_provider_error(e)
        except InstrumentError as e:
            _handle_instrument_error(e)
        except CLIError as e:
            _handle_cli_error(e)
        except VortexError as e:
            _handle_vortex_error(e)
        except (OSError, IOError) as e:
            _handle_system_error(e)
        except ImportError as e:
            _handle_import_error(e)
        except Exception as e:
            _handle_unexpected_error(e)
    return wrapper


def _print_error(message: str, style: str = "red"):
    """Print error message with appropriate formatting."""
    if RICH_AVAILABLE and console:
        console.print(f"[{style}]{message}[/{style}]")
    else:
        print(message)


def _print_help(message: str):
    """Print help message with appropriate formatting."""
    if RICH_AVAILABLE and console:
        console.print(f"[blue]💡 {message}[/blue]")
    else:
        print(f"💡 {message}")


def _print_action(message: str):
    """Print action suggestion with appropriate formatting."""
    if RICH_AVAILABLE and console:
        console.print(f"[green]🔧 Action: {message}[/green]")
    else:
        print(f"🔧 Action: {message}")


def _print_context(context_items: list):
    """Print context information with appropriate formatting."""
    if RICH_AVAILABLE and console:
        console.print(f"[dim]📋 Context: {', '.join(context_items)}[/dim]")
    else:
        print(f"📋 Context: {', '.join(context_items)}")


def _print_error_id(error_id: str):
    """Print error ID with appropriate formatting."""
    if RICH_AVAILABLE and console:
        console.print(f"[dim]🔍 Error ID: {error_id}[/dim]")
    else:
        print(f"🔍 Error ID: {error_id}")


def _handle_keyboard_interrupt():
    """Handle keyboard interrupt (Ctrl+C)."""
    _print_error("\nOperation cancelled by user", "yellow")
    sys.exit(1)


def _handle_authentication_error(e: AuthenticationError):
    """Handle authentication failures with comprehensive context."""
    _print_error(f"🔐 Authentication Failed: {e.message}")
    if e.help_text:
        _print_help(e.help_text)
    if e.user_action:
        _print_action(e.user_action)
    if e.technical_details:
        if RICH_AVAILABLE and console:
            console.print(f"[dim]📋 Details: {e.technical_details}[/dim]")
        else:
            print(f"📋 Details: {e.technical_details}")
    _print_error_id(e.correlation_id)
    
    # Enhanced logging with error context
    logger = get_logger("vortex.cli.error")
    logger.error("Authentication error occurred", 
                error_dict=e.to_dict(),
                correlation_id=e.correlation_id)
    sys.exit(2)


def _handle_configuration_error(e: ConfigurationError):
    """Handle configuration issues with specific guidance."""
    _print_error(f"⚙️  Configuration Error: {e.message}")
    if e.help_text:
        _print_help(e.help_text)
    
    logging.error(f"Configuration error ({e.error_code}): {e.message}")
    sys.exit(3)


def _handle_connection_error(e: VortexConnectionError):
    """Handle network/connection issues."""
    _print_error(f"🌐 Connection Error: {e.message}")
    if e.help_text:
        _print_help(e.help_text)
    
    logging.error(f"Connection error for provider {e.provider}: {e.message}")
    sys.exit(4)


def _handle_permission_error(e: VortexPermissionError):
    """Handle permission/file access issues."""
    _print_error(f"🔒 Permission Error: {e.message}")
    if e.help_text:
        _print_help(e.help_text)
    
    logging.error(f"Permission error ({e.error_code}): {e.message}")
    sys.exit(5)


def _handle_storage_error(e: DataStorageError):
    """Handle data storage issues."""
    _print_error(f"💾 Storage Error: {e.message}")
    if e.help_text:
        _print_help(e.help_text)
    
    logging.error(f"Storage error ({e.error_code}): {e.message}")
    sys.exit(6)


def _handle_provider_error(e: DataProviderError):
    """Handle data provider issues."""
    _print_error(f"📊 Provider Error: {e.message}")
    if e.help_text:
        _print_help(e.help_text)
    
    logging.error(f"Data provider error for {e.provider} ({e.error_code}): {e.message}")
    sys.exit(7)


def _handle_instrument_error(e: InstrumentError):
    """Handle instrument/symbol issues."""
    _print_error(f"📈 Instrument Error: {e.message}")
    if e.help_text:
        _print_help(e.help_text)
    
    logging.error(f"Instrument error ({e.error_code}): {e.message}")
    sys.exit(8)


def _handle_cli_error(e: CLIError):
    """Handle CLI usage errors."""
    _print_error(f"⌨️  Command Error: {e.message}")
    if e.help_text:
        _print_help(e.help_text)
    
    logging.error(f"CLI error ({e.error_code}): {e.message}")
    sys.exit(9)


def _handle_vortex_error(e: VortexError):
    """Handle any other Vortex exceptions with full context."""
    _print_error(f"❌ Error: {e.message}")
    if e.help_text:
        _print_help(e.help_text)
    if e.user_action:
        _print_action(e.user_action)
    if e.context:
        context_items = [f"{k}: {v}" for k, v in e.context.items() if v is not None]
        if context_items:
            _print_context(context_items)
    _print_error_id(e.correlation_id)
    
    # Enhanced logging with full error context
    logger = get_logger("vortex.cli.error")
    logger.error("Vortex error occurred", 
                error_dict=e.to_dict(),
                correlation_id=e.correlation_id)
    sys.exit(10)


def _handle_system_error(e: Exception):
    """Handle system-level file/network errors."""
    _print_error(f"💻 System Error: {e}")
    _print_help("Check file permissions, disk space, and network connectivity")
    
    logging.error(f"System error: {e}")
    sys.exit(11)


def _handle_import_error(e: ImportError):
    """Handle missing dependencies."""
    _print_error(f"📦 Dependency Error: {e}")
    _print_help("Try running: uv pip install -e . or pip install -e .")
    
    logging.error(f"Import error: {e}")
    sys.exit(12)


def _handle_unexpected_error(e: Exception):
    """Handle unexpected exceptions."""
    _print_error(f"🐛 Unexpected Error: {e}")
    if RICH_AVAILABLE and console:
        console.print("[yellow]This may be a bug. Please report it at: https://github.com/makutaku/vortex/issues[/yellow]")
    else:
        print("This may be a bug. Please report it at: https://github.com/makutaku/vortex/issues")
    
    logging.exception("Unexpected error occurred")
    sys.exit(1)