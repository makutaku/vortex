"""
Unified Logging and Observability System for Vortex

This module provides structured logging, performance metrics, and observability
features with configurable outputs (console, JSON, file) and integration with
the Vortex configuration system.
"""

import json
import logging
import logging.handlers
import os
import sys
import time
import traceback
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from uuid import uuid4

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
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
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
        if hasattr(record, 'correlation_id'):
            log_entry["correlation_id"] = record.correlation_id
        
        # Add performance metrics if present
        if hasattr(record, 'duration'):
            log_entry["duration_ms"] = record.duration
        
        if hasattr(record, 'operation'):
            log_entry["operation"] = record.operation
        
        # Add extra context if present
        if hasattr(record, 'extra_context'):
            log_entry.update(record.extra_context)
        
        # Add exception information
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_entry, default=str)


class VortexLogger:
    """Enhanced logger with structured logging and observability features."""
    
    def __init__(self, name: str, correlation_id: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.correlation_id = correlation_id or str(uuid4())
        self.extra_context = {}
    
    def _log(self, level: int, msg: str, extra: Optional[Dict[str, Any]] = None, **kwargs):
        """Internal logging method with correlation ID and context."""
        extra = extra or {}
        extra['correlation_id'] = self.correlation_id
        if self.extra_context:
            extra['extra_context'] = self.extra_context.copy()
        
        # Add any additional kwargs to extra context
        if kwargs:
            if 'extra_context' not in extra:
                extra['extra_context'] = {}
            extra['extra_context'].update(kwargs)
        
        self.logger.log(level, msg, extra=extra)
    
    def debug(self, msg: str, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        """Log info message."""
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):  
        """Log warning message."""
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, exc_info: bool = True, **kwargs):
        """Log error message."""
        extra = kwargs.pop('extra', {})
        if exc_info:
            extra['exc_info'] = True
        self._log(logging.ERROR, msg, extra=extra, **kwargs)
    
    def critical(self, msg: str, exc_info: bool = True, **kwargs):
        """Log critical message."""
        extra = kwargs.pop('extra', {})
        if exc_info:
            extra['exc_info'] = True
        self._log(logging.CRITICAL, msg, extra=extra, **kwargs)
    
    def set_context(self, **context):
        """Set persistent context for this logger."""
        self.extra_context.update(context)
    
    def clear_context(self):
        """Clear persistent context."""
        self.extra_context.clear()
    
    @contextmanager
    def context(self, **context):
        """Temporarily add context for a block of code."""
        old_context = self.extra_context.copy()
        self.extra_context.update(context)
        try:
            yield self
        finally:
            self.extra_context = old_context


class PerformanceLogger:
    """Logger specifically for performance metrics and timing."""
    
    def __init__(self, logger: VortexLogger):
        self.logger = logger
    
    def time_operation(self, operation: str, **context):
        """Context manager to time an operation."""
        return TimedOperation(self.logger, operation, **context)
    
    def log_metric(self, name: str, value: Union[int, float], unit: str = "", **context):
        """Log a performance metric."""
        self.logger.info(
            f"Metric: {name} = {value}{unit}",
            metric_name=name,
            metric_value=value,
            metric_unit=unit,
            **context
        )
    
    def log_counter(self, name: str, count: int = 1, **context):
        """Log a counter metric."""
        self.logger.info(
            f"Counter: {name} = {count}",
            counter_name=name,
            counter_value=count,
            **context
        )


class TimedOperation:
    """Context manager for timing operations."""
    
    def __init__(self, logger: VortexLogger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Started operation: {self.operation}", operation=self.operation, **self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration_ms = (self.end_time - self.start_time) * 1000
        
        if exc_type is None:
            self.logger.info(
                f"Completed operation: {self.operation} in {duration_ms:.2f}ms",
                operation=self.operation,
                duration=duration_ms,
                status="success",
                **self.context
            )
        else:
            self.logger.error(
                f"Failed operation: {self.operation} after {duration_ms:.2f}ms: {exc_val}",
                operation=self.operation,
                duration=duration_ms,
                status="failed",
                error_type=exc_type.__name__,
                **self.context
            )


class LoggingConfig:
    """Configuration for the logging system."""
    
    def __init__(
        self,
        level: Union[str, int] = logging.INFO,
        format_type: str = "console",  # "console", "json", "rich" 
        output: Union[str, List[str]] = "console",  # "console", "file", ["console", "file"]
        file_path: Optional[Path] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        service_name: str = "vortex",
        version: str = "unknown"
    ):
        self.level = level if isinstance(level, int) else getattr(logging, level.upper())
        self.format_type = format_type
        self.output = output if isinstance(output, list) else [output]
        self.file_path = file_path
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.service_name = service_name
        self.version = version


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
            if name.startswith('vortex'):
                logging.getLogger(name).setLevel(config.level)
    
    def _add_console_handler(self, config: LoggingConfig):
        """Add console handler."""
        if config.format_type == "rich" and rich_available:
            handler = RichHandler(
                console=Console(stderr=True),
                show_time=True,
                show_level=True,
                show_path=True,
                markup=True,
                rich_tracebacks=True
            )
            handler.setFormatter(logging.Formatter("%(message)s"))
        elif config.format_type == "json":
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(StructuredFormatter(config.service_name, config.version))
        else:  # console format
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
        
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
            backupCount=config.backup_count
        )
        
        if config.format_type == "json":
            handler.setFormatter(StructuredFormatter(config.service_name, config.version))
        else:
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)8s] %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
        
        handler.setLevel(config.level)
        logging.getLogger().addHandler(handler)
        self.handlers.append(handler)
    
    def get_logger(self, name: str, correlation_id: Optional[str] = None) -> VortexLogger:
        """Get a Vortex logger instance."""
        return VortexLogger(name, correlation_id)
    
    def get_performance_logger(self, name: str, correlation_id: Optional[str] = None) -> PerformanceLogger:
        """Get a performance logger instance."""
        vortex_logger = self.get_logger(name, correlation_id)
        return PerformanceLogger(vortex_logger)


# Global logging manager instance
logging_manager = LoggingManager()


def configure_logging(config: LoggingConfig):
    """Configure the global logging system."""
    logging_manager.configure(config)


def get_logger(name: str, correlation_id: Optional[str] = None) -> VortexLogger:
    """Get a logger instance with correlation ID support."""
    return logging_manager.get_logger(name, correlation_id)


def get_performance_logger(name: str, correlation_id: Optional[str] = None) -> PerformanceLogger:
    """Get a performance logger instance."""
    return logging_manager.get_performance_logger(name, correlation_id)


def timed(operation: Optional[str] = None, logger: Optional[VortexLogger] = None):
    """Decorator to time function execution."""
    def decorator(func):
        nonlocal operation, logger
        if not operation:
            operation = f"{func.__module__}.{func.__name__}"
        if not logger:
            logger = get_logger(func.__module__)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            perf_logger = PerformanceLogger(logger)
            with perf_logger.time_operation(operation):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def logged(level: str = "info", logger: Optional[VortexLogger] = None):
    """Decorator to automatically log function calls."""
    def decorator(func):
        nonlocal logger
        if not logger:
            logger = get_logger(func.__module__)
        
        log_method = getattr(logger, level.lower())
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                log_method(f"Calling {func.__name__}", function=func.__name__)
                result = func(*args, **kwargs)
                log_method(f"Completed {func.__name__}", function=func.__name__)
                return result
            except Exception as e:
                logger.error(f"Failed {func.__name__}: {e}", function=func.__name__)
                raise
        return wrapper
    return decorator


# Legacy compatibility
class LoggingContext:
    """Legacy logging context for backward compatibility."""
    
    def __init__(self, entry_msg=None, success_msg=None, failure_msg=None, 
                 logger=None, entry_level=logging.DEBUG, success_level=logging.INFO, 
                 failure_level=logging.ERROR):
        self.entry_msg = entry_msg
        self.success_msg = success_msg
        self.failure_msg = failure_msg
        
        if isinstance(logger, VortexLogger):
            self.logger = logger
        else:
            # Convert standard logger to VortexLogger
            logger_name = logger.name if logger else __name__
            self.logger = get_logger(logger_name)
        
        self.entry_level = entry_level
        self.success_level = success_level
        self.failure_level = failure_level
    
    def __enter__(self):
        if self.entry_msg:
            level_name = logging.getLevelName(self.entry_level).lower()
            getattr(self.logger, level_name.lower())(self.entry_msg)
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            if self.success_msg:
                level_name = logging.getLevelName(self.success_level).lower()
                getattr(self.logger, level_name.lower())(self.success_msg)
        else:
            if self.failure_msg:
                level_name = logging.getLevelName(self.failure_level).lower()
                getattr(self.logger, level_name.lower())(self.failure_msg)


def init_logging(level=logging.INFO):
    """Legacy function for backward compatibility."""
    config = LoggingConfig(level=level, format_type="console", output="console")
    configure_logging(config)