"""Phone Address Service with business logic."""

import logging
from datetime import datetime
from typing import Optional

from redis.exceptions import ConnectionError

from phone_address_service.models.schemas import (
    PhoneAddressRecord,
    CreatePhoneAddressRequest,
    UpdateAddressRequest
)
from phone_address_service.repositories.base import PhoneAddressRepository

logger = logging.getLogger(__name__)


class PhoneAddressService:
    """Service layer for phone address operations with business logic."""
    
    def __init__(self, repository: PhoneAddressRepository):
        """Initialize service with repository dependency.
        
        Args:
            repository: PhoneAddressRepository implementation
        """
        self.repository = repository
    
    async def get_address(self, phone: str) -> Optional[PhoneAddressRecord]:
        """Get address for a phone number.
        
        Args:
            phone: Phone number to lookup
            
        Returns:
            PhoneAddressRecord if found, None if not found
            
        Raises:
            ValueError: If phone format is invalid
            ConnectionError: If Redis is unavailable
        """
        # Validate phone format by creating a temporary record
        # This will raise ValueError if format is invalid
        try:
            PhoneAddressRecord(phone=phone, address="temp")
        except ValueError as e:
            logger.warning(
                "Invalid phone format in get request",
                extra={"phone": phone, "error": str(e), "operation": "get_address"}
            )
            raise ValueError(f"Invalid phone format: {str(e)}") from e
        
        try:
            record = await self.repository.get(phone)
            
            if record:
                logger.info(
                    "Address retrieved successfully",
                    extra={"phone": phone, "operation": "get_address"}
                )
            else:
                logger.info(
                    "Phone number not found",
                    extra={"phone": phone, "operation": "get_address"}
                )
            
            return record
            
        except ConnectionError:
            logger.error(
                "Redis unavailable during get operation",
                extra={"phone": phone, "operation": "get_address"}
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during get operation",
                extra={"phone": phone, "error": str(e), "operation": "get_address"}
            )
            raise
    
    async def create_record(self, request: CreatePhoneAddressRequest) -> PhoneAddressRecord:
        """Create a new phone address record.
        
        Args:
            request: CreatePhoneAddressRequest with phone and address
            
        Returns:
            Created PhoneAddressRecord
            
        Raises:
            ValueError: If phone already exists or validation fails
            ConnectionError: If Redis is unavailable
        """
        try:
            # Create record with timestamps
            record = PhoneAddressRecord(
                phone=request.phone,
                address=request.address,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Attempt to create in repository
            created_record = await self.repository.create(record)
            
            logger.info(
                "Phone address record created successfully",
                extra={"phone": request.phone, "operation": "create_record"}
            )
            
            return created_record
            
        except ValueError as e:
            # This covers both validation errors and duplicate phone numbers
            logger.warning(
                "Failed to create record due to validation or duplicate",
                extra={"phone": request.phone, "error": str(e), "operation": "create_record"}
            )
            raise
        except ConnectionError:
            logger.error(
                "Redis unavailable during create operation",
                extra={"phone": request.phone, "operation": "create_record"}
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during create operation",
                extra={"phone": request.phone, "error": str(e), "operation": "create_record"}
            )
            raise
    
    async def update_address(self, phone: str, request: UpdateAddressRequest) -> Optional[PhoneAddressRecord]:
        """Update address for existing phone number.
        
        Args:
            phone: Phone number to update
            request: UpdateAddressRequest with new address
            
        Returns:
            Updated PhoneAddressRecord if phone exists, None if not found
            
        Raises:
            ValueError: If phone format or address is invalid
            ConnectionError: If Redis is unavailable
        """
        # Validate phone format
        try:
            PhoneAddressRecord(phone=phone, address="temp")
        except ValueError as e:
            logger.warning(
                "Invalid phone format in update request",
                extra={"phone": phone, "error": str(e), "operation": "update_address"}
            )
            raise ValueError(f"Invalid phone format: {str(e)}") from e
        
        try:
            # Update in repository
            updated_record = await self.repository.update(phone, request.address)
            
            if updated_record:
                logger.info(
                    "Address updated successfully",
                    extra={"phone": phone, "operation": "update_address"}
                )
            else:
                logger.info(
                    "Phone number not found for update",
                    extra={"phone": phone, "operation": "update_address"}
                )
            
            return updated_record
            
        except ConnectionError:
            logger.error(
                "Redis unavailable during update operation",
                extra={"phone": phone, "operation": "update_address"}
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during update operation",
                extra={"phone": phone, "error": str(e), "operation": "update_address"}
            )
            raise
    
    async def delete_record(self, phone: str) -> bool:
        """Delete phone address record.
        
        Args:
            phone: Phone number to delete
            
        Returns:
            True if record was deleted, False if not found
            
        Raises:
            ValueError: If phone format is invalid
            ConnectionError: If Redis is unavailable
        """
        # Validate phone format
        try:
            PhoneAddressRecord(phone=phone, address="temp")
        except ValueError as e:
            logger.warning(
                "Invalid phone format in delete request",
                extra={"phone": phone, "error": str(e), "operation": "delete_record"}
            )
            raise ValueError(f"Invalid phone format: {str(e)}") from e
        
        try:
            # Delete from repository
            deleted = await self.repository.delete(phone)
            
            if deleted:
                logger.info(
                    "Record deleted successfully",
                    extra={"phone": phone, "operation": "delete_record"}
                )
            else:
                logger.info(
                    "Phone number not found for deletion",
                    extra={"phone": phone, "operation": "delete_record"}
                )
            
            return deleted
            
        except ConnectionError:
            logger.error(
                "Redis unavailable during delete operation",
                extra={"phone": phone, "operation": "delete_record"}
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during delete operation",
                extra={"phone": phone, "error": str(e), "operation": "delete_record"}
            )
            raise