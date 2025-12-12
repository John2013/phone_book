"""Property-based tests for logging functionality."""

import pytest
import logging
import json
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from hypothesis import given, strategies as st
from io import StringIO

from phone_address_service.models.schemas import (
    PhoneAddressRecord, 
    CreatePhoneAddressRequest, 
    UpdateAddressRequest
)
from phone_address_service.services.phone_address_service import PhoneAddressService
from phone_address_service.repositories.base import PhoneAddressRepository
from phone_address_service.config.logging import LoggingService, set_correlation_id


# Generator for valid phone numbers in E.164 format
def phone_number_strategy():
    """Generate valid phone numbers in E.164 format."""
    return st.builds(
        lambda first_digit, rest_digits: f"+{first_digit}{''.join(map(str, rest_digits))}",
        first_digit=st.integers(min_value=1, max_value=9),
        rest_digits=st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=1,
            max_size=14
        )
    )


# Generator for valid addresses
def address_strategy():
    """Generate valid addresses."""
    return st.text(
        min_size=1, 
        max_size=500,
        alphabet=st.characters(blacklist_categories=('Cc', 'Cs'))
    ).filter(lambda x: x.strip() and len(x.strip()) <= 500)


# Generator for CRUD operations
crud_operations_strategy = st.sampled_from(['create', 'read', 'update', 'delete'])


class LogCapture:
    """Helper class to capture log output."""
    
    def __init__(self):
        self.records = []
        self.handler = None
        
    def __enter__(self):
        # Create a custom handler that captures log records
        self.handler = logging.Handler()
        self.handler.emit = lambda record: self.records.append(record)
        
        # Add handler to root logger
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.DEBUG)
        
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handler:
            logging.getLogger().removeHandler(self.handler)
    
    def get_log_messages(self):
        """Get all captured log messages."""
        return [record.getMessage() for record in self.records]
    
    def get_log_records(self):
        """Get all captured log records."""
        return self.records


@pytest.mark.asyncio
@given(crud_operations_strategy, phone_number_strategy(), st.booleans())
async def test_operation_logging_property(operation, phone, success):
    """
    **Feature: phone-address-service, Property 12: Operation logging**
    **Validates: Requirements 7.1**
    
    For any CRUD operation performed, the system should log the operation type, 
    phone number, and result.
    """
    # Set up correlation ID for consistent logging
    set_correlation_id("test-correlation-id")
    
    with LogCapture() as log_capture:
        # Create mock repository
        mock_repo = AsyncMock(spec=PhoneAddressRepository)
        
        # Configure mock based on operation and success
        if operation == 'create':
            if success:
                record = PhoneAddressRecord(
                    phone=phone,
                    address="Test Address",
                    created_at=pytest.approx_datetime(),
                    updated_at=pytest.approx_datetime()
                )
                mock_repo.create.return_value = record
            else:
                mock_repo.create.side_effect = ValueError("Phone already exists")
        elif operation == 'read':
            if success:
                record = PhoneAddressRecord(
                    phone=phone,
                    address="Test Address",
                    created_at=pytest.approx_datetime(),
                    updated_at=pytest.approx_datetime()
                )
                mock_repo.get.return_value = record
            else:
                mock_repo.get.return_value = None
        elif operation == 'update':
            if success:
                record = PhoneAddressRecord(
                    phone=phone,
                    address="Updated Address",
                    created_at=pytest.approx_datetime(),
                    updated_at=pytest.approx_datetime()
                )
                mock_repo.update.return_value = record
            else:
                mock_repo.update.return_value = None
        elif operation == 'delete':
            mock_repo.delete.return_value = success
        
        # Create service
        service = PhoneAddressService(mock_repo)
        
        # Execute operation
        try:
            if operation == 'create':
                request = CreatePhoneAddressRequest(phone=phone, address="Test Address")
                await service.create_record(request)
            elif operation == 'read':
                await service.get_address(phone)
            elif operation == 'update':
                request = UpdateAddressRequest(address="Updated Address")
                await service.update_address(phone, request)
            elif operation == 'delete':
                await service.delete_record(phone)
        except ValueError:
            # Expected for failed create operations
            pass
        
        # Verify logging occurred
        log_records = log_capture.get_log_records()
        
        # Should have at least one log record
        assert len(log_records) > 0
        
        # Find CRUD operation log
        crud_logs = [
            record for record in log_records 
            if hasattr(record, 'operation') and record.operation == operation
        ]
        
        # Should have at least one CRUD operation log
        assert len(crud_logs) > 0
        
        # Verify the log contains required information
        crud_log = crud_logs[0]
        
        # Should contain phone number
        assert hasattr(crud_log, 'phone')
        assert crud_log.phone == phone
        
        # Should contain operation type
        assert hasattr(crud_log, 'operation')
        assert crud_log.operation == operation
        
        # Log message should contain operation information
        message = crud_log.getMessage()
        assert operation in message.lower() or "operation" in message.lower()


@pytest.mark.asyncio
@given(phone_number_strategy(), st.text(min_size=1, max_size=100))
async def test_error_logging_property(phone, error_message):
    """
    **Feature: phone-address-service, Property 13: Error logging**
    **Validates: Requirements 7.2**
    
    For any error that occurs, the system should log error details 
    with appropriate log level.
    """
    # Set up correlation ID for consistent logging
    set_correlation_id("test-correlation-id")
    
    with LogCapture() as log_capture:
        # Create mock repository that raises an exception
        mock_repo = AsyncMock(spec=PhoneAddressRepository)
        mock_repo.get.side_effect = Exception(error_message)
        
        # Create service
        service = PhoneAddressService(mock_repo)
        
        # Execute operation that will cause an error
        with pytest.raises(Exception):
            await service.get_address(phone)
        
        # Verify error logging occurred
        log_records = log_capture.get_log_records()
        
        # Should have at least one log record
        assert len(log_records) > 0
        
        # Find error logs (ERROR level)
        error_logs = [
            record for record in log_records 
            if record.levelno >= logging.ERROR
        ]
        
        # Should have at least one error log
        assert len(error_logs) > 0
        
        # Verify the error log contains required information
        error_log = error_logs[0]
        
        # Should contain phone number
        assert hasattr(error_log, 'phone')
        assert error_log.phone == phone
        
        # Should contain operation information
        assert hasattr(error_log, 'operation')
        
        # Should contain error information
        assert hasattr(error_log, 'error')
        assert error_message in error_log.error
        
        # Should contain error type
        assert hasattr(error_log, 'error_type')
        assert error_log.error_type == 'Exception'
        
        # Log message should indicate an error occurred
        message = error_log.getMessage()
        assert "error" in message.lower() or "failed" in message.lower()


@pytest.fixture
def approx_datetime():
    """Fixture to create approximate datetime for testing."""
    from datetime import datetime
    return datetime.utcnow()


# Add the fixture to pytest namespace
pytest.approx_datetime = lambda: __import__('datetime').datetime.utcnow()