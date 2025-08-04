"""
Provider plugin registry and dynamic loading system.

This module manages the registration, discovery, and loading of data provider plugins,
both built-in and external.
"""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Optional, Type, Any

from pydantic import BaseModel

from .base import ProviderPlugin, BuiltinProviderPlugin
from ..exceptions import PluginNotFoundError, PluginLoadError, PluginValidationError
from ..data_providers.data_provider import DataProvider
from ..logging_integration import get_module_logger

logger = get_module_logger()


class ProviderRegistry:
    """
    Registry for managing data provider plugins.
    
    Handles plugin discovery, registration, validation, and instantiation.
    Supports both built-in providers and external plugins.
    """
    
    def __init__(self):
        self._plugins: Dict[str, ProviderPlugin] = {}
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        self._initialized = False
    
    def initialize(self):
        """Initialize the registry by loading built-in providers."""
        if self._initialized:
            return
            
        logger.info("Initializing provider plugin registry")
        
        try:
            self._load_builtin_providers()
            self._load_external_providers()
            self._initialized = True
            
            logger.info(f"Loaded {len(self._plugins)} provider plugins", 
                       plugins=list(self._plugins.keys()))
                       
        except Exception as e:
            logger.error(f"Failed to initialize plugin registry: {e}")
            raise PluginLoadError("registry", str(e))
    
    def register_plugin(self, plugin: ProviderPlugin):
        """
        Register a provider plugin.
        
        Args:
            plugin: ProviderPlugin instance to register
            
        Raises:
            PluginValidationError: If plugin validation fails
        """
        try:
            # Validate plugin
            self._validate_plugin(plugin)
            
            plugin_name = plugin.metadata.name.lower()
            
            # Check for conflicts
            if plugin_name in self._plugins:
                existing = self._plugins[plugin_name]
                logger.warning(f"Replacing existing plugin '{plugin_name}' "
                             f"(v{existing.metadata.version}) with v{plugin.metadata.version}")
            
            self._plugins[plugin_name] = plugin
            logger.info(f"Registered plugin '{plugin_name}' v{plugin.metadata.version}")
            
        except Exception as e:
            raise PluginValidationError(plugin.metadata.name if hasattr(plugin, 'metadata') else 'unknown', str(e))
    
    def unregister_plugin(self, name: str):
        """
        Unregister a provider plugin.
        
        Args:
            name: Plugin name to unregister
        """
        name = name.lower()
        if name in self._plugins:
            plugin = self._plugins[name]
            try:
                plugin.cleanup()
            except Exception as e:
                logger.warning(f"Error during plugin cleanup for '{name}': {e}")
            
            del self._plugins[name]
            if name in self._plugin_configs:
                del self._plugin_configs[name]
            
            logger.info(f"Unregistered plugin '{name}'")
    
    def get_plugin(self, name: str) -> ProviderPlugin:
        """
        Get a registered plugin by name.
        
        Args:
            name: Plugin name
            
        Returns:
            ProviderPlugin instance
            
        Raises:
            PluginNotFoundError: If plugin not found
        """
        if not self._initialized:
            self.initialize()
            
        name = name.lower()
        if name not in self._plugins:
            # Try dynamic loading
            self._try_dynamic_load(name)
        
        if name not in self._plugins:
            raise PluginNotFoundError(name)
        
        return self._plugins[name]
    
    def list_plugins(self) -> List[str]:
        """
        List all registered plugin names.
        
        Returns:
            List of plugin names
        """
        if not self._initialized:
            self.initialize()
            
        return list(self._plugins.keys())
    
    def get_plugin_info(self, name: str = None) -> Dict[str, Any]:
        """
        Get information about plugins.
        
        Args:
            name: Specific plugin name, or None for all plugins
            
        Returns:
            Dictionary with plugin information
        """
        if not self._initialized:
            self.initialize()
            
        if name:
            plugin = self.get_plugin(name)
            return {
                "name": plugin.metadata.name,
                "display_name": plugin.metadata.display_name,
                "version": plugin.metadata.version,
                "description": plugin.metadata.description,
                "author": plugin.metadata.author,
                "requires_auth": plugin.metadata.requires_auth,
                "supported_assets": plugin.metadata.supported_assets,
                "rate_limits": plugin.metadata.rate_limits,
                "is_builtin": isinstance(plugin, BuiltinProviderPlugin),
                "config_schema": plugin.config_schema.schema() if plugin.config_schema else None
            }
        else:
            return {
                name: self.get_plugin_info(name) 
                for name in self.list_plugins()
            }
    
    def create_provider(self, name: str, config: Dict[str, Any]) -> DataProvider:
        """
        Create a data provider instance using the specified plugin.
        
        Args:
            name: Plugin name
            config: Provider configuration
            
        Returns:
            Configured DataProvider instance
            
        Raises:
            PluginNotFoundError: If plugin not found
            PluginValidationError: If configuration invalid
        """
        plugin = self.get_plugin(name)
        
        try:
            # Validate configuration
            validated_config = plugin.validate_config(config)
            
            # Create provider
            provider = plugin.create_provider(validated_config)
            
            logger.info(f"Created provider instance for '{name}'")
            return provider
            
        except Exception as e:
            logger.error(f"Failed to create provider '{name}': {e}")
            raise PluginValidationError(name, str(e))
    
    def test_provider(self, name: str, config: Dict[str, Any]) -> bool:
        """
        Test a provider connection.
        
        Args:
            name: Plugin name
            config: Provider configuration
            
        Returns:
            True if test successful, False otherwise
        """
        try:
            plugin = self.get_plugin(name)
            validated_config = plugin.validate_config(config)
            return plugin.test_connection(validated_config)
        except Exception as e:
            logger.error(f"Provider test failed for '{name}': {e}")
            return False
    
    def _validate_plugin(self, plugin: ProviderPlugin):
        """Validate a plugin before registration."""
        if not hasattr(plugin, 'metadata') or not plugin.metadata:
            raise ValueError("Plugin must have metadata")
        
        if not plugin.metadata.name:
            raise ValueError("Plugin metadata must include name")
        
        if not plugin.metadata.version:
            raise ValueError("Plugin metadata must include version")
        
        # Ensure required methods are implemented
        required_methods = ['validate_config', 'create_provider', 'test_connection']
        for method in required_methods:
            if not hasattr(plugin, method) or not callable(getattr(plugin, method)):
                raise ValueError(f"Plugin must implement {method} method")
        
        # Validate config schema
        if not plugin.config_schema or not issubclass(plugin.config_schema, BaseModel):
            raise ValueError("Plugin must provide valid Pydantic config schema")
    
    def _load_builtin_providers(self):
        """Load built-in provider plugins."""
        logger.debug("Loading built-in provider plugins")
        
        # Import and register built-in plugins
        builtin_modules = [
            'vortex.plugins.builtin.barchart_plugin',
            'vortex.plugins.builtin.yahoo_plugin', 
            'vortex.plugins.builtin.ibkr_plugin'
        ]
        
        for module_name in builtin_modules:
            try:
                self._load_plugin_from_module(module_name)
            except Exception as e:
                logger.warning(f"Failed to load builtin plugin {module_name}: {e}")
    
    def _load_external_providers(self):
        """Load external provider plugins."""
        logger.debug("Searching for external provider plugins")
        
        # Search for external plugins in common locations
        plugin_paths = [
            Path.home() / ".vortex" / "plugins",
            Path.cwd() / "vortex_plugins",
            Path("/opt/vortex/plugins") if Path("/opt/vortex/plugins").exists() else None
        ]
        
        for plugin_path in plugin_paths:
            if plugin_path and plugin_path.exists():
                self._load_plugins_from_directory(plugin_path)
    
    def _load_plugins_from_directory(self, directory: Path):
        """Load plugins from a directory."""
        logger.debug(f"Loading plugins from {directory}")
        
        for plugin_file in directory.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
                
            try:
                spec = importlib.util.spec_from_file_location(
                    f"external_plugin_{plugin_file.stem}", plugin_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find plugin classes in the module
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, ProviderPlugin) and 
                        obj != ProviderPlugin and
                        obj != BuiltinProviderPlugin):
                        
                        plugin_instance = obj()
                        self.register_plugin(plugin_instance)
                        
            except Exception as e:
                logger.warning(f"Failed to load external plugin {plugin_file}: {e}")
    
    def _load_plugin_from_module(self, module_name: str):
        """Load plugin from a module name."""
        try:
            module = importlib.import_module(module_name)
            
            # Find plugin classes in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, ProviderPlugin) and 
                    obj != ProviderPlugin and
                    obj != BuiltinProviderPlugin):
                    
                    plugin_instance = obj()
                    self.register_plugin(plugin_instance)
                    break
                    
        except ImportError as e:
            logger.debug(f"Could not import {module_name}: {e}")
        except Exception as e:
            logger.warning(f"Error loading plugin from {module_name}: {e}")
    
    def _try_dynamic_load(self, name: str):
        """Try to dynamically load a plugin by name."""
        # Try common plugin module patterns
        patterns = [
            f"vortex_plugin_{name}",
            f"vortex.plugins.{name}",
            f"vortex.plugins.external.{name}_plugin"
        ]
        
        for pattern in patterns:
            try:
                self._load_plugin_from_module(pattern)
                if name.lower() in self._plugins:
                    logger.info(f"Dynamically loaded plugin '{name}' from {pattern}")
                    return
            except Exception:
                continue


# Global registry instance
_registry = None


def get_provider_registry() -> ProviderRegistry:
    """
    Get the global provider registry instance.
    
    Returns:
        ProviderRegistry instance (singleton)
    """
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def register_plugin(plugin: ProviderPlugin):
    """
    Register a plugin with the global registry.
    
    Args:
        plugin: ProviderPlugin instance to register
    """
    registry = get_provider_registry()
    registry.register_plugin(plugin)