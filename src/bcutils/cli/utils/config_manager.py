"""Configuration management for BC-Utils CLI."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
except ImportError:
    tomllib = None

import tomli_w


class ConfigManager:
    """Manages BC-Utils configuration files and settings."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_file: Path to custom config file. If None, uses default location.
        """
        if config_file:
            self.config_file = config_file
        else:
            # Use standard user config directory
            config_dir = Path.home() / ".config" / "bcutils"
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file = config_dir / "config.toml"
        
        self._config: Optional[Dict[str, Any]] = None
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file and environment variables."""
        if self._config is not None:
            return self._config
        
        # Start with defaults
        config = self._get_default_config()
        
        # Load from file if it exists
        if self.config_file.exists():
            try:
                if tomllib is None:
                    raise ImportError("TOML support not available")
                
                with open(self.config_file, 'rb') as f:
                    file_config = tomllib.load(f)
                    config = self._merge_config(config, file_config)
            except Exception as e:
                # Don't fail if config file is corrupted, just use defaults
                import logging
                logging.warning(f"Failed to load config file {self.config_file}: {e}")
        
        # Override with environment variables
        env_config = self._load_from_environment()
        config = self._merge_config(config, env_config)
        
        self._config = config
        return config
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        if self._config is None:
            return
        
        # Ensure directory exists
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write TOML file
        with open(self.config_file, 'wb') as f:
            tomli_w.dump(self._config, f)
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for a specific provider."""
        config = self.load_config()
        return config.get("providers", {}).get(provider, {})
    
    def set_provider_config(self, provider: str, provider_config: Dict[str, Any]) -> None:
        """Set configuration for a specific provider."""
        config = self.load_config()
        
        if "providers" not in config:
            config["providers"] = {}
        
        config["providers"][provider] = provider_config
        self._config = config
    
    def export_config(self, export_path: Path) -> None:
        """Export configuration to a file."""
        config = self.load_config()
        
        with open(export_path, 'wb') as f:
            tomli_w.dump(config, f)
    
    def import_config(self, import_path: Path) -> None:
        """Import configuration from a file."""
        if tomllib is None:
            raise ImportError("TOML support not available")
        
        with open(import_path, 'rb') as f:
            imported_config = tomllib.load(f)
        
        # Merge with existing config
        current_config = self.load_config()
        merged_config = self._merge_config(current_config, imported_config)
        
        self._config = merged_config
        self.save_config()
    
    def reset_config(self) -> None:
        """Reset configuration to defaults."""
        self._config = self._get_default_config()
        
        # Remove config file if it exists
        if self.config_file.exists():
            self.config_file.unlink()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "output_directory": "./data",
            "backup_enabled": False,
            "log_level": "INFO",
            "providers": {
                "barchart": {
                    "daily_limit": 150,
                    "base_url": "https://www.barchart.com"
                },
                "yahoo": {
                    "base_url": "https://query1.finance.yahoo.com"
                },
                "ibkr": {
                    "host": "localhost",
                    "port": 7497,
                    "client_id": 1,
                    "timeout": 60
                }
            }
        }
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables.
        
        Note: Environment variable support is deprecated.
        Use config file or interactive setup instead.
        """
        # Return empty config - no environment variable support
        return {}
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge two configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result