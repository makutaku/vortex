"""
CLI-related exceptions.

All exceptions related to command-line interface usage and validation.
"""

from typing import Optional

from .base import VortexError


class CLIError(VortexError):
    """Base class for CLI-related errors."""


class InvalidCommandError(CLIError):
    """Raised when CLI command usage is invalid."""

    def __init__(self, command: str, reason: str):
        from .base import ExceptionContext

        message = f"Invalid command usage: {reason}"
        help_text = f"Use 'vortex {command} --help' for correct usage"
        context = ExceptionContext(help_text=help_text, error_code="INVALID_COMMAND")
        super().__init__(message, context)


class MissingArgumentError(CLIError):
    """Raised when required CLI arguments are missing."""

    def __init__(self, argument: str, command: str):
        from .base import ExceptionContext

        message = f"Missing required argument: {argument}"
        help_text = f"Use 'vortex {command} --help' to see all required arguments"
        context = ExceptionContext(help_text=help_text, error_code="MISSING_ARGUMENT")
        super().__init__(message, context)


class UserAbortError(CLIError):
    """Raised when user explicitly aborts an operation."""

    def __init__(self, reason: Optional[str] = None):
        from .base import ExceptionContext

        message = "Operation aborted by user"
        if reason:
            message += f": {reason}"
        context = ExceptionContext(error_code="USER_ABORT")
        super().__init__(message, context)
