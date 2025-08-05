"""
Unified correlation ID management for Vortex.

This module consolidates correlation ID functionality from the previous
utils.correlation and resilience.correlation modules into a single,
comprehensive implementation.

Key Features:
- Thread-local correlation ID storage
- Context management with nested correlation support
- Request tracking and performance monitoring
- Provider-specific correlation decorators
- Structured logging integration
- Exception correlation support

Usage:
    from vortex.core.correlation import (
        CorrelationIdManager, with_correlation, get_correlation_id
    )
    
    # Basic usage
    correlation_id = CorrelationIdManager.generate_id()
    
    # Context management
    with CorrelationIdManager.correlation_context(operation="download"):
        # Operation is tracked with correlation
        pass
    
    # Decorator usage
    @with_correlation(operation="process_data", provider="yahoo")
    def process_data():
        pass
"""

from .manager import (
    CorrelationIdManager,
    CorrelationContext,
    RequestTracker,
    get_request_tracker
)
from .decorators import (
    with_correlation,
    with_provider_correlation,
    track_operation
)
from .utils import (
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
    clear_correlation_id
)

__all__ = [
    # Core classes
    'CorrelationIdManager',
    'CorrelationContext', 
    'RequestTracker',
    
    # Decorators
    'with_correlation',
    'with_provider_correlation',
    'track_operation',
    
    # Utilities
    'get_correlation_id',
    'set_correlation_id',
    'generate_correlation_id',
    'clear_correlation_id',
    'get_request_tracker',
]