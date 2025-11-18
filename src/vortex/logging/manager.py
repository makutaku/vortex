"""
Centralized logging configuration and management.

Provides the LoggingManager singleton for configuring and managing loggers.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

from .config import LoggingConfig
from .formatters import (
    StructuredFormatter,
    create_console_formatter,
    create_rich_handler,
)
from .loggers import VortexLogger
from .performance import PerformanceLogger

try:
    pass

    rich_available = True
except ImportError:
    rich_available = False


class LoggingManager:
    """Centralized logging configuration and management."""

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.config = None
            self.handlers = []
            self._initialized = True

    def configure(self, config: LoggingConfig):
        """Configure the logging system."""
        self.config = config

        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        self.handlers.clear()

        # Set root level
        root_logger.setLevel(config.level)

        # Create handlers based on configuration
        for output in config.output:
            if output == "console":
                self._add_console_handler(config)
            elif output == "file":
                self._add_file_handler(config)

        # Set level for all Vortex loggers
        for name in logging.Logger.manager.loggerDict:
            if name.startswith("vortex"):
                logging.getLogger(name).setLevel(config.level)

    def _add_console_handler(self, config: LoggingConfig):
        """Add console handler."""
        if config.format_type == "rich" and rich_available:
            handler = create_rich_handler()
            handler.setFormatter(logging.Formatter("%(message)s"))
        elif config.format_type == "json":
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(
                StructuredFormatter(config.service_name, config.version)
            )
        else:  # console format
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(create_console_formatter())

        handler.setLevel(config.level)
        logging.getLogger().addHandler(handler)
        self.handlers.append(handler)

    def _add_file_handler(self, config: LoggingConfig):
        """Add file handler with rotation."""
        if not config.file_path:
            config.file_path = Path("logs/vortex.log")

        # Ensure log directory exists
        config.file_path.parent.mkdir(parents=True, exist_ok=True)

        handler = logging.handlers.RotatingFileHandler(
            config.file_path,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count,
        )

        if config.format_type == "json":
            handler.setFormatter(
                StructuredFormatter(config.service_name, config.version)
            )
        else:
            handler.setFormatter(create_console_formatter())

        handler.setLevel(config.level)
        logging.getLogger().addHandler(handler)
        self.handlers.append(handler)

    def get_logger(
        self, name: str, correlation_id: Optional[str] = None
    ) -> VortexLogger:
        """Get a Vortex logger instance."""
        return VortexLogger(name, correlation_id)

    def get_performance_logger(
        self, name: str, correlation_id: Optional[str] = None
    ) -> PerformanceLogger:
        """Get a performance logger instance."""
        return PerformanceLogger(name, correlation_id)


# Global logging manager instance
logging_manager = LoggingManager()


def configure_logging(config: LoggingConfig):
    """Configure the global logging system."""
    logging_manager.configure(config)
