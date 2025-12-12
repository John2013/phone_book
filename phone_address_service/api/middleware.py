"""Middleware for FastAPI application."""

import logging
from typing import Callable
from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis.exceptions import ConnectionError, TimeoutError, RedisError
from pydantic import ValidationError

from phone_address_service.config.logging import (
    generate_correlation_id, 
    set_correlation_id,
    LoggingService
)

logger = logging.getLogger(__name__)
logging_service = LoggingService(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs for request tracing."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID."""
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = generate_correlation_id()
        
        # Set correlation ID in context
        set_correlation_id(correlation_id)
        
        # Log request
        logging_service.log_operation(
            "info",
            f"Request started: {request.method} {request.url.path}",
            operation="request_start",
            method=request.method,
            path=str(request.url.path),
            query_params=str(request.query_params) if request.query_params else None
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            
            # Log response
            logging_service.log_operation(
                "info",
                f"Request completed: {request.method} {request.url.path}",
                operation="request_complete",
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code
            )
            
            return response
            
        except Exception as e:
            # Log error
            logging_service.log_error(
                f"Request failed: {request.method} {request.url.path}",
                e,
                operation="request_error",
                method=request.method,
                path=str(request.url.path)
            )
            
            # Return error response with correlation ID
            error_response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "correlation_id": correlation_id
                }
            )
            error_response.headers["X-Correlation-ID"] = correlation_id
            return error_response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        import time
        
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Log request/response details
        logging_service.log_operation(
            "info",
            "Request processed",
            operation="request_metrics",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            process_time_ms=round(process_time * 1000, 2),
            content_length=response.headers.get("content-length")
        )
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors and return appropriate HTTP responses."""
        try:
            response = await call_next(request)
            return response
            
        except HTTPException:
            # Let FastAPI handle HTTPExceptions normally
            raise
            
        except (ConnectionError, TimeoutError) as e:
            # Redis connection errors
            logging_service.log_error(
                "Redis connection error",
                e,
                operation="error_handling",
                path=str(request.url.path),
                method=request.method
            )
            
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "message": "Redis service unavailable"
                }
            )
            
        except RedisError as e:
            # Other Redis errors
            logging_service.log_error(
                "Redis error",
                e,
                operation="error_handling",
                path=str(request.url.path),
                method=request.method
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "Database error occurred"
                }
            )
            
        except ValidationError as e:
            # Pydantic validation errors
            logging_service.log_operation(
                "warning",
                "Validation error",
                operation="error_handling",
                path=str(request.url.path),
                method=request.method,
                error=str(e)
            )
            
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Bad Request",
                    "message": "Invalid request data",
                    "details": e.errors()
                }
            )
            
        except ValueError as e:
            # Business logic validation errors
            logging_service.log_operation(
                "warning",
                "Value error",
                operation="error_handling",
                path=str(request.url.path),
                method=request.method,
                error=str(e)
            )
            
            # Check if it's a duplicate error (409) or validation error (400)
            if "already exists" in str(e):
                return JSONResponse(
                    status_code=409,
                    content={
                        "error": "Conflict",
                        "message": str(e)
                    }
                )
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Bad Request",
                        "message": str(e)
                    }
                )
                
        except Exception as e:
            # Unexpected errors
            logging_service.log_error(
                "Unexpected error",
                e,
                operation="error_handling",
                path=str(request.url.path),
                method=request.method
            )
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred"
                }
            )