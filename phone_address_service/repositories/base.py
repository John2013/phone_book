"""Abstract repository interface for phone address data."""

from abc import ABC, abstractmethod
from typing import Optional

from phone_address_service.models.schemas import PhoneAddressRecord


class PhoneAddressRepository(ABC):
    """Abstract repository interface for phone address operations."""
    
    @abstractmethod
    async def get(self, phone: str) -> Optional[PhoneAddressRecord]:
        """Get phone address record by phone number.
        
        Args:
            phone: Phone number to lookup
            
        Returns:
            PhoneAddressRecord if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def create(self, record: PhoneAddressRecord) -> PhoneAddressRecord:
        """Create a new phone address record.
        
        Args:
            record: PhoneAddressRecord to create
            
        Returns:
            Created PhoneAddressRecord
            
        Raises:
            ValueError: If record already exists
        """
        pass
    
    @abstractmethod
    async def update(self, phone: str, address: str) -> Optional[PhoneAddressRecord]:
        """Update address for existing phone number.
        
        Args:
            phone: Phone number to update
            address: New address value
            
        Returns:
            Updated PhoneAddressRecord if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, phone: str) -> bool:
        """Delete phone address record.
        
        Args:
            phone: Phone number to delete
            
        Returns:
            True if record was deleted, False if not found
        """
        pass
    
    @abstractmethod
    async def exists(self, phone: str) -> bool:
        """Check if phone number exists.
        
        Args:
            phone: Phone number to check
            
        Returns:
            True if exists, False otherwise
        """
        pass