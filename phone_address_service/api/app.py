"""FastAPI application factory and configuration."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import ConnectionError

from phone_address_service.config.logging import setup_logging, LoggingService
from phone_address_service.api.middleware import CorrelationIdMiddleware, LoggingMiddleware, ErrorHandlingMiddleware
from phone_address_service.models.schemas import (
    PhoneAddressResponse,
    CreatePhoneAddressRequest,
    UpdateAddressRequest,
    ErrorResponse,
    HealthCheckResponse
)
from phone_address_service.services.phone_address_service import PhoneAddressService
from phone_address_service.repositories.redis_repository import RedisPhoneAddressRepository
from phone_address_service.repositories.connection import redis_manager

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
    
    # Initialize Redis connection and log startup status
    try:
        await redis_manager.initialize()
        logging_service.log_operation(
            "info",
            "Redis connection established successfully",
            operation="redis_startup",
            redis_host=redis_manager._pool.connection_kwargs.get('host') if redis_manager._pool else 'unknown',
            redis_port=redis_manager._pool.connection_kwargs.get('port') if redis_manager._pool else 'unknown'
        )
    except Exception as e:
        logging_service.log_error(
            "Failed to establish Redis connection during startup",
            e,
            operation="redis_startup"
        )
        # Don't fail startup - let health check handle Redis availability
    
    yield
    
    # Shutdown
    logging_service.log_operation(
        "info",
        "Phone Address Service shutting down...",
        operation="service_shutdown"
    )
    
    # Close Redis connection
    try:
        await redis_manager.close()
        logging_service.log_operation(
            "info",
            "Redis connection closed successfully",
            operation="redis_shutdown"
        )
    except Exception as e:
        logging_service.log_error(
            "Error closing Redis connection during shutdown",
            e,
            operation="redis_shutdown"
        )


# Dependency injection
def get_phone_address_service() -> PhoneAddressService:
    """Get PhoneAddressService instance with Redis repository."""
    repository = RedisPhoneAddressRepository()
    return PhoneAddressService(repository)


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
    
    # Add error handling middleware (before logging to catch errors)
    app.add_middleware(ErrorHandlingMiddleware)
    
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
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check():
        """Health check endpoint with Redis connectivity check."""
        logging_service.log_operation(
            "info",
            "Health check requested",
            operation="health_check"
        )
        
        # Check Redis connectivity
        redis_connected = await redis_manager.health_check()
        
        # Determine overall service status
        if redis_connected:
            status = "healthy"
            logging_service.log_operation(
                "info",
                "Health check passed - all systems operational",
                operation="health_check",
                redis_connected=redis_connected
            )
        else:
            status = "degraded"
            logging_service.log_operation(
                "warning",
                "Health check shows degraded status - Redis unavailable",
                operation="health_check",
                redis_connected=redis_connected
            )
        
        return HealthCheckResponse(
            status=status,
            redis_connected=redis_connected
        )
    
    # Phone address endpoints
    @app.get(
        "/phone/{phone_number}",
        response_model=PhoneAddressResponse,
        responses={
            404: {"model": ErrorResponse, "description": "Phone number not found"},
            400: {"model": ErrorResponse, "description": "Invalid phone number format"},
            503: {"model": ErrorResponse, "description": "Service unavailable"}
        }
    )
    async def get_phone_address(
        phone_number: str,
        service: PhoneAddressService = Depends(get_phone_address_service)
    ):
        """Get address for a phone number."""
        try:
            record = await service.get_address(phone_number)
            
            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Phone number not found"
                )
            
            return PhoneAddressResponse(
                phone=record.phone,
                address=record.address,
                created_at=record.created_at,
                updated_at=record.updated_at
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except ConnectionError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service unavailable"
            )
    
    @app.post(
        "/phone",
        response_model=PhoneAddressResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            409: {"model": ErrorResponse, "description": "Phone number already exists"},
            400: {"model": ErrorResponse, "description": "Invalid request data"},
            503: {"model": ErrorResponse, "description": "Service unavailable"}
        }
    )
    async def create_phone_address(
        request: CreatePhoneAddressRequest,
        service: PhoneAddressService = Depends(get_phone_address_service)
    ):
        """Create a new phone-address record."""
        try:
            record = await service.create_record(request)
            
            return PhoneAddressResponse(
                phone=record.phone,
                address=record.address,
                created_at=record.created_at,
                updated_at=record.updated_at
            )
            
        except ValueError as e:
            # Handle both validation errors and duplicate phone numbers
            if "already exists" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=str(e)
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        except ConnectionError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service unavailable"
            )
    
    @app.put(
        "/phone/{phone_number}",
        response_model=PhoneAddressResponse,
        responses={
            404: {"model": ErrorResponse, "description": "Phone number not found"},
            400: {"model": ErrorResponse, "description": "Invalid request data"},
            503: {"model": ErrorResponse, "description": "Service unavailable"}
        }
    )
    async def update_phone_address(
        phone_number: str,
        request: UpdateAddressRequest,
        service: PhoneAddressService = Depends(get_phone_address_service)
    ):
        """Update address for an existing phone number."""
        try:
            record = await service.update_address(phone_number, request)
            
            if record is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Phone number not found"
                )
            
            return PhoneAddressResponse(
                phone=record.phone,
                address=record.address,
                created_at=record.created_at,
                updated_at=record.updated_at
            )
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except ConnectionError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service unavailable"
            )
    
    @app.delete(
        "/phone/{phone_number}",
        status_code=status.HTTP_204_NO_CONTENT,
        responses={
            404: {"model": ErrorResponse, "description": "Phone number not found"},
            400: {"model": ErrorResponse, "description": "Invalid phone number format"},
            503: {"model": ErrorResponse, "description": "Service unavailable"}
        }
    )
    async def delete_phone_address(
        phone_number: str,
        service: PhoneAddressService = Depends(get_phone_address_service)
    ):
        """Delete a phone-address record."""
        try:
            deleted = await service.delete_record(phone_number)
            
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Phone number not found"
                )
            
            # Return 204 No Content (no response body)
            return None
            
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except ConnectionError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service unavailable"
            )
    
    return app


# Create the application instance
app = create_app()