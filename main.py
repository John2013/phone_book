"""Main entry point for the Phone Address Service."""

import uvicorn
from phone_address_service.config.settings import settings
from phone_address_service.config.logging import setup_logging


def main():
    """Run the FastAPI application."""
    setup_logging()
    
    uvicorn.run(
        "phone_address_service.api.app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
        log_config=None,  # Use our custom logging configuration
    )


if __name__ == "__main__":
    main()
