"""
XenFlow Mailer - Structured Logging
"""

import sys
import logging
from typing import Any
import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

from app.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Determine log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        TimeStamper(fmt="iso"),
    ]
    
    if settings.LOG_FORMAT == "json":
        processors.append(JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Also configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name or __name__)


class LogContext:
    """Context manager for adding temporary context to logs."""
    
    def __init__(self, **kwargs: Any):
        self.kwargs = kwargs
    
    def __enter__(self):
        structlog.contextvars.bind_contextvars(**self.kwargs)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        structlog.contextvars.unbind_contextvars(*self.kwargs.keys())

