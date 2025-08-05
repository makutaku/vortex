"""
Logging context management and decorators.

Provides decorators and context managers for automatic logging.
"""

import logging
from functools import wraps
from typing import Optional

from .loggers import VortexLogger
from .manager import logging_manager


def logged(level: str = "info", logger: Optional[VortexLogger] = None):
    """Decorator to automatically log function calls."""
    def decorator(func):
        nonlocal logger
        if not logger:
            logger = logging_manager.get_logger(func.__module__)
        
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


class LoggingContext:
    """Context manager for structured logging with entry/exit messages."""
    
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
            self.logger = logging_manager.get_logger(logger_name)
        
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