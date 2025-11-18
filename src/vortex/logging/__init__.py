"""
Vortex Logging Package

Modular logging system providing structured logging, performance metrics,
and observability features with configurable outputs.

This package replaces the monolithic logging.py module with focused components:
- formatters: Log formatting (JSON, console, rich)
- loggers: Enhanced logger classes with correlation IDs
- performance: Performance tracking and metrics
- config: Logging configuration management
- manager: Centralized logging setup and management
"""

# Core logging interfaces
from .config import LoggingConfig
from .context import LoggingContext, logged
from .formatters import StructuredFormatter
from .loggers import VortexLogger
from .manager import LoggingManager, configure_logging, logging_manager
from .performance import PerformanceLogger, TimedOperation, timed

# Make logging manager methods available directly
get_logger = logging_manager.get_logger
get_performance_logger = logging_manager.get_performance_logger

__all__ = [
    # Core interfaces
    "LoggingConfig",
    "LoggingManager",
    "configure_logging",
    "VortexLogger",
    "get_logger",
    # Performance tracking
    "PerformanceLogger",
    "get_performance_logger",
    "timed",
    "TimedOperation",
    # Context management
    "LoggingContext",
    "logged",
    # Formatters
    "StructuredFormatter",
]
