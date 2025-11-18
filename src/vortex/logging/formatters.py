"""
Log formatters for different output formats.

Provides structured JSON formatting, console formatting, and Rich terminal output.
"""

import json
import logging
import traceback
from datetime import datetime, timezone

try:
    from rich.console import Console
    from rich.logging import RichHandler

    rich_available = True
except ImportError:
    rich_available = False


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, service_name: str = "vortex", version: str = "unknown"):
        super().__init__()
        self.service_name = service_name
        self.version = version

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Build base log entry
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "service": self.service_name,
            "version": self.version,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
        }

        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id

        # Add performance metrics if present
        if hasattr(record, "duration"):
            log_entry["duration_ms"] = record.duration

        if hasattr(record, "operation"):
            log_entry["operation"] = record.operation

        # Add extra context if present
        if hasattr(record, "extra_context"):
            log_entry.update(record.extra_context)

        # Add exception information
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_entry, default=str)


def create_console_formatter() -> logging.Formatter:
    """Create a console formatter for human-readable output."""
    return logging.Formatter(
        "%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def create_rich_handler() -> logging.Handler:
    """Create a Rich handler for enhanced terminal output."""
    if not rich_available:
        raise ImportError("Rich library not available. Install with: pip install rich")

    return RichHandler(
        console=Console(stderr=True),
        show_time=True,
        show_level=True,
        show_path=True,
        markup=True,
        rich_tracebacks=True,
    )


def create_structured_formatter(
    service_name: str = "vortex", version: str = "unknown"
) -> StructuredFormatter:
    """Create a structured JSON formatter."""
    return StructuredFormatter(service_name, version)
