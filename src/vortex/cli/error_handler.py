"""
Centralized error handling for Vortex CLI.

This module provides a unified error handling system that ensures consistent
error reporting, logging, and user experience across all CLI commands.
"""

import sys
import logging
from typing import Optional, Any

from vortex.shared.utils.logging_utils import get_structured_logger

from vortex.shared.exceptions import (
    VortexError, CLIError, ConfigurationError, DataProviderError,
    DataStorageError, InstrumentError, AuthenticationError,
    ConnectionError as VortexConnectionError, PermissionError as VortexPermissionError
)


class CLIErrorHandler:
    """Centralized error handler for Vortex CLI operations."""
    
    def __init__(self, rich_available: bool = False, console: Any = None, 
                 config_available: bool = False, get_logger_func: Optional[callable] = None):
        """Initialize the error handler.
        
        Args:
            rich_available: Whether Rich library is available for enhanced output
            console: Rich console instance if available
            config_available: Whether advanced configuration/logging is available
            get_logger_func: Function to get logger instance if available
        """
        self.rich_available = rich_available
        self.console = console
        self.config_available = config_available
        self.get_logger = get_logger_func
        self.structured_logger = get_structured_logger()
        
    def handle_keyboard_interrupt(self) -> None:
        """Handle user cancellation (Ctrl+C)."""
        if self.rich_available and self.console:
            self.console.print("\n[yellow]Operation cancelled by user[/yellow]")
        else:
            print("\nOperation cancelled by user")
        sys.exit(1)
    
    def handle_authentication_error(self, error: AuthenticationError) -> None:
        """Handle authentication failures with comprehensive context."""
        if self.rich_available and self.console:
            self.console.print(f"[red]🔐 Authentication Failed: {error.message}[/red]")
            if error.help_text:
                self.console.print(f"[blue]💡 {error.help_text}[/blue]")
            if error.user_action:
                self.console.print(f"[green]🔧 Action: {error.user_action}[/green]")
            if error.technical_details:
                self.console.print(f"[dim]📋 Details: {error.technical_details}[/dim]")
            self.console.print(f"[dim]🔍 Error ID: {error.correlation_id}[/dim]")
        else:
            print(f"🔐 Authentication Failed: {error.message}")
            if error.help_text:
                print(f"💡 {error.help_text}")
            if error.user_action:
                print(f"🔧 Action: {error.user_action}")
            print(f"🔍 Error ID: {error.correlation_id}")
        
        self._log_error("Authentication error occurred", error)
        sys.exit(2)
    
    def handle_configuration_error(self, error: ConfigurationError) -> None:
        """Handle configuration issues with specific guidance."""
        if self.rich_available and self.console:
            self.console.print(f"[red]⚙️  Configuration Error: {error.message}[/red]")
            if error.help_text:
                self.console.print(f"[blue]💡 {error.help_text}[/blue]")
        else:
            print(f"⚙️  Configuration Error: {error.message}")
            if error.help_text:
                print(f"💡 {error.help_text}")
        
        self._log_simple_error(f"Configuration error ({error.error_code}): {error.message}")
        sys.exit(3)
    
    def handle_connection_error(self, error: VortexConnectionError) -> None:
        """Handle network/connection issues."""
        if self.rich_available and self.console:
            self.console.print(f"[red]🌐 Connection Error: {error.message}[/red]")
            if error.help_text:
                self.console.print(f"[blue]💡 {error.help_text}[/blue]")
        else:
            print(f"🌐 Connection Error: {error.message}")
            if error.help_text:
                print(f"💡 {error.help_text}")
        
        self._log_simple_error(f"Connection error for provider {error.provider}: {error.message}")
        sys.exit(4)
    
    def handle_permission_error(self, error: VortexPermissionError) -> None:
        """Handle permission/file access issues."""
        if self.rich_available and self.console:
            self.console.print(f"[red]🔒 Permission Error: {error.message}[/red]")
            if error.help_text:
                self.console.print(f"[blue]💡 {error.help_text}[/blue]")
        else:
            print(f"🔒 Permission Error: {error.message}")
            if error.help_text:
                print(f"💡 {error.help_text}")
        
        self._log_simple_error(f"Permission error ({error.error_code}): {error.message}")
        sys.exit(5)
    
    def handle_storage_error(self, error: DataStorageError) -> None:
        """Handle data storage issues."""
        if self.rich_available and self.console:
            self.console.print(f"[red]💾 Storage Error: {error.message}[/red]")
            if error.help_text:
                self.console.print(f"[blue]💡 {error.help_text}[/blue]")
        else:
            print(f"💾 Storage Error: {error.message}")
            if error.help_text:
                print(f"💡 {error.help_text}")
        
        self._log_simple_error(f"Storage error ({error.error_code}): {error.message}")
        sys.exit(6)
    
    def handle_provider_error(self, error: DataProviderError) -> None:
        """Handle data provider issues."""
        if self.rich_available and self.console:
            self.console.print(f"[red]📊 Provider Error: {error.message}[/red]")
            if error.help_text:
                self.console.print(f"[blue]💡 {error.help_text}[/blue]")
        else:
            print(f"📊 Provider Error: {error.message}")
            if error.help_text:
                print(f"💡 {error.help_text}")
        
        self._log_simple_error(f"Data provider error for {error.provider} ({error.error_code}): {error.message}")
        sys.exit(7)
    
    def handle_instrument_error(self, error: InstrumentError) -> None:
        """Handle instrument/symbol issues."""
        if self.rich_available and self.console:
            self.console.print(f"[red]📈 Instrument Error: {error.message}[/red]")
            if error.help_text:
                self.console.print(f"[blue]💡 {error.help_text}[/blue]")
        else:
            print(f"📈 Instrument Error: {error.message}")
            if error.help_text:
                print(f"💡 {error.help_text}")
        
        self._log_simple_error(f"Instrument error ({error.error_code}): {error.message}")
        sys.exit(8)
    
    def handle_cli_error(self, error: CLIError) -> None:
        """Handle CLI usage errors."""
        if self.rich_available and self.console:
            self.console.print(f"[red]⌨️  Command Error: {error.message}[/red]")
            if error.help_text:
                self.console.print(f"[blue]💡 {error.help_text}[/blue]")
        else:
            print(f"⌨️  Command Error: {error.message}")
            if error.help_text:
                print(f"💡 {error.help_text}")
        
        self._log_simple_error(f"CLI error ({error.error_code}): {error.message}")
        sys.exit(9)
    
    def handle_vortex_error(self, error: VortexError) -> None:
        """Handle any other Vortex exceptions with full context."""
        if self.rich_available and self.console:
            self.console.print(f"[red]❌ Error: {error.message}[/red]")
            if error.help_text:
                self.console.print(f"[blue]💡 {error.help_text}[/blue]")
            if error.user_action:
                self.console.print(f"[green]🔧 Action: {error.user_action}[/green]")
            if error.context:
                context_items = [f"{k}: {v}" for k, v in error.context.items() if v is not None]
                if context_items:
                    self.console.print(f"[dim]📋 Context: {', '.join(context_items)}[/dim]")
            self.console.print(f"[dim]🔍 Error ID: {error.correlation_id}[/dim]")
        else:
            print(f"❌ Error: {error.message}")
            if error.help_text:
                print(f"💡 {error.help_text}")
            if error.user_action:
                print(f"🔧 Action: {error.user_action}")
            print(f"🔍 Error ID: {error.correlation_id}")
        
        self._log_error("Vortex error occurred", error)
        sys.exit(10)
    
    def handle_system_error(self, error: Exception) -> None:
        """Handle system-level file/network errors."""
        if self.rich_available and self.console:
            self.console.print(f"[red]💻 System Error: {error}[/red]")
            self.console.print("[blue]💡 Check file permissions, disk space, and network connectivity[/blue]")
        else:
            print(f"💻 System Error: {error}")
            print("💡 Check file permissions, disk space, and network connectivity")
        
        self._log_simple_error(f"System error: {error}")
        sys.exit(11)
    
    def handle_import_error(self, error: ImportError) -> None:
        """Handle missing dependencies."""
        if self.rich_available and self.console:
            self.console.print(f"[red]📦 Dependency Error: {error}[/red]")
            self.console.print("[blue]💡 Try running: uv pip install -e . or pip install -e .[/blue]")
        else:
            print(f"📦 Dependency Error: {error}")
            print("💡 Try running: uv pip install -e . or pip install -e .")
        
        self._log_simple_error(f"Import error: {error}")
        sys.exit(12)
    
    def handle_unexpected_error(self, error: Exception) -> None:
        """Handle unexpected exceptions."""
        if self.rich_available and self.console:
            self.console.print(f"[red]🐛 Unexpected Error: {error}[/red]")
            self.console.print("[yellow]This may be a bug. Please report it at: https://github.com/makutaku/vortex/issues[/yellow]")
        else:
            print(f"🐛 Unexpected Error: {error}")
            print("This may be a bug. Please report it at: https://github.com/makutaku/vortex/issues")
        
        logging.exception("Unexpected error occurred")
        sys.exit(1)
    
    def _log_error(self, message: str, error: VortexError) -> None:
        """Log error with full context using structured logging."""
        try:
            # Use structured logging for enhanced error tracking
            context = {
                "error_code": getattr(error, 'error_code', None),
                "provider": getattr(error, 'provider', None),
                "operation": getattr(error, 'operation', None),
            }
            
            self.structured_logger.log_error(
                error=error,
                message=message,
                correlation_id=getattr(error, 'correlation_id', None),
                context=context,
                operation="cli_operation"
            )
            
            # Also try advanced logging if available
            if self.config_available and self.get_logger:
                try:
                    logger = self.get_logger("vortex.cli.error")
                    logger.error(message, 
                               error_dict=error.to_dict(),
                               correlation_id=error.correlation_id)
                except Exception:
                    pass  # Structured logging already handled it
        except Exception:
            # Ultimate fallback to basic logging
            logging.error(f"{message}: {error.message}")
    
    def _log_simple_error(self, message: str) -> None:
        """Log simple error message."""
        logging.error(message)


def create_error_handler(rich_available: bool = False, console: Any = None, 
                        config_available: bool = False, get_logger_func: Optional[callable] = None) -> CLIErrorHandler:
    """Factory function to create a configured error handler."""
    return CLIErrorHandler(
        rich_available=rich_available,
        console=console,
        config_available=config_available,
        get_logger_func=get_logger_func
    )


def handle_cli_exceptions(error_handler: CLIErrorHandler, func: callable, *args, **kwargs) -> Any:
    """
    Universal exception handler wrapper for CLI operations.
    
    This function wraps CLI operations and handles all exceptions consistently.
    
    Args:
        error_handler: Configured error handler instance
        func: Function to execute
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        The result of the function call
        
    Raises:
        SystemExit: On any handled exception
    """
    try:
        return func(*args, **kwargs)
    except KeyboardInterrupt:
        error_handler.handle_keyboard_interrupt()
    except AuthenticationError as e:
        error_handler.handle_authentication_error(e)
    except ConfigurationError as e:
        error_handler.handle_configuration_error(e)
    except VortexConnectionError as e:
        error_handler.handle_connection_error(e)
    except VortexPermissionError as e:
        error_handler.handle_permission_error(e)
    except DataStorageError as e:
        error_handler.handle_storage_error(e)
    except DataProviderError as e:
        error_handler.handle_provider_error(e)
    except InstrumentError as e:
        error_handler.handle_instrument_error(e)
    except CLIError as e:
        error_handler.handle_cli_error(e)
    except VortexError as e:
        error_handler.handle_vortex_error(e)
    except (OSError, IOError) as e:
        error_handler.handle_system_error(e)
    except ImportError as e:
        error_handler.handle_import_error(e)
    except Exception as e:
        error_handler.handle_unexpected_error(e)