"""Repository layer for data access."""

from phone_address_service.repositories.base import PhoneAddressRepository
from phone_address_service.repositories.redis_repository import RedisPhoneAddressRepository
from phone_address_service.repositories.connection import redis_manager, get_redis_client

__all__ = [
    "PhoneAddressRepository",
    "RedisPhoneAddressRepository", 
    "redis_manager",
    "get_redis_client"
]