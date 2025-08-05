"""
Base plugin architecture for Vortex data providers.

This module defines the abstract interfaces that all data provider plugins
must implement, enabling a modular and extensible architecture.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Type, Union
from datetime import datetime

from pydantic import BaseModel, Field
from vortex.infrastructure.providers.data_providers.data_provider import DataProvider
from vortex.logging_integration import get_module_logger

logger = get_module_logger()


@dataclass
class PluginMetadata:
    """Metadata describing a data provider plugin."""
    
    name: str
    display_name: str
    version: str
    description: str
    author: str
    homepage: Optional[str] = None
    requires_auth: bool = True
    supported_assets: List[str] = None
    rate_limits: Optional[str] = None
    api_documentation: Optional[str] = None
    
    def __post_init__(self):
        if self.supported_assets is None:
            self.supported_assets = ["stocks", "futures", "forex"]


class ProviderConfigSchema(BaseModel):
    """Base configuration schema for provider plugins."""
    
    enabled: bool = Field(default=True, description="Whether the provider is enabled")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retries")
    
    class Config:
        extra = "allow"  # Allow provider-specific configuration


class ProviderPlugin(ABC):
    """
    Abstract base class for data provider plugins.
    
    All data provider plugins must inherit from this class and implement
    the required methods to integrate with the Vortex plugin system.
    """
    
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Return plugin metadata."""
        pass
    
    @property
    @abstractmethod
    def config_schema(self) -> Type[BaseModel]:
        """Return Pydantic schema for provider configuration."""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize provider configuration.
        
        Args:
            config: Raw configuration dictionary
            
        Returns:
            Validated configuration dictionary
            
        Raises:
            PluginConfigurationError: If configuration is invalid
        """
        pass
    
    @abstractmethod
    def create_provider(self, config: Dict[str, Any]) -> DataProvider:
        """
        Create and return a configured data provider instance.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            Configured DataProvider instance
            
        Raises:
            PluginConfigurationError: If provider cannot be created
        """
        pass
    
    @abstractmethod
    def test_connection(self, config: Dict[str, Any]) -> bool:
        """
        Test provider connection and authentication.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    def get_available_symbols(self, config: Dict[str, Any]) -> List[str]:
        """
        Get list of available symbols from the provider.
        
        Optional method - providers can override to provide symbol discovery.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            List of available symbols, or empty list if not supported
        """
        return []
    
    def get_provider_info(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get runtime information about the provider.
        
        Optional method - providers can override to provide status info.
        
        Args:
            config: Validated configuration dictionary
            
        Returns:
            Dictionary with provider status information
        """
        return {
            "status": "available",
            "last_check": datetime.now().isoformat(),
            "metadata": {
                "name": self.metadata.name,
                "version": self.metadata.version,
                "requires_auth": self.metadata.requires_auth
            }
        }
    
    def cleanup(self):
        """
        Cleanup resources when plugin is unloaded.
        
        Optional method - providers can override for custom cleanup.
        """
        pass
    
    def get_help_text(self) -> str:
        """
        Get help text for configuring this provider.
        
        Returns:
            Human-readable configuration help text
        """
        help_lines = [
            f"# {self.metadata.display_name} Configuration",
            f"# {self.metadata.description}",
            "",
        ]
        
        if self.metadata.requires_auth:
            help_lines.extend([
                "Authentication required. Configure with:",
                f"  vortex config --provider {self.metadata.name} --set-credentials",
                "",
            ])
        
        if self.metadata.api_documentation:
            help_lines.extend([
                f"API Documentation: {self.metadata.api_documentation}",
                "",
            ])
        
        if self.metadata.rate_limits:
            help_lines.extend([
                f"Rate Limits: {self.metadata.rate_limits}",
                "",
            ])
        
        # Add schema-based configuration help
        schema = self.config_schema.schema()
        if "properties" in schema:
            help_lines.append("Configuration Options:")
            for field_name, field_info in schema["properties"].items():
                description = field_info.get("description", "")
                field_type = field_info.get("type", "string")
                default = field_info.get("default")
                
                help_line = f"  {field_name} ({field_type})"
                if default is not None:
                    help_line += f" [default: {default}]"
                if description:
                    help_line += f" - {description}"
                help_lines.append(help_line)
        
        return "\\n".join(help_lines)


class BuiltinProviderPlugin(ProviderPlugin):
    """
    Base class for built-in provider plugins.
    
    Built-in plugins are always available and don't require external installation.
    """
    
    @property
    def is_builtin(self) -> bool:
        return True