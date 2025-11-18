"""
Standardized error message templates and formatting utilities.

This module provides consistent error message formatting across all Vortex exceptions
to ensure users receive clear, actionable error information.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


class ErrorMessageTemplates:
    """Standardized error message templates for consistent formatting."""

    # Provider error templates
    PROVIDER_ERROR = "Provider {provider}: {message}"
    PROVIDER_AUTH_FAILED = "Provider {provider}: Authentication failed - {details}"
    PROVIDER_CONNECTION_FAILED = "Provider {provider}: Connection failed - {details}"
    PROVIDER_RATE_LIMITED = (
        "Provider {provider}: Rate limit exceeded ({current}/{limit})"
    )
    PROVIDER_DATA_NOT_FOUND = (
        "Provider {provider}: No data found for {symbol} ({period}) "
        "from {start_date} to {end_date}"
    )

    # Configuration error templates
    CONFIG_ERROR = "Configuration error in {field}: {message}"
    CONFIG_MISSING = "Missing required configuration: {field}"
    CONFIG_INVALID = "Invalid configuration value for {field}: {value} - {reason}"
    CONFIG_FILE_ERROR = "Configuration file error: {file_path} - {details}"

    # Storage error templates
    STORAGE_ERROR = "Storage operation failed: {operation} on {path}"
    PERMISSION_ERROR = "Permission denied: Cannot {operation} {path}"
    DISK_SPACE_ERROR = "Insufficient disk space: {path} (need {required_space})"
    FILE_NOT_FOUND = "File not found: {path}"

    # CLI error templates
    CLI_ERROR = "Command error: {message}"
    INVALID_ARGUMENT = "Invalid argument '{argument}': {reason}"
    MISSING_ARGUMENT = "Missing required argument: {argument}"
    COMMAND_FAILED = "Command '{command}' failed: {reason}"

    # Plugin error templates
    PLUGIN_ERROR = "Plugin '{plugin}': {message}"
    PLUGIN_NOT_FOUND = "Plugin '{plugin}' not found - Available: {available_plugins}"
    PLUGIN_LOAD_ERROR = "Failed to load plugin '{plugin}': {details}"
    PLUGIN_CONFIG_ERROR = "Plugin '{plugin}' configuration error: {details}"

    # Instrument error templates
    INSTRUMENT_ERROR = "Instrument '{symbol}': {message}"
    INVALID_SYMBOL = "Invalid symbol '{symbol}': {reason}"
    UNSUPPORTED_INSTRUMENT = (
        "Unsupported instrument type '{instrument_type}' for provider {provider}"
    )


class RecoverySuggestions:
    """Standard recovery suggestions for common error scenarios."""

    @staticmethod
    def for_auth_error(provider: str) -> List[str]:
        """Get recovery suggestions for authentication errors."""
        return [
            f"Verify your {provider} credentials are correct and active",
            f"Run: vortex config --provider {provider} --set-credentials",
            f"Check {provider} service status at their website",
            "Wait a few minutes and try again (temporary server issues)",
        ]

    @staticmethod
    def for_connection_error(provider: str) -> List[str]:
        """Get recovery suggestions for connection errors."""
        return [
            "Check your internet connection",
            f"Verify {provider} service is accessible",
            "Check firewall and proxy settings",
            "Try again in a few minutes (temporary network issues)",
        ]

    @staticmethod
    def for_permission_error(path: str) -> List[str]:
        """Get recovery suggestions for permission errors."""
        return [
            f"Check file permissions for: {path}",
            f"Run: chmod 755 '{path}' (Unix/Linux/Mac)",
            "Ensure Vortex has write access to the directory",
            "Try running with appropriate permissions or as administrator",
        ]

    @staticmethod
    def for_config_error(field: str) -> List[str]:
        """Get recovery suggestions for configuration errors."""
        return [
            f"Check the '{field}' configuration setting",
            "Run: vortex config --show to view current configuration",
            f"Edit configuration file or use: vortex config --set {field}=<value>",
            "Use: vortex config --help for configuration options",
        ]

    @staticmethod
    def for_disk_space_error(path: str) -> List[str]:
        """Get recovery suggestions for disk space errors."""
        return [
            f"Free up disk space in: {path}",
            "Choose a different output directory with more space",
            "Clean up old data files if no longer needed",
            "Check disk usage with: df -h (Unix/Linux/Mac) or dir (Windows)",
        ]


class ErrorFormatter:
    """Utility for formatting error messages with context."""

    @staticmethod
    def format_message(template: str, **kwargs) -> str:
        """Format error message using template and context variables."""
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # If template variable is missing, return a safe fallback
            return f"Error formatting message template: missing variable {e}"

    @staticmethod
    def format_context_summary(context: Dict[str, Any]) -> str:
        """Format context dictionary into a readable summary."""
        if not context:
            return ""

        items = []
        for key, value in context.items():
            if value is not None:
                # Format special types
                if isinstance(value, datetime):
                    value = value.strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(value, (list, tuple)):
                    value = ", ".join(str(v) for v in value)

                items.append(f"{key}: {value}")

        return "; ".join(items)

    @staticmethod
    def format_recovery_actions(suggestions: List[str]) -> str:
        """Format recovery suggestions into a readable list."""
        if not suggestions:
            return "No specific recovery suggestions available"

        if len(suggestions) == 1:
            return suggestions[0]

        formatted_suggestions = []
        for i, suggestion in enumerate(suggestions, 1):
            formatted_suggestions.append(f"{i}. {suggestion}")

        return "\n".join(formatted_suggestions)


class ErrorCodes:
    """Standardized error codes for consistent error categorization."""

    # Configuration errors (CONFIG_xxx)
    CONFIG_MISSING = "CONFIG_001"
    CONFIG_INVALID = "CONFIG_002"
    CONFIG_FILE_ERROR = "CONFIG_003"
    CONFIG_VALIDATION_ERROR = "CONFIG_004"

    # Provider errors (PROVIDER_xxx)
    PROVIDER_AUTH_FAILED = "PROVIDER_001"
    PROVIDER_CONNECTION_FAILED = "PROVIDER_002"
    PROVIDER_RATE_LIMITED = "PROVIDER_003"
    PROVIDER_DATA_NOT_FOUND = "PROVIDER_004"
    PROVIDER_ALLOWANCE_EXCEEDED = "PROVIDER_005"

    # Storage errors (STORAGE_xxx)
    STORAGE_PERMISSION_DENIED = "STORAGE_001"
    STORAGE_DISK_SPACE = "STORAGE_002"
    STORAGE_FILE_NOT_FOUND = "STORAGE_003"
    STORAGE_IO_ERROR = "STORAGE_004"

    # CLI errors (CLI_xxx)
    CLI_INVALID_ARGUMENT = "CLI_001"
    CLI_MISSING_ARGUMENT = "CLI_002"
    CLI_COMMAND_FAILED = "CLI_003"
    CLI_USER_ABORT = "CLI_004"

    # Plugin errors (PLUGIN_xxx)
    PLUGIN_NOT_FOUND = "PLUGIN_001"
    PLUGIN_LOAD_ERROR = "PLUGIN_002"
    PLUGIN_VALIDATION_ERROR = "PLUGIN_003"
    PLUGIN_CONFIG_ERROR = "PLUGIN_004"

    # Instrument errors (INSTRUMENT_xxx)
    INSTRUMENT_INVALID = "INSTRUMENT_001"
    INSTRUMENT_UNSUPPORTED = "INSTRUMENT_002"

    # System errors (SYSTEM_xxx)
    SYSTEM_IMPORT_ERROR = "SYSTEM_001"
    SYSTEM_DEPENDENCY_ERROR = "SYSTEM_002"
    SYSTEM_UNEXPECTED_ERROR = "SYSTEM_003"


def create_standardized_error(
    template: str,
    error_code: str,
    recovery_suggestions: Optional[List[str]] = None,
    **template_vars,
) -> Dict[str, Any]:
    """
    Create a standardized error dictionary with consistent formatting.

    Args:
        template: Error message template
        error_code: Standardized error code
        recovery_suggestions: Optional list of recovery suggestions
        **template_vars: Variables to format into the template

    Returns:
        Dictionary with standardized error information
    """
    formatter = ErrorFormatter()

    return {
        "message": formatter.format_message(template, **template_vars),
        "error_code": error_code,
        "recovery_suggestions": recovery_suggestions or [],
        "context": {k: v for k, v in template_vars.items() if k not in ["message"]},
        "timestamp": datetime.now().isoformat(),
    }
