import logging
import json
import traceback
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime


def init_logging(level=logging.INFO):
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')


class LoggingContext:

    def __init__(self, entry_msg=None, success_msg=None, failure_msg=None, exit_msg=None, logger=None,
                 entry_level=logging.DEBUG, exit_level=logging.DEBUG,
                 success_level=logging.INFO, failure_level=logging.ERROR):
        self.entry_msg = entry_msg
        self.success_msg = success_msg
        self.failure_msg = failure_msg
        self.exit_msg = exit_msg
        self.logger = logger or logging.getLogger(__name__)
        self.entry_level = entry_level
        self.exit_level = exit_level
        self.success_level = success_level
        self.failure_level = failure_level

    def __enter__(self):
        self.log(self.entry_msg, level=self.entry_level)

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is None:
            self.log(self.success_msg, level=self.success_level)
        else:
            self.log(self.failure_msg, level=self.failure_level)

        self.log(self.exit_msg, level=self.exit_level)

    def log(self, message, level=logging.INFO):
        if message:
            self.logger.log(level, message)


class StructuredErrorLogger:
    """Enhanced error logging with structured context and correlation IDs."""
    
    def __init__(self, logger_name: str = "vortex.error"):
        """Initialize the structured error logger.
        
        Args:
            logger_name: Name of the logger to use
        """
        self.logger = logging.getLogger(logger_name)
    
    def log_error(self, 
                  error: Exception,
                  message: str,
                  correlation_id: Optional[str] = None,
                  context: Optional[Dict[str, Any]] = None,
                  user_id: Optional[str] = None,
                  operation: Optional[str] = None,
                  provider: Optional[str] = None,
                  include_traceback: bool = True) -> str:
        """Log an error with structured context.
        
        Args:
            error: The exception that occurred
            message: Human-readable error message
            correlation_id: Unique ID to track related operations
            context: Additional context data
            user_id: User identifier if available
            operation: Operation being performed when error occurred
            provider: Data provider involved in the error
            include_traceback: Whether to include full traceback
            
        Returns:
            The correlation ID used for this error
        """
        if correlation_id is None:
            correlation_id = self.generate_correlation_id()
        
        error_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "message": message,
            "context": context or {},
        }
        
        # Add optional fields
        if user_id:
            error_data["user_id"] = user_id
        if operation:
            error_data["operation"] = operation
        if provider:
            error_data["provider"] = provider
        
        # Add VortexError specific fields if available
        if hasattr(error, 'correlation_id'):
            error_data["vortex_correlation_id"] = error.correlation_id
        if hasattr(error, 'error_code'):
            error_data["error_code"] = error.error_code
        if hasattr(error, 'context'):
            error_data["vortex_context"] = error.context
        
        # Add traceback if requested
        if include_traceback:
            error_data["traceback"] = traceback.format_exc()
        
        # Log as structured JSON for better parsing
        self.logger.error(
            f"{message} [ID: {correlation_id}]",
            extra={
                "error_data": error_data,
                "correlation_id": correlation_id,
                "structured": True
            }
        )
        
        return correlation_id
    
    def log_operation_start(self, 
                           operation: str,
                           correlation_id: Optional[str] = None,
                           context: Optional[Dict[str, Any]] = None) -> str:
        """Log the start of an operation.
        
        Args:
            operation: Operation being started
            correlation_id: Existing correlation ID or None to generate new one
            context: Additional context data
            
        Returns:
            The correlation ID for this operation
        """
        if correlation_id is None:
            correlation_id = self.generate_correlation_id()
        
        operation_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "operation": operation,
            "status": "started",
            "context": context or {}
        }
        
        self.logger.info(
            f"Operation started: {operation} [ID: {correlation_id}]",
            extra={
                "operation_data": operation_data,
                "correlation_id": correlation_id,
                "structured": True
            }
        )
        
        return correlation_id
    
    def log_operation_success(self, 
                             operation: str,
                             correlation_id: str,
                             duration_ms: Optional[float] = None,
                             context: Optional[Dict[str, Any]] = None) -> None:
        """Log successful completion of an operation.
        
        Args:
            operation: Operation that completed
            correlation_id: Correlation ID from operation start
            duration_ms: Operation duration in milliseconds
            context: Additional context data
        """
        operation_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "operation": operation,
            "status": "completed",
            "context": context or {}
        }
        
        if duration_ms is not None:
            operation_data["duration_ms"] = duration_ms
        
        self.logger.info(
            f"Operation completed: {operation} [ID: {correlation_id}]",
            extra={
                "operation_data": operation_data,
                "correlation_id": correlation_id,
                "structured": True
            }
        )
    
    def log_operation_failure(self, 
                             operation: str,
                             correlation_id: str,
                             error: Exception,
                             duration_ms: Optional[float] = None,
                             context: Optional[Dict[str, Any]] = None) -> None:
        """Log failure of an operation.
        
        Args:
            operation: Operation that failed
            correlation_id: Correlation ID from operation start
            error: Exception that caused the failure
            duration_ms: Operation duration in milliseconds
            context: Additional context data
        """
        operation_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": correlation_id,
            "operation": operation,
            "status": "failed",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        
        if duration_ms is not None:
            operation_data["duration_ms"] = duration_ms
        
        self.logger.error(
            f"Operation failed: {operation} [ID: {correlation_id}]",
            extra={
                "operation_data": operation_data,
                "correlation_id": correlation_id,
                "structured": True
            }
        )
    
    @staticmethod
    def generate_correlation_id() -> str:
        """Generate a unique correlation ID."""
        return str(uuid4())[:8]  # Short ID for readability


# Global structured logger instance
_structured_logger = None

def get_structured_logger() -> StructuredErrorLogger:
    """Get the global structured error logger instance."""
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredErrorLogger()
    return _structured_logger


def log_error_with_context(error: Exception, 
                          message: str,
                          **context) -> str:
    """Convenience function to log an error with context.
    
    Args:
        error: The exception that occurred
        message: Human-readable error message
        **context: Additional context as keyword arguments
        
    Returns:
        The correlation ID for this error
    """
    logger = get_structured_logger()
    return logger.log_error(error, message, context=context)
