"""Unit tests for repository operations."""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from phone_address_service.models.schemas import PhoneAddressRecord
from phone_address_service.repositories.redis_repository import RedisPhoneAddressRepository
from phone_address_service.repositories.connection import RedisConnectionManager


class TestRedisConnectionManager:
    """Test Redis connection management."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create a fresh connection manager for each test."""
        return RedisConnectionManager()
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, connection_manager):
        """Test successful Redis connection initialization."""
        with patch('phone_address_service.repositories.connection.ConnectionPool') as mock_pool_class, \
             patch('phone_address_service.repositories.connection.Redis') as mock_redis_class:
            
            mock_pool = MagicMock()
            mock_pool_class.return_value = mock_pool
            
            mock_redis = AsyncMock()
            mock_redis.ping.return_value = True
            mock_redis_class.return_value = mock_redis
            
            await connection_manager.initialize()
            
            assert connection_manager.is_connected
            mock_pool_class.assert_called_once()
            mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self, connection_manager):
        """Test Redis connection initialization failure."""
        with patch('phone_address_service.repositories.connection.ConnectionPool') as mock_pool_class:
            mock_pool_class.side_effect = ConnectionError("Connection failed")
            
            with pytest.raises(ConnectionError):
                await connection_manager.initialize()
            
            assert not connection_manager.is_connected
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, connection_manager):
        """Test successful health check."""
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        connection_manager._client = mock_redis
        
        result = await connection_manager.health_check()
        
        assert result is True
        mock_redis.ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_connection_error(self, connection_manager):
        """Test health check with connection error."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = ConnectionError("Connection lost")
        connection_manager._client = mock_redis
        connection_manager._is_connected = True
        
        result = await connection_manager.health_check()
        
        assert result is False
        assert not connection_manager.is_connected
    
    @pytest.mark.asyncio
    async def test_health_check_timeout_error(self, connection_manager):
        """Test health check with timeout error."""
        mock_redis = AsyncMock()
        mock_redis.ping.side_effect = TimeoutError("Timeout")
        connection_manager._client = mock_redis
        connection_manager._is_connected = True
        
        result = await connection_manager.health_check()
        
        assert result is False
        assert not connection_manager.is_connected
    
    @pytest.mark.asyncio
    async def test_close_connection(self, connection_manager):
        """Test closing Redis connection."""
        mock_redis = AsyncMock()
        mock_pool = AsyncMock()
        
        connection_manager._client = mock_redis
        connection_manager._pool = mock_pool
        connection_manager._is_connected = True
        
        await connection_manager.close()
        
        mock_redis.aclose.assert_called_once()
        mock_pool.aclose.assert_called_once()
        assert not connection_manager.is_connected
        assert connection_manager._client is None
        assert connection_manager._pool is None


class TestRedisPhoneAddressRepository:
    """Test Redis phone address repository operations."""
    
    @pytest.fixture
    def repository(self):
        """Create repository instance for testing."""
        return RedisPhoneAddressRepository()
    
    @pytest.fixture
    def sample_record(self):
        """Create sample phone address record."""
        return PhoneAddressRecord(
            phone="+1234567890",
            address="123 Main St, City, Country",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0)
        )
    
    @pytest.mark.asyncio
    async def test_get_existing_record(self, repository, sample_record):
        """Test getting an existing phone address record."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = sample_record.model_dump_json()
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            result = await repository.get("+1234567890")
            
            assert result is not None
            assert result.phone == sample_record.phone
            assert result.address == sample_record.address
            mock_redis.get.assert_called_once_with("phone:+1234567890")
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_record(self, repository):
        """Test getting a non-existent phone address record."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            result = await repository.get("+1234567890")
            
            assert result is None
            mock_redis.get.assert_called_once_with("phone:+1234567890")
    
    @pytest.mark.asyncio
    async def test_get_corrupted_data(self, repository):
        """Test getting corrupted JSON data."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "invalid json"
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            with pytest.raises(ValueError, match="Corrupted data in storage"):
                await repository.get("+1234567890")
    
    @pytest.mark.asyncio
    async def test_get_connection_error(self, repository):
        """Test get operation with Redis connection error."""
        with patch.object(repository, '_get_redis_client', side_effect=ConnectionError("Redis unavailable")):
            with pytest.raises(ConnectionError, match="Redis service unavailable"):
                await repository.get("+1234567890")
    
    @pytest.mark.asyncio
    async def test_create_new_record(self, repository, sample_record):
        """Test creating a new phone address record."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0  # Record doesn't exist
        mock_redis.set.return_value = True
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            result = await repository.create(sample_record)
            
            assert result == sample_record
            mock_redis.exists.assert_called_once_with("phone:+1234567890")
            mock_redis.set.assert_called_once_with("phone:+1234567890", sample_record.model_dump_json())
    
    @pytest.mark.asyncio
    async def test_create_duplicate_record(self, repository, sample_record):
        """Test creating a duplicate phone address record."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1  # Record exists
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            with pytest.raises(ValueError, match="already exists"):
                await repository.create(sample_record)
    
    @pytest.mark.asyncio
    async def test_create_redis_set_failure(self, repository, sample_record):
        """Test create operation when Redis set fails."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0
        mock_redis.set.return_value = False  # Set operation failed
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            with pytest.raises(RuntimeError, match="Failed to store record"):
                await repository.create(sample_record)
    
    @pytest.mark.asyncio
    async def test_update_existing_record(self, repository, sample_record):
        """Test updating an existing phone address record."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = sample_record.model_dump_json()
        mock_redis.set.return_value = True
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            result = await repository.update("+1234567890", "456 New St, New City")
            
            assert result is not None
            assert result.phone == "+1234567890"
            assert result.address == "456 New St, New City"
            assert result.created_at == sample_record.created_at
            assert result.updated_at > sample_record.updated_at
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_record(self, repository):
        """Test updating a non-existent phone address record."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            result = await repository.update("+1234567890", "456 New St")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_update_redis_set_failure(self, repository, sample_record):
        """Test update operation when Redis set fails."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = sample_record.model_dump_json()
        mock_redis.set.return_value = False
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            with pytest.raises(RuntimeError, match="Failed to update record"):
                await repository.update("+1234567890", "456 New St")
    
    @pytest.mark.asyncio
    async def test_delete_existing_record(self, repository):
        """Test deleting an existing phone address record."""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 1  # One record deleted
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            result = await repository.delete("+1234567890")
            
            assert result is True
            mock_redis.delete.assert_called_once_with("phone:+1234567890")
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_record(self, repository):
        """Test deleting a non-existent phone address record."""
        mock_redis = AsyncMock()
        mock_redis.delete.return_value = 0  # No records deleted
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            result = await repository.delete("+1234567890")
            
            assert result is False
            mock_redis.delete.assert_called_once_with("phone:+1234567890")
    
    @pytest.mark.asyncio
    async def test_exists_record_found(self, repository):
        """Test checking existence of an existing record."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 1
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            result = await repository.exists("+1234567890")
            
            assert result is True
            mock_redis.exists.assert_called_once_with("phone:+1234567890")
    
    @pytest.mark.asyncio
    async def test_exists_record_not_found(self, repository):
        """Test checking existence of a non-existent record."""
        mock_redis = AsyncMock()
        mock_redis.exists.return_value = 0
        
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            result = await repository.exists("+1234567890")
            
            assert result is False
            mock_redis.exists.assert_called_once_with("phone:+1234567890")
    
    @pytest.mark.asyncio
    async def test_redis_error_handling(self, repository):
        """Test handling of various Redis errors."""
        mock_redis = AsyncMock()
        
        # Test ConnectionError
        mock_redis.get.side_effect = ConnectionError("Connection lost")
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            with pytest.raises(ConnectionError, match="Redis service unavailable"):
                await repository.get("+1234567890")
        
        # Test TimeoutError
        mock_redis.get.side_effect = TimeoutError("Operation timed out")
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            with pytest.raises(ConnectionError, match="Redis service unavailable"):
                await repository.get("+1234567890")
        
        # Test RedisError
        mock_redis.get.side_effect = RedisError("Redis internal error")
        with patch.object(repository, '_get_redis_client', return_value=mock_redis):
            with pytest.raises(RedisError):
                await repository.get("+1234567890")
    
    def test_make_key(self, repository):
        """Test Redis key generation."""
        key = repository._make_key("+1234567890")
        assert key == "phone:+1234567890"
        
        key = repository._make_key("+44123456789")
        assert key == "phone:+44123456789"