"""Logging configuration for the application."""

import logging
import logging.config
import sys
from typing import Dict, Any

from .settings import settings


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration based on settings."""
    
    if settings.log_format == "json":
        formatter_config = {
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
            "datefmt": "%Y-%m-%dT%H:%M:%S"
        }
    else:
        formatter_config = {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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