"""
Logging configuration management.

Provides configuration classes and utilities for setting up logging.
"""

import logging
from pathlib import Path
from typing import List, Optional, Union


class LoggingConfig:
    """Configuration for the logging system."""

    def __init__(
        self,
        level: Union[str, int] = logging.INFO,
        format_type: str = "console",  # "console", "json", "rich"
        output: Union[
            str, List[str]
        ] = "console",  # "console", "file", ["console", "file"]
        file_path: Optional[Path] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        service_name: str = "vortex",
        version: str = "unknown",
    ):
        self.level = (
            level if isinstance(level, int) else getattr(logging, level.upper())
        )
        self.format_type = format_type
        self.output = output if isinstance(output, list) else [output]
        self.file_path = file_path
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.service_name = service_name
        self.version = version


def create_default_config() -> LoggingConfig:
    """Create a default logging configuration."""
    return LoggingConfig(
        level=logging.INFO,
        format_type="console",
        output="console",
        service_name="vortex",
        version="unknown",
    )
