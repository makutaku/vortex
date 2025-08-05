"""Dependency injection and optional module management for Vortex CLI.

This module provides a clean way to handle optional dependencies and fallback
implementations, eliminating the need for scattered try/except blocks throughout
the codebase.
"""

import logging
from typing import Optional, Any, Callable, Dict, Type
from pathlib import Path


class DependencyRegistry:
    """Registry for managing optional dependencies and fallback implementations."""
    
    def __init__(self):
        self._modules: Dict[str, Any] = {}
        self._fallbacks: Dict[str, Any] = {}
        self._availability: Dict[str, bool] = {}
        self._logger = logging.getLogger(__name__)
    
    def register_optional_module(self, name: str, import_func: Callable, fallback: Any = None):
        """Register an optional module with optional fallback."""
        try:
            module = import_func()
            self._modules[name] = module
            self._availability[name] = True
            self._logger.debug(f"Successfully loaded optional module: {name}")
        except ImportError as e:
            self._modules[name] = fallback
            self._fallbacks[name] = fallback
            self._availability[name] = False
            self._logger.debug(f"Optional module {name} not available: {e}")
    
    def get(self, name: str, default: Any = None) -> Any:
        """Get a registered module or return default."""
        return self._modules.get(name, default)
    
    def is_available(self, name: str) -> bool:
        """Check if a module is available (not using fallback)."""
        return self._availability.get(name, False)
    
    def get_availability_summary(self) -> Dict[str, bool]:
        """Get summary of all module availability."""
        return self._availability.copy()


# Global dependency registry instance
_registry = DependencyRegistry()


# Fallback implementations
class NullUX:
    """Minimal UX implementation when Rich/advanced UX unavailable."""
    
    def set_quiet(self, quiet: bool): pass
    def set_force_yes(self, force: bool): pass
    
    def print_panel(self, text: str, title: str = "", style: str = ""):
        """Print panel content as plain text."""
        if title:
            print(f"\n{title}")
            print("=" * len(title))
        print(text)
        print()
    
    def choice(self, question: str, choices: list, default: str = None):
        """Simple text-based choice prompt."""
        print(f"\n{question}")
        for i, choice in enumerate(choices, 1):
            marker = " (default)" if choice == default else ""
            print(f"  {i}. {choice}{marker}")
        
        try:
            selection = input("\nEnter choice number: ").strip()
            if not selection and default:
                return default
            index = int(selection) - 1
            if 0 <= index < len(choices):
                return choices[index]
        except (ValueError, KeyboardInterrupt):
            pass
        
        return default or choices[0] if choices else None


class NullWizard:
    """Minimal command wizard when advanced wizard unavailable."""
    
    def __init__(self, ux): 
        self.ux = ux
    
    def run_download_wizard(self) -> dict:
        """Simple download configuration."""
        print("\n📊 Download Wizard")
        symbol = input("Enter symbol (e.g., AAPL): ").strip().upper()
        if symbol:
            return {"symbols": [symbol], "execute": True}
        return {"execute": False}
    
    def run_config_wizard(self) -> dict:
        """Simple configuration wizard."""
        print("\n⚙️ Configuration Wizard")
        provider = input("Enter provider (barchart/yahoo/ibkr): ").strip().lower()
        if provider in ["barchart", "yahoo", "ibkr"]:
            return {"provider": provider}
        return {}


class NullCorrelationManager:
    """Null correlation manager when resilience unavailable."""
    
    @staticmethod
    def get_current_id() -> Optional[str]:
        return None


def null_correlation_decorator(*args, **kwargs):
    """Null correlation decorator."""
    def decorator(func):
        return func
    return decorator


# Import functions for lazy loading
def _import_config():
    """Import configuration modules."""
    from vortex.cli.utils.config_manager import ConfigManager
    from vortex.logging_integration import configure_logging_from_manager, get_logger, run_health_checks
    return {
        'ConfigManager': ConfigManager,
        'configure_logging_from_manager': configure_logging_from_manager,
        'get_logger': get_logger,
        'run_health_checks': run_health_checks
    }


def _import_resilience():
    """Import resilience modules."""
    from vortex.shared.resilience.correlation import CorrelationIdManager, with_correlation
    from vortex.shared.resilience.circuit_breaker import get_circuit_breaker_stats
    from vortex.shared.resilience.recovery import ErrorRecoveryManager
    return {
        'CorrelationIdManager': CorrelationIdManager,
        'with_correlation': with_correlation,
        'get_circuit_breaker_stats': get_circuit_breaker_stats,
        'ErrorRecoveryManager': ErrorRecoveryManager
    }


def _import_rich():
    """Import Rich console."""
    from rich.console import Console
    return {'Console': Console}


def _import_commands():
    """Import command modules."""
    from .commands import download, config, providers, validate
    from .help import help as help_command
    from .completion import install_completion
    return {
        'download': download,
        'config': config,
        'providers': providers,
        'validate': validate,
        'help_command': help_command,
        'install_completion': install_completion
    }


def _import_ux():
    """Import UX modules."""
    from .ux import get_ux, CommandWizard
    return {
        'get_ux': get_ux,
        'CommandWizard': CommandWizard
    }


def _import_resilience_commands():
    """Import resilience command modules."""
    from .commands import resilience
    return {'resilience': resilience}


def initialize_dependencies():
    """Initialize all dependencies with fallbacks."""
    # Register configuration dependencies
    _registry.register_optional_module(
        'config',
        _import_config,
        fallback={
            'ConfigManager': None,
            'configure_logging_from_manager': lambda *args, **kwargs: None,
            'get_logger': lambda name: logging.getLogger(name),
            'run_health_checks': lambda: None
        }
    )
    
    # Register resilience dependencies
    _registry.register_optional_module(
        'resilience',
        _import_resilience,
        fallback={
            'CorrelationIdManager': NullCorrelationManager,
            'with_correlation': null_correlation_decorator,
            'get_circuit_breaker_stats': lambda: {},
            'ErrorRecoveryManager': None
        }
    )
    
    # Register Rich console
    _registry.register_optional_module(
        'rich',
        _import_rich,
        fallback={'Console': None}
    )
    
    # Register command modules
    _registry.register_optional_module(
        'commands',
        _import_commands,
        fallback=None  # Will be handled specially in main.py
    )
    
    # Register UX modules
    _registry.register_optional_module(
        'ux',
        _import_ux,
        fallback={
            'get_ux': lambda: NullUX(),
            'CommandWizard': NullWizard
        }
    )
    
    # Register resilience commands
    _registry.register_optional_module(
        'resilience_commands',
        _import_resilience_commands,
        fallback=None
    )


def get_dependency(name: str, component: str = None) -> Any:
    """Get a dependency or component from the registry."""
    module = _registry.get(name)
    if module is None:
        return None
    
    if component:
        return module.get(component) if isinstance(module, dict) else getattr(module, component, None)
    
    return module


def is_available(name: str) -> bool:
    """Check if a dependency is available."""
    return _registry.is_available(name)


def get_availability_summary() -> Dict[str, bool]:
    """Get summary of all dependency availability."""
    return _registry.get_availability_summary()


# Initialize dependencies when module is imported
initialize_dependencies()