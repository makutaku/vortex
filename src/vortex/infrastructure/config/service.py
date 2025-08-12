"""
Unified configuration service for standardized configuration management.

This module provides a centralized configuration service that can be injected
into components that need configuration access.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from vortex.core.config import ConfigManager, VortexConfig
from vortex.exceptions.config import ConfigurationError


class ConfigurationService:
    """Centralized configuration service for dependency injection."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration service.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.logger = logging.getLogger(__name__)
        self._manager = ConfigManager(config_path)
        self._config: Optional[VortexConfig] = None
        self._provider_configs: Dict[str, Dict[str, Any]] = {}
    
    @property
    def config(self) -> VortexConfig:
        """Get the current configuration, loading if necessary."""
        if self._config is None:
            self._config = self._manager.load_config()
        return self._config
    
    def reload_config(self) -> None:
        """Force reload of configuration from sources."""
        self._config = None
        self._provider_configs.clear()
        self._config = self._manager.load_config()
        self.logger.info("Configuration reloaded")
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific provider with caching.
        
        Args:
            provider: Provider name
            
        Returns:
            Provider configuration dictionary
        """
        if provider not in self._provider_configs:
            self._provider_configs[provider] = self._manager.get_provider_config(provider)
        return self._provider_configs[provider].copy()  # Return copy to prevent mutation
    
    def get_general_config(self) -> Dict[str, Any]:
        """Get general configuration section."""
        return {
            'output_directory': str(self.config.general.output_directory),
            'backup_enabled': self.config.general.backup_enabled,
            'dry_run': self.config.general.dry_run,
            'default_provider': self.config.general.default_provider.value,
            'logging': self.config.general.logging.model_dump()
        }
    
    def get_output_directory(self) -> Path:
        """Get configured output directory."""
        return self.config.general.output_directory
    
    def get_default_provider(self) -> str:
        """Get default provider name."""
        return self.config.general.default_provider.value
    
    def is_backup_enabled(self) -> bool:
        """Check if backup is enabled."""
        return self.config.general.backup_enabled
    
    def is_dry_run(self) -> bool:
        """Check if dry run mode is enabled."""
        return self.config.general.dry_run
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.config.general.logging.model_dump()
    
    def validate_provider_config(self, provider: str) -> bool:
        """Validate that a provider has all required configuration.
        
        Args:
            provider: Provider name
            
        Returns:
            True if configuration is valid
        """
        try:
            return self._manager.validate_provider_credentials(provider)
        except ConfigurationError:
            return False
    
    def get_missing_provider_fields(self, provider: str) -> list[str]:
        """Get list of missing configuration fields for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            List of missing field names
        """
        return self._manager.get_missing_credentials(provider)
    
    def update_provider_config(self, provider: str, updates: Dict[str, Any]) -> None:
        """Update provider configuration and save.
        
        Args:
            provider: Provider name
            updates: Configuration updates to apply
        """
        current_config = self.get_provider_config(provider)
        current_config.update(updates)
        
        self._manager.set_provider_config(provider, current_config)
        
        # Clear cache to force reload
        if provider in self._provider_configs:
            del self._provider_configs[provider]
        
        self.logger.info(f"Updated configuration for provider '{provider}'")
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        self._manager.save_config(self._config)
        self.logger.info("Configuration saved")


# Singleton instance
_config_service: Optional[ConfigurationService] = None


def get_config_service(config_path: Optional[Path] = None) -> ConfigurationService:
    """Get the global configuration service instance.
    
    Args:
        config_path: Optional configuration file path (only used on first call)
        
    Returns:
        Global ConfigurationService instance
    """
    global _config_service
    
    if _config_service is None:
        _config_service = ConfigurationService(config_path)
    
    return _config_service


def reset_config_service() -> None:
    """Reset the global configuration service (mainly for testing)."""
    global _config_service
    _config_service = None