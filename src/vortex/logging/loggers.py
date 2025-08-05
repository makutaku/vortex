"""
Enhanced logger classes with correlation IDs and structured context.

Provides VortexLogger with correlation tracking and context management.
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, Optional
from uuid import uuid4


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
    
    def error(self, msg: str, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, msg, **kwargs)
    
    def exception(self, msg: str, **kwargs):
        """Log exception with traceback."""
        kwargs['exc_info'] = True
        self._log(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, msg, **kwargs)
    
    def add_context(self, **kwargs):
        """Add persistent context to this logger."""
        self.extra_context.update(kwargs)
    
    def clear_context(self):
        """Clear persistent context."""
        self.extra_context.clear()
    
    def with_context(self, **kwargs) -> 'VortexLogger':
        """Create a copy of this logger with additional context."""
        new_logger = VortexLogger(self.logger.name, self.correlation_id)
        new_logger.extra_context = self.extra_context.copy()
        new_logger.extra_context.update(kwargs)
        return new_logger
    
    @contextmanager
    def context(self, context_dict: Dict[str, Any]):
        """Context manager for temporary context addition."""
        original_context = self.extra_context.copy()
        self.extra_context.update(context_dict)
        try:
            yield self
        finally:
            self.extra_context = original_context
    
    @contextmanager
    def temp_context(self, **kwargs):
        """Context manager for temporary context (keyword arguments)."""
        original_context = self.extra_context.copy()
        self.extra_context.update(kwargs)
        try:
            yield self
        finally:
            self.extra_context = original_context


def get_logger(name: str, correlation_id: Optional[str] = None) -> VortexLogger:
    """Get a VortexLogger instance."""
    return VortexLogger(name, correlation_id)