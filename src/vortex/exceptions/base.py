"""
Base exception classes for Vortex.

Provides the foundational VortexError class that all other exceptions inherit from.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ExceptionContext:
    """Context information for Vortex exceptions."""

    help_text: Optional[str] = None
    error_code: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    user_action: Optional[str] = None
    technical_details: Optional[str] = None
    correlation_id: Optional[str] = None


class VortexError(Exception):
    """Base exception for all Vortex-related errors.

    All Vortex exceptions should inherit from this class to provide
    consistent error handling and user experience.

    Attributes:
        message: The error message
        help_text: Optional actionable guidance for the user
        error_code: Optional error code for programmatic handling
        correlation_id: Unique ID for tracking this error across logs
        context: Additional context information
        user_action: Suggested user action to resolve the issue
        technical_details: Technical information for debugging
    """

    def __init__(self, message: str, context: Optional[ExceptionContext] = None):
        self.message = message

        if context is not None:
            self.help_text = context.help_text
            self.error_code = context.error_code
            self.context = context.context
            self.user_action = context.user_action
            self.technical_details = context.technical_details
            self.correlation_id = context.correlation_id or str(uuid.uuid4())[:8]
        else:
            self.help_text = None
            self.error_code = None
            self.context = {}
            self.user_action = None
            self.technical_details = None
            self.correlation_id = str(uuid.uuid4())[:8]

        self.timestamp = datetime.now()
        super().__init__(message)

    def __str__(self) -> str:
        result = self.message

        if self.help_text:
            result += f"\n\n💡 Help: {self.help_text}"

        if self.user_action:
            result += f"\n\n🔧 Action: {self.user_action}"

        if self.context:
            context_items = [
                f"{k}: {v}" for k, v in self.context.items() if v is not None
            ]
            if context_items:
                result += f"\n\n📋 Context: {', '.join(context_items)}"

        result += f"\n\n🔍 Error ID: {self.correlation_id}"
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "help_text": self.help_text,
            "user_action": self.user_action,
            "technical_details": self.technical_details,
        }

    def add_context(self, **kwargs) -> "VortexError":
        """Add additional context to the exception."""
        self.context.update(kwargs)
        return self
