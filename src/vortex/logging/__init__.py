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

# Import main interfaces for backward compatibility
from .config import LoggingConfig
from .manager import LoggingManager, configure_logging, logging_manager
from .loggers import VortexLogger, get_logger
from .performance import PerformanceLogger, get_performance_logger, timed, TimedOperation
from .context import LoggingContext, logged
from .formatters import StructuredFormatter

# Legacy compatibility - these functions were in the original logging.py
from .legacy import init_logging

# Also make logging manager available directly
get_logger = logging_manager.get_logger
get_performance_logger = logging_manager.get_performance_logger

__all__ = [
    # Core interfaces
    'LoggingConfig',
    'LoggingManager', 
    'configure_logging',
    'VortexLogger',
    'get_logger',
    
    # Performance tracking
    'PerformanceLogger',
    'get_performance_logger', 
    'timed',
    'TimedOperation',
    
    # Context management
    'LoggingContext',
    'logged',
    
    # Formatters
    'StructuredFormatter',
    
    # Legacy compatibility
    'init_logging',
]