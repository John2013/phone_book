"""Redis implementation of PhoneAddressRepository."""

import json
import logging
from datetime import datetime
from typing import Optional

from redis.exceptions import ConnectionError, TimeoutError, RedisError
from redis.asyncio import Redis

from phone_address_service.models.schemas import PhoneAddressRecord
from phone_address_service.repositories.base import PhoneAddressRepository
from phone_address_service.repositories.connection import get_redis_client
from phone_address_service.config.logging import LoggingService

logger = logging.getLogger(__name__)
logging_service = LoggingService(__name__)


class RedisPhoneAddressRepository(PhoneAddressRepository):
    """Redis implementation of PhoneAddressRepository."""
    
    def __init__(self):
        self._key_prefix = "phone:"
    
    def _make_key(self, phone: str) -> str:
        """Create Redis key for phone number."""
        return f"{self._key_prefix}{phone}"
    
    async def _get_redis_client(self) -> Redis:
        """Get Redis client with error handling."""
        try:
            return await get_redis_client()
        except (ConnectionError, TimeoutError) as e:
            logging_service.log_error(
                "Redis connection error",
                e,
                operation="get_client"
            )
            raise ConnectionError("Redis service unavailable") from e
        except Exception as e:
            logging_service.log_error(
                "Unexpected error getting Redis client",
                e,
                operation="get_client"
            )
            raise
    
    async def get(self, phone: str) -> Optional[PhoneAddressRecord]:
        """Get phone address record by phone number."""
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(phone)
            
            data = await redis_client.get(key)
            
            if data is None:
                logger.debug(
                    "Phone number not found",
                    extra={"phone": phone, "operation": "get"}
                )
                return None
            
            # Parse JSON data
            record_data = json.loads(data)
            record = PhoneAddressRecord(**record_data)
            
            logger.debug(
                "Phone address record retrieved",
                extra={"phone": phone, "operation": "get"}
            )
            
            return record
            
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse stored JSON data",
                extra={"phone": phone, "error": str(e), "operation": "get"}
            )
            raise ValueError("Corrupted data in storage") from e
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Redis connection error during get operation",
                extra={"phone": phone, "error": str(e), "operation": "get"}
            )
            raise ConnectionError("Redis service unavailable") from e
            
        except RedisError as e:
            logger.error(
                "Redis error during get operation",
                extra={"phone": phone, "error": str(e), "operation": "get"}
            )
            raise
            
        except Exception as e:
            logger.error(
                "Unexpected error during get operation",
                extra={"phone": phone, "error": str(e), "operation": "get"}
            )
            raise
    
    async def create(self, record: PhoneAddressRecord) -> PhoneAddressRecord:
        """Create a new phone address record."""
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(record.phone)
            
            # Check if record already exists
            exists = await redis_client.exists(key)
            if exists:
                logger.warning(
                    "Attempted to create duplicate phone record",
                    extra={"phone": record.phone, "operation": "create"}
                )
                raise ValueError(f"Phone number {record.phone} already exists")
            
            # Serialize record to JSON
            record_json = record.model_dump_json()
            
            # Store in Redis
            success = await redis_client.set(key, record_json)
            
            if not success:
                logger.error(
                    "Failed to store record in Redis",
                    extra={"phone": record.phone, "operation": "create"}
                )
                raise RuntimeError("Failed to store record")
            
            logger.info(
                "Phone address record created",
                extra={"phone": record.phone, "operation": "create"}
            )
            
            return record
            
        except ValueError:
            # Re-raise validation errors as-is
            raise
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Redis connection error during create operation",
                extra={"phone": record.phone, "error": str(e), "operation": "create"}
            )
            raise ConnectionError("Redis service unavailable") from e
            
        except RedisError as e:
            logger.error(
                "Redis error during create operation",
                extra={"phone": record.phone, "error": str(e), "operation": "create"}
            )
            raise
            
        except Exception as e:
            logger.error(
                "Unexpected error during create operation",
                extra={"phone": record.phone, "error": str(e), "operation": "create"}
            )
            raise
    
    async def update(self, phone: str, address: str) -> Optional[PhoneAddressRecord]:
        """Update address for existing phone number."""
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(phone)
            
            # Get existing record
            existing_record = await self.get(phone)
            if existing_record is None:
                logger.debug(
                    "Phone number not found for update",
                    extra={"phone": phone, "operation": "update"}
                )
                return None
            
            # Create updated record
            updated_record = PhoneAddressRecord(
                phone=phone,
                address=address,
                created_at=existing_record.created_at,
                updated_at=datetime.utcnow()
            )
            
            # Serialize and store
            record_json = updated_record.model_dump_json()
            success = await redis_client.set(key, record_json)
            
            if not success:
                logger.error(
                    "Failed to update record in Redis",
                    extra={"phone": phone, "operation": "update"}
                )
                raise RuntimeError("Failed to update record")
            
            logger.info(
                "Phone address record updated",
                extra={"phone": phone, "operation": "update"}
            )
            
            return updated_record
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Redis connection error during update operation",
                extra={"phone": phone, "error": str(e), "operation": "update"}
            )
            raise ConnectionError("Redis service unavailable") from e
            
        except RedisError as e:
            logger.error(
                "Redis error during update operation",
                extra={"phone": phone, "error": str(e), "operation": "update"}
            )
            raise
            
        except Exception as e:
            logger.error(
                "Unexpected error during update operation",
                extra={"phone": phone, "error": str(e), "operation": "update"}
            )
            raise
    
    async def delete(self, phone: str) -> bool:
        """Delete phone address record."""
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(phone)
            
            # Delete the key
            deleted_count = await redis_client.delete(key)
            
            if deleted_count > 0:
                logger.info(
                    "Phone address record deleted",
                    extra={"phone": phone, "operation": "delete"}
                )
                return True
            else:
                logger.debug(
                    "Phone number not found for deletion",
                    extra={"phone": phone, "operation": "delete"}
                )
                return False
                
        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Redis connection error during delete operation",
                extra={"phone": phone, "error": str(e), "operation": "delete"}
            )
            raise ConnectionError("Redis service unavailable") from e
            
        except RedisError as e:
            logger.error(
                "Redis error during delete operation",
                extra={"phone": phone, "error": str(e), "operation": "delete"}
            )
            raise
            
        except Exception as e:
            logger.error(
                "Unexpected error during delete operation",
                extra={"phone": phone, "error": str(e), "operation": "delete"}
            )
            raise
    
    async def exists(self, phone: str) -> bool:
        """Check if phone number exists."""
        try:
            redis_client = await self._get_redis_client()
            key = self._make_key(phone)
            
            exists = await redis_client.exists(key)
            
            logger.debug(
                "Phone existence check",
                extra={"phone": phone, "exists": bool(exists), "operation": "exists"}
            )
            
            return bool(exists)
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(
                "Redis connection error during exists operation",
                extra={"phone": phone, "error": str(e), "operation": "exists"}
            )
            raise ConnectionError("Redis service unavailable") from e
            
        except RedisError as e:
            logger.error(
                "Redis error during exists operation",
                extra={"phone": phone, "error": str(e), "operation": "exists"}
            )
            raise
            
        except Exception as e:
            logger.error(
                "Unexpected error during exists operation",
                extra={"phone": phone, "error": str(e), "operation": "exists"}
            )
            raise