"""
Utility functions for dynamic provider management in CLI.

This module provides utilities to work with providers dynamically through
the plugin system, eliminating hardcoded provider strings.
"""

from typing import List, Optional, Dict, Any
import click

from vortex.plugins import get_provider_registry, PluginNotFoundError
from vortex.logging_integration import get_module_logger

logger = get_module_logger()


def get_available_providers() -> List[str]:
    """
    Get list of available provider names from plugin registry.
    
    Returns:
        List of provider names, or fallback list if registry fails
    """
    try:
        registry = get_provider_registry()
        return registry.list_plugins()
    except Exception as e:
        logger.warning(f"Failed to get providers from registry: {e}")
        # Fallback to known providers
        return ["barchart", "yahoo", "ibkr"]


def create_provider_choice() -> click.Choice:
    """
    Create Click Choice object with available providers.
    
    Returns:
        Click Choice object with dynamic provider list
    """
    providers = get_available_providers()
    return click.Choice(providers, case_sensitive=False)


def create_provider_choice_with_all() -> click.Choice:
    """
    Create Click Choice object with available providers plus 'all' option.
    
    Returns:
        Click Choice object with providers and 'all'
    """
    providers = get_available_providers()
    providers.append("all")
    return click.Choice(providers, case_sensitive=False)


def get_provider_config_from_vortex_config(provider: str, vortex_config) -> Dict[str, Any]:
    """
    Extract provider-specific configuration from vortex config using plugin metadata.
    
    Args:
        provider: Provider name
        vortex_config: Vortex configuration object
        
    Returns:
        Provider-specific configuration dictionary
    """
    try:
        registry = get_provider_registry()
        plugin = registry.get_plugin(provider)
        
        # Get provider config section
        provider_config_section = getattr(vortex_config.providers, provider, {})
        
        # Convert to dictionary, handling both dict and object types
        if hasattr(provider_config_section, '__dict__'):
            provider_config = provider_config_section.__dict__
        elif hasattr(provider_config_section, 'dict'):
            provider_config = provider_config_section.dict()
        elif isinstance(provider_config_section, dict):
            provider_config = provider_config_section
        else:
            provider_config = {}
        
        # Add general configuration that all providers can use
        general_config = {
            "timeout": getattr(vortex_config.general, 'timeout', 30),
            "max_retries": getattr(vortex_config.general, 'max_retries', 3),
            "enabled": True
        }
        
        # Merge with provider-specific config taking precedence
        final_config = {**general_config, **provider_config}
        
        logger.debug(f"Generated config for provider '{provider}': {final_config}")
        return final_config
        
    except PluginNotFoundError:
        logger.error(f"Provider plugin '{provider}' not found")
        raise
    except Exception as e:
        logger.error(f"Failed to get config for provider '{provider}': {e}")
        # Return minimal config as fallback
        return {
            "timeout": 30,
            "max_retries": 3,
            "enabled": True
        }


def validate_provider_exists(provider: str) -> bool:
    """
    Validate that a provider exists in the plugin registry.
    
    Args:
        provider: Provider name to validate
        
    Returns:
        True if provider exists, False otherwise
    """
    try:
        registry = get_provider_registry()
        registry.get_plugin(provider)
        return True
    except PluginNotFoundError:
        return False
    except Exception as e:
        logger.warning(f"Error checking provider '{provider}': {e}")
        return False


def get_provider_display_name(provider: str) -> str:
    """
    Get display name for a provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Display name or provider name if not found
    """
    try:
        registry = get_provider_registry()
        plugin_info = registry.get_plugin_info(provider)
        return plugin_info["display_name"]
    except Exception:
        return provider.title()


def get_provider_auth_requirements(provider: str) -> Dict[str, Any]:
    """
    Get authentication requirements for a provider.
    
    Args:
        provider: Provider name
        
    Returns:
        Dictionary with auth requirements
    """
    try:
        registry = get_provider_registry()
        plugin_info = registry.get_plugin_info(provider)
        
        return {
            "requires_auth": plugin_info["requires_auth"],
            "config_schema": plugin_info.get("config_schema"),
            "display_name": plugin_info["display_name"]
        }
    except Exception as e:
        logger.warning(f"Failed to get auth requirements for '{provider}': {e}")
        return {
            "requires_auth": True,  # Safe default
            "config_schema": None,
            "display_name": provider.title()
        }


def check_provider_configuration(provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if provider is properly configured.
    
    Args:
        provider: Provider name
        config: Provider configuration
        
    Returns:
        Dictionary with configuration status
    """
    try:
        registry = get_provider_registry()
        plugin_info = registry.get_plugin_info(provider)
        
        # Check if authentication is required
        if not plugin_info["requires_auth"]:
            return {
                "configured": True,
                "status": "✓ Available",
                "message": "No authentication required"
            }
        
        # Check for common required fields based on provider
        if not config:
            return {
                "configured": False,
                "status": "⚠ Not configured",
                "message": "Authentication required but not configured"
            }
        
        # Try to validate config through plugin
        try:
            plugin = registry.get_plugin(provider)
            plugin.validate_config(config)
            return {
                "configured": True,
                "status": "✓ Available", 
                "message": "Configuration valid"
            }
        except Exception as e:
            return {
                "configured": False,
                "status": "⚠ Configuration error",
                "message": f"Invalid configuration: {str(e)[:50]}..."
            }
            
    except Exception as e:
        logger.warning(f"Failed to check configuration for '{provider}': {e}")
        return {
            "configured": False,
            "status": "✗ Error",
            "message": f"Plugin error: {str(e)[:50]}..."
        }