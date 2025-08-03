"""
Plugin system exceptions.
"""

from ..exceptions import VortexError


class PluginError(VortexError):
    """Base exception for plugin system errors."""
    
    def __init__(self, message: str, plugin_name: str = None, help_text: str = None):
        self.plugin_name = plugin_name
        super().__init__(
            message=message,
            help_text=help_text,
            error_code="PLUGIN_ERROR"
        )


class PluginNotFoundError(PluginError):
    """Raised when a requested plugin cannot be found."""
    
    def __init__(self, plugin_name: str):
        super().__init__(
            message=f"Provider plugin '{plugin_name}' not found",
            plugin_name=plugin_name,
            help_text=f"Available providers: Use 'vortex providers --list' to see available providers"
        )


class PluginValidationError(PluginError):
    """Raised when plugin validation fails."""
    
    def __init__(self, plugin_name: str, validation_error: str):
        super().__init__(
            message=f"Plugin '{plugin_name}' validation failed: {validation_error}",
            plugin_name=plugin_name,
            help_text="Check plugin configuration and ensure all required dependencies are installed"
        )


class PluginConfigurationError(PluginError):
    """Raised when plugin configuration is invalid."""
    
    def __init__(self, plugin_name: str, config_error: str):
        super().__init__(
            message=f"Plugin '{plugin_name}' configuration error: {config_error}",
            plugin_name=plugin_name,
            help_text=f"Use 'vortex config --provider {plugin_name} --set-credentials' to configure"
        )


class PluginLoadError(PluginError):
    """Raised when plugin loading fails."""
    
    def __init__(self, plugin_name: str, load_error: str):
        super().__init__(
            message=f"Failed to load plugin '{plugin_name}': {load_error}",
            plugin_name=plugin_name,
            help_text="Check that the plugin is properly installed and dependencies are available"
        )