"""
CLI setup and initialization functions.

Handles logging configuration and initial setup for the CLI.
"""

import logging
from pathlib import Path
from typing import Optional

# Import version safely
try:
    from . import __version__
except ImportError:
    __version__ = "unknown"


def setup_logging(config_file: Optional[Path] = None, verbose: int = 0) -> None:
    """Set up logging using Vortex configuration system."""
    # Set up fallback logging first to avoid missing log messages
    logging.basicConfig(
        level=logging.DEBUG if verbose > 1 else logging.INFO if verbose else logging.WARNING,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    fallback_logger = logging.getLogger("vortex.cli")
    
    try:
        # Try to load configuration and set up advanced logging
        from vortex.core.config import ConfigManager
        from vortex.logging_integration import configure_logging_from_manager, get_logger
        
        config_manager = ConfigManager(config_file)
        configure_logging_from_manager(config_manager, service_name="vortex-cli", version=__version__)
        
        # Get logger for CLI - this will use advanced logging if successful
        logger = get_logger("vortex.cli")
        logger.info("Vortex CLI started", version=__version__, verbose_level=verbose)
        
    except Exception as e:
        # Continue with fallback logging - no warning needed as this is expected in containers
        if verbose > 0:  # Only show warning in verbose mode
            fallback_logger.debug(f"Using fallback logging configuration (advanced config not available: {e})")