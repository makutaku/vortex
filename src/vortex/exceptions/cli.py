"""
CLI-related exceptions.

All exceptions related to command-line interface usage and validation.
"""

from typing import Optional

from .base import VortexError


class CLIError(VortexError):
    """Base class for CLI-related errors."""
    pass


class InvalidCommandError(CLIError):
    """Raised when CLI command usage is invalid."""
    
    def __init__(self, command: str, reason: str):
        message = f"Invalid command usage: {reason}"
        help_text = f"Use 'vortex {command} --help' for correct usage"
        super().__init__(message, help_text, "INVALID_COMMAND")


class MissingArgumentError(CLIError):
    """Raised when required CLI arguments are missing."""
    
    def __init__(self, argument: str, command: str):
        message = f"Missing required argument: {argument}"
        help_text = f"Use 'vortex {command} --help' to see all required arguments"
        super().__init__(message, help_text, "MISSING_ARGUMENT")


class UserAbortError(CLIError):
    """Raised when user explicitly aborts an operation."""
    
    def __init__(self, reason: Optional[str] = None):
        message = "Operation aborted by user"
        if reason:
            message += f": {reason}"
        super().__init__(message, error_code="USER_ABORT")