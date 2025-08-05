import pytest
from datetime import datetime
from unittest.mock import patch

from vortex.exceptions.templates import (
    ErrorMessageTemplates,
    RecoverySuggestions,
    ErrorFormatter,
    ErrorCodes,
    create_standardized_error
)


class TestErrorMessageTemplates:
    def test_provider_error_templates(self):
        """Test provider error message templates."""
        assert ErrorMessageTemplates.PROVIDER_ERROR == "Provider {provider}: {message}"
        assert ErrorMessageTemplates.PROVIDER_AUTH_FAILED == "Provider {provider}: Authentication failed - {details}"
        assert ErrorMessageTemplates.PROVIDER_CONNECTION_FAILED == "Provider {provider}: Connection failed - {details}"
        assert ErrorMessageTemplates.PROVIDER_RATE_LIMITED == "Provider {provider}: Rate limit exceeded ({current}/{limit})"
        assert ErrorMessageTemplates.PROVIDER_DATA_NOT_FOUND == "Provider {provider}: No data found for {symbol} ({period}) from {start_date} to {end_date}"

    def test_config_error_templates(self):
        """Test configuration error message templates."""
        assert ErrorMessageTemplates.CONFIG_ERROR == "Configuration error in {field}: {message}"
        assert ErrorMessageTemplates.CONFIG_MISSING == "Missing required configuration: {field}"
        assert ErrorMessageTemplates.CONFIG_INVALID == "Invalid configuration value for {field}: {value} - {reason}"
        assert ErrorMessageTemplates.CONFIG_FILE_ERROR == "Configuration file error: {file_path} - {details}"

    def test_storage_error_templates(self):
        """Test storage error message templates."""
        assert ErrorMessageTemplates.STORAGE_ERROR == "Storage operation failed: {operation} on {path}"
        assert ErrorMessageTemplates.PERMISSION_ERROR == "Permission denied: Cannot {operation} {path}"
        assert ErrorMessageTemplates.DISK_SPACE_ERROR == "Insufficient disk space: {path} (need {required_space})"
        assert ErrorMessageTemplates.FILE_NOT_FOUND == "File not found: {path}"

    def test_cli_error_templates(self):
        """Test CLI error message templates."""
        assert ErrorMessageTemplates.CLI_ERROR == "Command error: {message}"
        assert ErrorMessageTemplates.INVALID_ARGUMENT == "Invalid argument '{argument}': {reason}"
        assert ErrorMessageTemplates.MISSING_ARGUMENT == "Missing required argument: {argument}"
        assert ErrorMessageTemplates.COMMAND_FAILED == "Command '{command}' failed: {reason}"

    def test_plugin_error_templates(self):
        """Test plugin error message templates."""
        assert ErrorMessageTemplates.PLUGIN_ERROR == "Plugin '{plugin}': {message}"
        assert ErrorMessageTemplates.PLUGIN_NOT_FOUND == "Plugin '{plugin}' not found - Available: {available_plugins}"
        assert ErrorMessageTemplates.PLUGIN_LOAD_ERROR == "Failed to load plugin '{plugin}': {details}"
        assert ErrorMessageTemplates.PLUGIN_CONFIG_ERROR == "Plugin '{plugin}' configuration error: {details}"

    def test_instrument_error_templates(self):
        """Test instrument error message templates."""
        assert ErrorMessageTemplates.INSTRUMENT_ERROR == "Instrument '{symbol}': {message}"
        assert ErrorMessageTemplates.INVALID_SYMBOL == "Invalid symbol '{symbol}': {reason}"
        assert ErrorMessageTemplates.UNSUPPORTED_INSTRUMENT == "Unsupported instrument type '{instrument_type}' for provider {provider}"


class TestRecoverySuggestions:
    def test_for_auth_error(self):
        """Test authentication error recovery suggestions."""
        suggestions = RecoverySuggestions.for_auth_error("barchart")
        
        assert len(suggestions) == 4
        assert "Verify your barchart credentials are correct and active" in suggestions
        assert "Run: vortex config --provider barchart --set-credentials" in suggestions
        assert "Check barchart service status at their website" in suggestions
        assert "Wait a few minutes and try again (temporary server issues)" in suggestions

    def test_for_connection_error(self):
        """Test connection error recovery suggestions."""
        suggestions = RecoverySuggestions.for_connection_error("yahoo")
        
        assert len(suggestions) == 4
        assert "Check your internet connection" in suggestions
        assert "Verify yahoo service is accessible" in suggestions
        assert "Check firewall and proxy settings" in suggestions
        assert "Try again in a few minutes (temporary network issues)" in suggestions

    def test_for_permission_error(self):
        """Test permission error recovery suggestions."""
        path = "/data/output"
        suggestions = RecoverySuggestions.for_permission_error(path)
        
        assert len(suggestions) == 4
        assert f"Check file permissions for: {path}" in suggestions
        assert f"Run: chmod 755 '{path}' (Unix/Linux/Mac)" in suggestions
        assert "Ensure Vortex has write access to the directory" in suggestions
        assert "Try running with appropriate permissions or as administrator" in suggestions

    def test_for_config_error(self):
        """Test configuration error recovery suggestions."""
        field = "output_directory"
        suggestions = RecoverySuggestions.for_config_error(field)
        
        assert len(suggestions) == 4
        assert f"Check the '{field}' configuration setting" in suggestions
        assert "Run: vortex config --show to view current configuration" in suggestions
        assert f"Edit configuration file or use: vortex config --set {field}=<value>" in suggestions
        assert "Use: vortex config --help for configuration options" in suggestions

    def test_for_disk_space_error(self):
        """Test disk space error recovery suggestions."""
        path = "/var/data"
        suggestions = RecoverySuggestions.for_disk_space_error(path)
        
        assert len(suggestions) == 4
        assert f"Free up disk space in: {path}" in suggestions
        assert "Choose a different output directory with more space" in suggestions
        assert "Clean up old data files if no longer needed" in suggestions
        assert "Check disk usage with: df -h (Unix/Linux/Mac) or dir (Windows)" in suggestions


class TestErrorFormatter:
    def test_format_message_success(self):
        """Test successful message formatting."""
        template = "Provider {provider}: {message}"
        result = ErrorFormatter.format_message(
            template, 
            provider="barchart", 
            message="Authentication failed"
        )
        
        assert result == "Provider barchart: Authentication failed"

    def test_format_message_missing_variable(self):
        """Test message formatting with missing template variable."""
        template = "Provider {provider}: {missing_var}"
        result = ErrorFormatter.format_message(template, provider="barchart")
        
        assert "Error formatting message template" in result
        assert "missing variable" in result

    def test_format_context_summary_empty(self):
        """Test context summary formatting with empty context."""
        result = ErrorFormatter.format_context_summary({})
        assert result == ""

    def test_format_context_summary_with_values(self):
        """Test context summary formatting with various value types."""
        context = {
            "provider": "barchart",
            "symbol": "GC",
            "count": 42,
            "active": True,
            "none_value": None
        }
        
        result = ErrorFormatter.format_context_summary(context)
        
        assert "provider: barchart" in result
        assert "symbol: GC" in result
        assert "count: 42" in result
        assert "active: True" in result
        assert "none_value" not in result  # None values should be filtered out

    def test_format_context_summary_with_datetime(self):
        """Test context summary formatting with datetime objects."""
        test_date = datetime(2024, 1, 15, 14, 30, 45)
        context = {"timestamp": test_date}
        
        result = ErrorFormatter.format_context_summary(context)
        
        assert "timestamp: 2024-01-15 14:30:45" in result

    def test_format_context_summary_with_list(self):
        """Test context summary formatting with list/tuple values."""
        context = {
            "symbols": ["GC", "ES", "CL"],
            "coordinates": (10, 20, 30)
        }
        
        result = ErrorFormatter.format_context_summary(context)
        
        assert "symbols: GC, ES, CL" in result
        assert "coordinates: 10, 20, 30" in result

    def test_format_recovery_actions_empty(self):
        """Test recovery actions formatting with empty list."""
        result = ErrorFormatter.format_recovery_actions([])
        assert result == "No specific recovery suggestions available"

    def test_format_recovery_actions_single(self):
        """Test recovery actions formatting with single suggestion."""
        suggestions = ["Check your credentials"]
        result = ErrorFormatter.format_recovery_actions(suggestions)
        
        assert result == "Check your credentials"

    def test_format_recovery_actions_multiple(self):
        """Test recovery actions formatting with multiple suggestions."""
        suggestions = [
            "Check your credentials",
            "Verify network connection",
            "Try again later"
        ]
        
        result = ErrorFormatter.format_recovery_actions(suggestions)
        
        assert "1. Check your credentials" in result
        assert "2. Verify network connection" in result
        assert "3. Try again later" in result
        assert result.count("\n") == 2  # Two newlines for three items


class TestErrorCodes:
    def test_config_error_codes(self):
        """Test configuration error codes."""
        assert ErrorCodes.CONFIG_MISSING == "CONFIG_001"
        assert ErrorCodes.CONFIG_INVALID == "CONFIG_002"
        assert ErrorCodes.CONFIG_FILE_ERROR == "CONFIG_003"
        assert ErrorCodes.CONFIG_VALIDATION_ERROR == "CONFIG_004"

    def test_provider_error_codes(self):
        """Test provider error codes."""
        assert ErrorCodes.PROVIDER_AUTH_FAILED == "PROVIDER_001"
        assert ErrorCodes.PROVIDER_CONNECTION_FAILED == "PROVIDER_002"
        assert ErrorCodes.PROVIDER_RATE_LIMITED == "PROVIDER_003"
        assert ErrorCodes.PROVIDER_DATA_NOT_FOUND == "PROVIDER_004"
        assert ErrorCodes.PROVIDER_ALLOWANCE_EXCEEDED == "PROVIDER_005"

    def test_storage_error_codes(self):
        """Test storage error codes."""
        assert ErrorCodes.STORAGE_PERMISSION_DENIED == "STORAGE_001"
        assert ErrorCodes.STORAGE_DISK_SPACE == "STORAGE_002"
        assert ErrorCodes.STORAGE_FILE_NOT_FOUND == "STORAGE_003"
        assert ErrorCodes.STORAGE_IO_ERROR == "STORAGE_004"

    def test_cli_error_codes(self):
        """Test CLI error codes."""
        assert ErrorCodes.CLI_INVALID_ARGUMENT == "CLI_001"
        assert ErrorCodes.CLI_MISSING_ARGUMENT == "CLI_002"
        assert ErrorCodes.CLI_COMMAND_FAILED == "CLI_003"
        assert ErrorCodes.CLI_USER_ABORT == "CLI_004"

    def test_plugin_error_codes(self):
        """Test plugin error codes."""
        assert ErrorCodes.PLUGIN_NOT_FOUND == "PLUGIN_001"
        assert ErrorCodes.PLUGIN_LOAD_ERROR == "PLUGIN_002"
        assert ErrorCodes.PLUGIN_VALIDATION_ERROR == "PLUGIN_003"
        assert ErrorCodes.PLUGIN_CONFIG_ERROR == "PLUGIN_004"

    def test_instrument_error_codes(self):
        """Test instrument error codes."""
        assert ErrorCodes.INSTRUMENT_INVALID == "INSTRUMENT_001"
        assert ErrorCodes.INSTRUMENT_UNSUPPORTED == "INSTRUMENT_002"

    def test_system_error_codes(self):
        """Test system error codes."""
        assert ErrorCodes.SYSTEM_IMPORT_ERROR == "SYSTEM_001"
        assert ErrorCodes.SYSTEM_DEPENDENCY_ERROR == "SYSTEM_002"
        assert ErrorCodes.SYSTEM_UNEXPECTED_ERROR == "SYSTEM_003"


class TestCreateStandardizedError:
    @patch('vortex.exceptions.templates.datetime')
    def test_create_standardized_error_basic(self, mock_datetime):
        """Test basic standardized error creation."""
        # Mock datetime.now()
        fixed_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        
        result = create_standardized_error(
            template=ErrorMessageTemplates.PROVIDER_ERROR,
            error_code=ErrorCodes.PROVIDER_AUTH_FAILED,
            provider="barchart",
            message="Invalid credentials"
        )
        
        assert result["message"] == "Provider barchart: Invalid credentials"
        assert result["error_code"] == "PROVIDER_001"
        assert result["recovery_suggestions"] == []
        assert result["context"] == {"provider": "barchart"}
        assert result["timestamp"] == fixed_time.isoformat()

    @patch('vortex.exceptions.templates.datetime')
    def test_create_standardized_error_with_suggestions(self, mock_datetime):
        """Test standardized error creation with recovery suggestions."""
        fixed_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        
        suggestions = ["Check credentials", "Try again"]
        
        result = create_standardized_error(
            template=ErrorMessageTemplates.CONFIG_MISSING,
            error_code=ErrorCodes.CONFIG_MISSING,
            recovery_suggestions=suggestions,
            field="api_key"
        )
        
        assert result["message"] == "Missing required configuration: api_key"
        assert result["error_code"] == "CONFIG_001"
        assert result["recovery_suggestions"] == suggestions
        assert result["context"] == {"field": "api_key"}

    @patch('vortex.exceptions.templates.datetime')
    def test_create_standardized_error_filters_message_from_context(self, mock_datetime):
        """Test that 'message' is filtered out of context."""
        fixed_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        
        result = create_standardized_error(
            template=ErrorMessageTemplates.CLI_ERROR,
            error_code=ErrorCodes.CLI_INVALID_ARGUMENT,
            message="Invalid argument",  # This should be filtered from context
            argument="--invalid",
            other_field="value"
        )
        
        assert result["message"] == "Command error: Invalid argument"
        assert result["context"] == {"argument": "--invalid", "other_field": "value"}
        assert "message" not in result["context"]

    @patch('vortex.exceptions.templates.datetime')
    def test_create_standardized_error_with_complex_template(self, mock_datetime):
        """Test standardized error creation with complex template variables."""
        fixed_time = datetime(2024, 1, 15, 12, 0, 0)
        mock_datetime.now.return_value = fixed_time
        
        result = create_standardized_error(
            template=ErrorMessageTemplates.PROVIDER_DATA_NOT_FOUND,
            error_code=ErrorCodes.PROVIDER_DATA_NOT_FOUND,
            provider="yahoo",
            symbol="AAPL",
            period="1d",
            start_date="2024-01-01",
            end_date="2024-01-31"
        )
        
        expected_message = "Provider yahoo: No data found for AAPL (1d) from 2024-01-01 to 2024-01-31"
        assert result["message"] == expected_message
        assert result["context"]["provider"] == "yahoo"
        assert result["context"]["symbol"] == "AAPL"
        assert result["context"]["period"] == "1d"