"""
Configuration utilities shared across CLI commands.

This module extracts shared configuration logic to prevent circular dependencies
between CLI command modules.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from vortex.core.config import ConfigManager
from vortex.exceptions import ConfigurationError
from vortex.core.constants import ProviderConstants

logger = logging.getLogger(__name__)


def get_or_create_config_manager(config_file: Optional[Path] = None) -> ConfigManager:
    """Get or create a ConfigManager instance.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        ConfigManager instance
    """
    return ConfigManager(config_file)


def validate_provider_configuration(
    config_manager: ConfigManager, 
    provider: str
) -> Tuple[bool, Optional[str]]:
    """Validate provider configuration and return status.
    
    Args:
        config_manager: Configuration manager instance
        provider: Provider name to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        if provider == "barchart":
            has_creds = config_manager.validate_provider_credentials(provider)
            if not has_creds:
                return False, "Missing credentials"
        elif provider == "yahoo":
            # Yahoo doesn't require credentials
            return True, None
        elif provider == "ibkr":
            # IBKR always has default config
            return True, None
        else:
            return False, f"Unknown provider: {provider}"
            
        return True, None
    except ConfigurationError as e:
        return False, str(e)


def get_provider_config_with_defaults(
    config_manager: ConfigManager,
    provider: str
) -> Dict[str, Any]:
    """Get provider configuration with defaults applied.
    
    Args:
        config_manager: Configuration manager instance
        provider: Provider name
        
    Returns:
        Provider configuration dictionary
    """
    try:
        config = config_manager.get_provider_config(provider)
    except Exception as e:
        logger.debug(f"Could not get config for provider '{provider}': {e}")
        # Return defaults if config not found
        config = {}
    
    # Apply provider-specific defaults
    if provider == "barchart":
        config.setdefault('daily_limit', ProviderConstants.Barchart.DEFAULT_DAILY_DOWNLOAD_LIMIT)
    elif provider == "ibkr":
        config.setdefault('host', 'localhost')
        config.setdefault('port', 7497)
        config.setdefault('client_id', 1)
    
    return config


def get_default_date_range(
    provider: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Tuple[datetime, datetime]:
    """Get default date range for downloads based on provider.
    
    Args:
        provider: Provider name
        start_date: Optional start date
        end_date: Optional end date
        
    Returns:
        Tuple of (start_date, end_date)
    """
    # Default end date is today
    if end_date is None:
        end_date = datetime.now()
    
    # Default start date depends on provider
    if start_date is None:
        if provider == "yahoo":
            # Yahoo: 1 year of data by default
            start_date = end_date - timedelta(days=365)
        elif provider == "barchart":
            # Barchart: 3 months by default
            start_date = end_date - timedelta(days=90)
        else:
            # Others: 6 months by default
            start_date = end_date - timedelta(days=180)
    
    return start_date, end_date


def format_provider_status(
    config_manager: ConfigManager,
    provider: str,
    config: Optional[Any] = None
) -> Dict[str, str]:
    """Format provider status for display.
    
    Args:
        config_manager: Configuration manager instance
        provider: Provider name
        config: Optional pre-loaded configuration to avoid repeated loads
        
    Returns:
        Dictionary with status, notes, and other display info
    """
    is_valid, error_msg = validate_provider_configuration(config_manager, provider)
    if config is None:
        config = config_manager.load_config()
    
    result = {
        'provider': provider,
        'status': "✓ Configured" if is_valid else "✗ Not configured",
        'notes': ""
    }
    
    if provider == "barchart":
        if is_valid:
            result['notes'] = f"Daily limit: {config.providers.barchart.daily_limit}"
        else:
            result['notes'] = error_msg or "Missing credentials"
    elif provider == "yahoo":
        result['notes'] = "Free - No credentials required"
    elif provider == "ibkr":
        result['notes'] = f"Host: {config.providers.ibkr.host}:{config.providers.ibkr.port}"
    
    return result


def ensure_provider_configured(
    config_manager: ConfigManager,
    provider: str
) -> None:
    """Ensure provider is configured, raising error if not.
    
    Args:
        config_manager: Configuration manager instance
        provider: Provider name
        
    Raises:
        ConfigurationError: If provider is not properly configured
    """
    is_valid, error_msg = validate_provider_configuration(config_manager, provider)
    
    if not is_valid:
        if provider == "barchart":
            raise ConfigurationError(
                f"Barchart provider requires credentials. "
                f"Run 'vortex config --provider barchart --set-credentials' to configure."
            )
        else:
            raise ConfigurationError(
                f"Provider '{provider}' is not properly configured: {error_msg}"
            )