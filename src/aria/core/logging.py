"""
Structured logging configuration for ARIA Hotel AI.

Uses structlog for structured logging with JSON output in production.
"""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder

from aria.core.config import settings


def setup_logging() -> None:
    """Configure structured logging based on environment."""
    
    # Set log level from settings
    log_level = getattr(logging, settings.log_level)
    
    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.contextvars.merge_contextvars,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add callsite info in development
    if settings.is_development:
        processors.insert(
            0,
            CallsiteParameterAdder(
                parameters=[
                    CallsiteParameter.FILENAME,
                    CallsiteParameter.LINENO,
                    CallsiteParameter.FUNC_NAME,
                ]
            ),
        )
    
    # Use console renderer in development, JSON in production
    if settings.is_development:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Suppress noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Set specific log levels for our modules
    logging.getLogger("aria").setLevel(log_level)


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def log_context(**kwargs: Any) -> Dict[str, Any]:
    """
    Add context to all subsequent log messages in this context.
    
    Args:
        **kwargs: Key-value pairs to add to log context
        
    Returns:
        Current context dictionary
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**kwargs)
    return kwargs


def log_request_context(
    request_id: str,
    user_id: str | None = None,
    session_id: str | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Add request-specific context to logs.
    
    Args:
        request_id: Unique request identifier
        user_id: User identifier (if authenticated)
        session_id: Session identifier
        **kwargs: Additional context
        
    Returns:
        Context dictionary
    """
    context = {
        "request_id": request_id,
        "user_id": user_id,
        "session_id": session_id,
        **kwargs,
    }
    return log_context(**context)


# Initialize logging on import
setup_logging()
