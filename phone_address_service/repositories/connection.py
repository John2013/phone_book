"""Redis connection management with health checks and error handling."""

import asyncio
import logging
from typing import Optional
import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from phone_address_service.config.settings import settings

logger = logging.getLogger(__name__)


class RedisConnectionManager:
    """Manages Redis connection pool with health checks and error handling."""
    
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None
        self._is_connected = False
    
    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self._pool = ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                socket_timeout=settings.redis_socket_timeout,
                socket_connect_timeout=settings.redis_connection_timeout,
                max_connections=settings.redis_max_connections,
                decode_responses=True,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            self._client = Redis(connection_pool=self._pool)
            
            # Test connection
            await self.health_check()
            self._is_connected = True
            
            logger.info(
                "Redis connection initialized successfully",
                extra={
                    "redis_host": settings.redis_host,
                    "redis_port": settings.redis_port,
                    "redis_db": settings.redis_db,
                    "max_connections": settings.redis_max_connections
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize Redis connection",
                extra={
                    "error": str(e),
                    "redis_host": settings.redis_host,
                    "redis_port": settings.redis_port
                }
            )
            raise
    
    async def get_client(self) -> Redis:
        """Get Redis client instance."""
        if not self._client or not self._is_connected:
            await self.initialize()
        
        return self._client
    
    async def health_check(self) -> bool:
        """Perform Redis health check."""
        try:
            if not self._client:
                return False
            
            # Simple ping to check connection
            result = await self._client.ping()
            
            if result:
                logger.debug("Redis health check passed")
                return True
            else:
                logger.warning("Redis health check failed: ping returned False")
                return False
                
        except (ConnectionError, TimeoutError) as e:
            logger.warning(
                "Redis health check failed: connection error",
                extra={"error": str(e)}
            )
            self._is_connected = False
            return False
            
        except RedisError as e:
            logger.error(
                "Redis health check failed: Redis error",
                extra={"error": str(e)}
            )
            self._is_connected = False
            return False
            
        except Exception as e:
            logger.error(
                "Redis health check failed: unexpected error",
                extra={"error": str(e)}
            )
            self._is_connected = False
            return False
    
    async def close(self) -> None:
        """Close Redis connection pool."""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
            
            if self._pool:
                await self._pool.aclose()
                self._pool = None
            
            self._is_connected = False
            logger.info("Redis connection closed successfully")
            
        except Exception as e:
            logger.error(
                "Error closing Redis connection",
                extra={"error": str(e)}
            )
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is connected."""
        return self._is_connected
    
    async def reconnect(self) -> None:
        """Reconnect to Redis."""
        logger.info("Attempting to reconnect to Redis")
        await self.close()
        await self.initialize()


# Global connection manager instance
redis_manager = RedisConnectionManager()


async def get_redis_client() -> Redis:
    """Dependency function to get Redis client."""
    return await redis_manager.get_client()