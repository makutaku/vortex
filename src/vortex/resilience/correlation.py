"""
Correlation ID Management for Request Tracing.

Provides correlation ID generation and propagation for tracking requests
across different components and external services.
"""

import uuid
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from functools import wraps

# Optional logging - graceful fallback if not available
try:
    from ..logging import get_logger
    logger = get_logger(__name__)
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# Thread-local storage for correlation context
_context_storage = threading.local()


@dataclass
class CorrelationContext:
    """Context information for request correlation."""
    correlation_id: str
    parent_id: Optional[str] = None
    operation: Optional[str] = None
    provider: Optional[str] = None
    start_time: datetime = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class CorrelationIdManager:
    """
    Manager for correlation IDs and request tracing.
    
    Provides context management for tracking requests across
    multiple components and external service calls.
    """
    
    @staticmethod
    def generate_id() -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def get_current_id() -> Optional[str]:
        """Get the current correlation ID from thread-local storage."""
        return getattr(_context_storage, 'correlation_id', None)
    
    @staticmethod
    def get_current_context() -> Optional[CorrelationContext]:
        """Get the current correlation context."""
        return getattr(_context_storage, 'context', None)
    
    @staticmethod
    def set_context(context: CorrelationContext):
        """Set the correlation context for the current thread."""
        _context_storage.context = context
        _context_storage.correlation_id = context.correlation_id
        
        logger.debug("Correlation context set",
                   correlation_id=context.correlation_id,
                   operation=context.operation,
                   provider=context.provider)
    
    @staticmethod
    def clear_context():
        """Clear the correlation context for the current thread."""
        correlation_id = getattr(_context_storage, 'correlation_id', None)
        if hasattr(_context_storage, 'context'):
            delattr(_context_storage, 'context')
        if hasattr(_context_storage, 'correlation_id'):
            delattr(_context_storage, 'correlation_id')
            
        if correlation_id:
            logger.debug("Correlation context cleared", correlation_id=correlation_id)
    
    @staticmethod
    @contextmanager
    def correlation_context(
        correlation_id: Optional[str] = None,
        operation: Optional[str] = None,
        provider: Optional[str] = None,
        **metadata
    ):
        """
        Context manager for correlation ID management.
        
        Args:
            correlation_id: Specific correlation ID (generates new if None)
            operation: Name of the operation being performed
            provider: Data provider name
            **metadata: Additional metadata for the context
        """
        # Generate ID if not provided
        if correlation_id is None:
            correlation_id = CorrelationIdManager.generate_id()
        
        # Get parent context if exists
        parent_context = CorrelationIdManager.get_current_context()
        parent_id = parent_context.correlation_id if parent_context else None
        
        # Create new context
        context = CorrelationContext(
            correlation_id=correlation_id,
            parent_id=parent_id,
            operation=operation,
            provider=provider,
            metadata=metadata
        )
        
        # Store previous context to restore later
        previous_context = getattr(_context_storage, 'context', None)
        previous_id = getattr(_context_storage, 'correlation_id', None)
        
        try:
            # Set new context
            CorrelationIdManager.set_context(context)
            logger.info("Operation started",
                       correlation_id=correlation_id,
                       parent_id=parent_id,
                       operation=operation,
                       provider=provider)
            
            yield context
            
            # Log successful completion
            elapsed = (datetime.now() - context.start_time).total_seconds()
            logger.info("Operation completed successfully",
                       correlation_id=correlation_id,
                       operation=operation,
                       elapsed_seconds=elapsed)
            
        except Exception as e:
            # Log error with context
            elapsed = (datetime.now() - context.start_time).total_seconds()
            logger.error("Operation failed",
                        correlation_id=correlation_id,
                        operation=operation,
                        exception_type=type(e).__name__,
                        exception_message=str(e),
                        elapsed_seconds=elapsed)
            
            # Add correlation ID to exception if it's a VortexError
            if hasattr(e, 'correlation_id'):
                e.correlation_id = correlation_id
            if hasattr(e, 'add_context'):
                e.add_context(
                    correlation_id=correlation_id,
                    operation=operation,
                    provider=provider
                )
            
            raise
            
        finally:
            # Restore previous context
            if previous_context:
                _context_storage.context = previous_context
                _context_storage.correlation_id = previous_id
            else:
                CorrelationIdManager.clear_context()
    
    @staticmethod
    def add_context_metadata(**metadata):
        """Add metadata to the current correlation context."""
        context = CorrelationIdManager.get_current_context()
        if context:
            context.metadata.update(metadata)
            logger.debug("Added context metadata",
                        correlation_id=context.correlation_id,
                        metadata=metadata)


def with_correlation(
    operation: Optional[str] = None,
    provider: Optional[str] = None,
    generate_id: bool = True
):
    """
    Decorator to add correlation context to a function.
    
    Args:
        operation: Name of the operation (defaults to function name)
        provider: Data provider name
        generate_id: Whether to generate a new correlation ID
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            op_name = operation or func.__name__
            
            # Use existing correlation ID if present and not generating new
            correlation_id = None
            if not generate_id:
                correlation_id = CorrelationIdManager.get_current_id()
            
            with CorrelationIdManager.correlation_context(
                correlation_id=correlation_id,
                operation=op_name,
                provider=provider
            ):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def with_provider_correlation(provider: str):
    """
    Decorator specifically for data provider operations.
    
    Args:
        provider: Name of the data provider
    """
    return with_correlation(provider=provider, generate_id=True)


class RequestTracker:
    """
    Helper class for tracking request metrics and performance.
    
    Works with correlation context to provide detailed request analytics.
    """
    
    def __init__(self):
        self._requests: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def start_request(self, correlation_id: str, operation: str, **metadata):
        """Start tracking a request."""
        with self._lock:
            self._requests[correlation_id] = {
                'operation': operation,
                'start_time': datetime.now(),
                'metadata': metadata,
                'status': 'in_progress'
            }
    
    def complete_request(self, correlation_id: str, success: bool = True, **result_metadata):
        """Mark a request as completed."""
        with self._lock:
            if correlation_id in self._requests:
                request = self._requests[correlation_id]
                request['end_time'] = datetime.now()
                request['duration'] = (request['end_time'] - request['start_time']).total_seconds()
                request['status'] = 'success' if success else 'failed'
                request['result_metadata'] = result_metadata
    
    def get_request_stats(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a specific request."""
        with self._lock:
            return self._requests.get(correlation_id)
    
    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently active requests."""
        with self._lock:
            return {
                cid: req for cid, req in self._requests.items()
                if req['status'] == 'in_progress'
            }
    
    def cleanup_old_requests(self, max_age_hours: int = 24):
        """Clean up old request tracking data."""
        with self._lock:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            to_remove = [
                cid for cid, req in self._requests.items()
                if req.get('end_time', req['start_time']) < cutoff_time
            ]
            
            for cid in to_remove:
                del self._requests[cid]
            
            if to_remove:
                logger.info(f"Cleaned up {len(to_remove)} old request tracking records")


# Global request tracker instance
_request_tracker = RequestTracker()

def get_request_tracker() -> RequestTracker:
    """Get the global request tracker instance."""
    return _request_tracker