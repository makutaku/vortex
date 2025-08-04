"""
Legacy compatibility functions.

Maintains backward compatibility with the original logging.py interface.
"""

import logging

from .config import LoggingConfig
from .manager import configure_logging


def init_logging(level=logging.INFO):
    """Legacy function for backward compatibility."""
    config = LoggingConfig(level=level, format_type="console", output="console")
    configure_logging(config)