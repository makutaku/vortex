# Column mapping registry for provider-specific column handling

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
from .column_constants import DATETIME_INDEX_NAME, REQUIRED_DATA_COLUMNS


class ProviderColumnMapping(ABC):
    """Abstract base class for provider-specific column mappings."""
    
    @abstractmethod
    def get_column_mapping(self, df_columns: List[str]) -> Dict[str, str]:
        """Get mapping from provider columns to internal standard columns."""
        pass
    
    @abstractmethod
    def get_provider_specific_columns(self) -> List[str]:
        """Get list of provider-specific columns that should be preserved."""
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get the provider name."""
        pass


class ColumnMappingRegistry:
    """Registry for managing provider-specific column mappings."""
    
    def __init__(self):
        self._mappings: Dict[str, ProviderColumnMapping] = {}
    
    def register(self, mapping: ProviderColumnMapping) -> None:
        """Register a provider column mapping."""
        self._mappings[mapping.provider_name.lower()] = mapping
    
    def get_mapping(self, provider_name: str) -> ProviderColumnMapping:
        """Get column mapping for a provider."""
        provider_lower = provider_name.lower()
        if provider_lower not in self._mappings:
            raise ValueError(f"No column mapping registered for provider: {provider_name}")
        return self._mappings[provider_lower]
    
    def get_column_mapping(self, provider_name: str, df_columns: List[str]) -> Dict[str, str]:
        """Get column mapping dictionary for a provider."""
        try:
            mapping = self.get_mapping(provider_name)
            return mapping.get_column_mapping(df_columns)
        except ValueError:
            # Return empty mapping for unknown providers
            return {}
    
    def get_provider_expected_columns(self, provider_name: str) -> Tuple[List[str], List[str]]:
        """Get expected columns for a provider."""
        try:
            mapping = self.get_mapping(provider_name)
            required = REQUIRED_DATA_COLUMNS  # Standard OHLCV columns
            optional = mapping.get_provider_specific_columns()
            return required, optional
        except ValueError:
            # Return just standard columns for unknown providers
            return REQUIRED_DATA_COLUMNS, []


# Global registry instance
_column_registry = ColumnMappingRegistry()


def register_provider_column_mapping(mapping: ProviderColumnMapping) -> None:
    """Register a provider column mapping with the global registry."""
    _column_registry.register(mapping)


def get_column_mapping(provider_name: str, df_columns: List[str]) -> Dict[str, str]:
    """Get column mapping for a provider."""
    return _column_registry.get_column_mapping(provider_name, df_columns)


def get_provider_expected_columns(provider_name: str) -> Tuple[List[str], List[str]]:
    """Get expected columns for a provider."""
    return _column_registry.get_provider_expected_columns(provider_name)