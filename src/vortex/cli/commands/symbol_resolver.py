"""
Symbol resolution and assets file handling for download commands.

Extracted from download.py to implement single responsibility principle.
Handles symbol resolution, assets file processing, and instrument configuration.
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Note: InstrumentParser functions available in vortex.cli.utils.instrument_parser if needed
from vortex.exceptions.cli import CLIError


def load_config_instruments(assets_file_path: Path) -> Dict[str, Any]:
    """Load instruments from assets configuration file.

    Args:
        assets_file_path: Path to the assets configuration file

    Returns:
        Dictionary mapping asset types to instrument configurations

    Raises:
        CLIError: If file cannot be read or parsed
    """
    try:
        with open(assets_file_path, "r") as f:
            assets_config = json.load(f)

        # Validate the assets structure
        if not isinstance(assets_config, dict):
            raise CLIError(f"Assets file {assets_file_path} must contain a JSON object")

        # Extract all instruments from all asset classes
        all_instruments = {}
        for asset_class, instruments in assets_config.items():
            if not isinstance(instruments, dict):
                logging.warning(
                    f"Skipping non-dict asset class '{asset_class}' in {assets_file_path}"
                )
                continue

            for symbol, config in instruments.items():
                if not isinstance(config, dict):
                    logging.warning(
                        f"Skipping non-dict config for symbol '{symbol}' in {assets_file_path}"
                    )
                    continue

                # Add asset_class to the config for context
                enhanced_config = config.copy()
                enhanced_config["asset_class"] = asset_class
                all_instruments[symbol] = enhanced_config

        if not all_instruments:
            raise CLIError(
                f"No valid instruments found in assets file {assets_file_path}"
            )

        logging.info(
            f"Loaded {len(all_instruments)} instruments from {assets_file_path}"
        )
        return all_instruments

    except FileNotFoundError:
        raise CLIError(f"Assets file not found: {assets_file_path}")
    except json.JSONDecodeError as e:
        raise CLIError(f"Invalid JSON in assets file {assets_file_path}: {e}")
    except PermissionError:
        raise CLIError(f"Permission denied reading assets file: {assets_file_path}")
    except OSError as e:
        raise CLIError(f"Error reading assets file {assets_file_path}: {e}")


class SymbolResolver:
    """Resolves symbols from various sources (direct, assets files, defaults)."""

    def __init__(self, provider: str):
        self.provider = provider
        self.logger = logging.getLogger(__name__)

    def resolve_symbols(
        self, symbols: Optional[List[str]] = None, assets_file: Optional[Path] = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Resolve symbols and their configurations from various sources.

        Args:
            symbols: Direct symbol list
            assets_file: Path to assets configuration file

        Returns:
            Tuple of (symbol_list, instrument_configs)
        """
        context = SymbolResolutionContext(symbols, assets_file, self.provider)

        # Try handlers in order of preference
        handlers = [AssetsFileHandler(), DirectSymbolsHandler(), DefaultAssetsHandler()]

        for handler in handlers:
            if handler.can_handle(context):
                return handler.handle(context)

        # Fallback - should never reach here
        raise CLIError("No symbol resolution method succeeded")


class SymbolResolutionContext:
    """Context for symbol resolution containing all input parameters."""

    def __init__(
        self, symbols: Optional[List[str]], assets_file: Optional[Path], provider: str
    ):
        self.symbols = symbols
        self.assets_file = assets_file
        self.provider = provider


class SymbolResolutionHandler(ABC):
    """Abstract base class for symbol resolution strategies."""

    @abstractmethod
    def can_handle(self, context: SymbolResolutionContext) -> bool:
        """Check if this handler can process the given context."""

    @abstractmethod
    def handle(
        self, context: SymbolResolutionContext
    ) -> Tuple[List[str], Dict[str, Any]]:
        """Handle symbol resolution for the given context."""


class AssetsFileHandler(SymbolResolutionHandler):
    """Handles symbol resolution from assets files."""

    def can_handle(self, context: SymbolResolutionContext) -> bool:
        return context.assets_file is not None

    def handle(
        self, context: SymbolResolutionContext
    ) -> Tuple[List[str], Dict[str, Any]]:
        instrument_configs = load_config_instruments(context.assets_file)
        symbols = list(instrument_configs.keys())
        logging.info(
            f"Using {len(symbols)} symbols from assets file: {context.assets_file}"
        )
        return symbols, instrument_configs


class DirectSymbolsHandler(SymbolResolutionHandler):
    """Handles direct symbol resolution."""

    def can_handle(self, context: SymbolResolutionContext) -> bool:
        return context.symbols is not None and len(context.symbols) > 0

    def handle(
        self, context: SymbolResolutionContext
    ) -> Tuple[List[str], Dict[str, Any]]:
        symbols = context.symbols
        logging.info(f"Using {len(symbols)} directly specified symbols")
        return symbols, {}


class DefaultAssetsHandler(SymbolResolutionHandler):
    """Handles default assets file resolution."""

    def can_handle(self, context: SymbolResolutionContext) -> bool:
        return True  # Always can handle as fallback

    def handle(
        self, context: SymbolResolutionContext
    ) -> Tuple[List[str], Dict[str, Any]]:
        default_file = self._get_default_assets_file(context.provider)
        if default_file and default_file.exists():
            instrument_configs = load_config_instruments(default_file)
            symbols = list(instrument_configs.keys())
            logging.info(
                f"Using {len(symbols)} symbols from default assets file: {default_file}"
            )
            return symbols, instrument_configs

        raise CLIError(
            f"No symbols specified and no default assets file found for provider '{context.provider}'. "
            f"Either provide --symbol parameters or --assets file."
        )

    def _get_default_assets_file(self, provider: str) -> Optional[Path]:
        """Get default assets file path for provider."""
        # Check multiple possible locations
        possible_paths = [
            Path(f"assets/{provider}.json"),
            Path(f"config/assets/{provider}.json"),
            Path("assets/default.json"),
            Path("config/assets/default.json"),
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None


def resolve_symbols_and_configs(
    provider: str,
    symbols: Optional[List[str]] = None,
    assets_file: Optional[Path] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """Resolve symbols and their configurations from various sources.

    This is the main entry point for symbol resolution.

    Args:
        provider: Data provider name
        symbols: Direct symbol list
        assets_file: Path to assets configuration file

    Returns:
        Tuple of (symbol_list, instrument_configs)
    """
    resolver = SymbolResolver(provider)
    return resolver.resolve_symbols(symbols, assets_file)
