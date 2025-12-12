"""FastAPI application factory and configuration."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from phone_address_service.config.logging import setup_logging, LoggingService
from phone_address_service.api.middleware import CorrelationIdMiddleware, LoggingMiddleware

logger = logging.getLogger(__name__)
logging_service = LoggingService(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup
    setup_logging()
    logging_service.log_operation(
        "info", 
        "Phone Address Service starting up...",
        operation="service_startup"
    )
    
    yield
    
    # Shutdown
    logging_service.log_operation(
        "info",
        "Phone Address Service shutting down...",
        operation="service_shutdown"
    )


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Phone Address Service",
        description="Микросервис для хранения и управления связками телефон-адрес",
        version="0.1.0",
        lifespan=lifespan,
    )
    
    # Add correlation ID middleware (first to ensure all requests have correlation ID)
    app.add_middleware(CorrelationIdMiddleware)
    
    # Add logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Basic health check endpoint."""
        logging_service.log_operation(
            "info",
            "Health check requested",
            operation="health_check"
        )
        return {"status": "healthy", "service": "phone-address-service"}
    
    return app


# Create the application instance
app = create_app()