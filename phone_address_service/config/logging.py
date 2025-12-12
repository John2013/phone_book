"""Logging configuration for the application."""

import logging
import logging.config
import sys
import uuid
from contextvars import ContextVar
from typing import Dict, Any, Optional

from .settings import settings

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIdFormatter(logging.Formatter):
    """Custom formatter that includes correlation ID in log records."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with correlation ID."""
        # Add correlation ID to the record
        record.correlation_id = correlation_id.get() or "N/A"
        return super().format(record)


class StructuredFormatter(CorrelationIdFormatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        import json
        
        # Get correlation ID
        corr_id = correlation_id.get() or "N/A"
        
        # Build log entry
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": corr_id,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, 'phone'):
            log_entry['phone'] = record.phone
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'error'):
            log_entry['error'] = record.error
        
        # Add any other extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs', 
                          'relativeCreated', 'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info', 'correlation_id',
                          'phone', 'operation', 'error']:
                if not key.startswith('_'):
                    log_entry[key] = value
        
        return json.dumps(log_entry, ensure_ascii=False)


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration based on settings."""
    
    if settings.log_format == "json":
        formatter_config = {
            "()": "phone_address_service.config.logging.StructuredFormatter",
            "datefmt": "%Y-%m-%dT%H:%M:%S"
        }
    else:
        formatter_config = {
            "()": "phone_address_service.config.logging.CorrelationIdFormatter",
            "format": "%(asctime)s - %(correlation_id)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": formatter_config,
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "default",
                "level": settings.log_level,
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console"],
        },
        "loggers": {
            "phone_address_service": {
                "level": settings.log_level,
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }


def setup_logging() -> None:
    """Setup logging configuration."""
    config = get_logging_config()
    logging.config.dictConfig(config)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def set_correlation_id(corr_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id.set(corr_id)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id.get()


class LoggingService:
    """Service for consistent logging across the application."""
    
    def __init__(self, logger_name: str):
        """Initialize logging service with logger name."""
        self.logger = logging.getLogger(logger_name)
    
    def log_operation(self, level: str, message: str, phone: Optional[str] = None, 
                     operation: Optional[str] = None, error: Optional[str] = None, **kwargs) -> None:
        """Log operation with consistent format.
        
        Args:
            level: Log level (info, warning, error, debug)
            message: Log message
            phone: Phone number involved in operation
            operation: Operation name
            error: Error message if applicable
            **kwargs: Additional fields to log
        """
        extra = {}
        if phone:
            extra['phone'] = phone
        if operation:
            extra['operation'] = operation
        if error:
            extra['error'] = error
        
        # Add any additional fields
        extra.update(kwargs)
        
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra)
    
    def log_crud_operation(self, operation: str, phone: str, success: bool, 
                          error: Optional[str] = None, **kwargs) -> None:
        """Log CRUD operation with standard format.
        
        Args:
            operation: CRUD operation name (create, read, update, delete)
            phone: Phone number
            success: Whether operation was successful
            error: Error message if operation failed
            **kwargs: Additional fields
        """
        if success:
            self.log_operation(
                "info", 
                f"{operation.capitalize()} operation completed successfully",
                phone=phone,
                operation=operation,
                **kwargs
            )
        else:
            self.log_operation(
                "error" if error else "warning",
                f"{operation.capitalize()} operation failed",
                phone=phone,
                operation=operation,
                error=error,
                **kwargs
            )
    
    def log_error(self, message: str, error: Exception, phone: Optional[str] = None, 
                  operation: Optional[str] = None, **kwargs) -> None:
        """Log error with consistent format.
        
        Args:
            message: Error message
            error: Exception object
            phone: Phone number if applicable
            operation: Operation name if applicable
            **kwargs: Additional fields
        """
        self.log_operation(
            "error",
            message,
            phone=phone,
            operation=operation,
            error=str(error),
            error_type=type(error).__name__,
            **kwargs
        )