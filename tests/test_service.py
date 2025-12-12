"""Property-based tests for phone address service layer."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, Mock
from hypothesis import given, strategies as st, assume
from redis.exceptions import ConnectionError

from phone_address_service.models.schemas import (
    PhoneAddressRecord, 
    CreatePhoneAddressRequest, 
    UpdateAddressRequest
)
from phone_address_service.services.phone_address_service import PhoneAddressService
from phone_address_service.repositories.base import PhoneAddressRepository


# Generator for valid phone numbers in E.164 format
def phone_number_strategy():
    """Generate valid phone numbers in E.164 format."""
    # Generate 2-15 digits total, starting with non-zero
    return st.builds(
        lambda first_digit, rest_digits: f"+{first_digit}{''.join(map(str, rest_digits))}",
        first_digit=st.integers(min_value=1, max_value=9),
        rest_digits=st.lists(
            st.integers(min_value=0, max_value=9),
            min_size=1,  # At least 1 more digit after the first
            max_size=14
        )
    )


# Generator for valid addresses
def address_strategy():
    """Generate valid addresses."""
    return st.text(
        min_size=1, 
        max_size=500,
        alphabet=st.characters(blacklist_categories=('Cc', 'Cs'))  # Exclude control characters
    ).filter(lambda x: x.strip() and len(x.strip()) <= 500)


# Generator for valid PhoneAddressRecord instances
def phone_address_record_strategy():
    """Generate valid PhoneAddressRecord instances."""
    return st.builds(
        PhoneAddressRecord,
        phone=phone_number_strategy(),
        address=address_strategy(),
        created_at=st.datetimes(),
        updated_at=st.datetimes()
    )


@pytest.mark.asyncio
@given(phone_address_record_strategy())
async def test_successful_retrieval_returns_correct_data(record):
    """
    **Feature: phone-address-service, Property 1: Successful retrieval returns correct data**
    **Validates: Requirements 1.1**
    
    For any valid phone number with an associated address in the system, 
    requesting that phone number should return the correct address with HTTP status 200.
    """
    # Create mock repository
    mock_repo = AsyncMock(spec=PhoneAddressRepository)
    mock_repo.get.return_value = record
    
    # Create service
    service = PhoneAddressService(mock_repo)
    
    # Test retrieval
    result = await service.get_address(record.phone)
    
    # Verify correct data is returned
    assert result is not None
    assert result.phone == record.phone
    assert result.address == record.address
    assert result.created_at == record.created_at
    assert result.updated_at == record.updated_at
    
    # Verify repository was called correctly
    mock_repo.get.assert_called_once_with(record.phone)


@pytest.mark.asyncio
@given(phone_number_strategy())
async def test_non_existent_record_handling_get(phone):
    """
    **Feature: phone-address-service, Property 3: Non-existent record handling**
    **Validates: Requirements 1.2, 3.2, 4.2**
    
    For any phone number that does not exist in the system, 
    GET operations should return None (which translates to HTTP status 404).
    """
    # Create mock repository that returns None (not found)
    mock_repo = AsyncMock(spec=PhoneAddressRepository)
    mock_repo.get.return_value = None
    
    # Create service
    service = PhoneAddressService(mock_repo)
    
    # Test retrieval of non-existent record
    result = await service.get_address(phone)
    
    # Should return None for non-existent records
    assert result is None
    
    # Verify repository was called correctly
    mock_repo.get.assert_called_once_with(phone)


@pytest.mark.asyncio
@given(phone_number_strategy())
async def test_non_existent_record_handling_update(phone):
    """
    **Feature: phone-address-service, Property 3: Non-existent record handling**
    **Validates: Requirements 1.2, 3.2, 4.2**
    
    For any phone number that does not exist in the system, 
    PUT operations should return None (which translates to HTTP status 404).
    """
    # Create mock repository that returns None (not found)
    mock_repo = AsyncMock(spec=PhoneAddressRepository)
    mock_repo.update.return_value = None
    
    # Create service
    service = PhoneAddressService(mock_repo)
    
    # Create update request
    update_request = UpdateAddressRequest(address="New Address")
    
    # Test update of non-existent record
    result = await service.update_address(phone, update_request)
    
    # Should return None for non-existent records
    assert result is None
    
    # Verify repository was called correctly
    mock_repo.update.assert_called_once_with(phone, "New Address")


@pytest.mark.asyncio
@given(phone_number_strategy())
async def test_non_existent_record_handling_delete(phone):
    """
    **Feature: phone-address-service, Property 3: Non-existent record handling**
    **Validates: Requirements 1.2, 3.2, 4.2**
    
    For any phone number that does not exist in the system, 
    DELETE operations should return False (which translates to HTTP status 404).
    """
    # Create mock repository that returns False (not found)
    mock_repo = AsyncMock(spec=PhoneAddressRepository)
    mock_repo.delete.return_value = False
    
    # Create service
    service = PhoneAddressService(mock_repo)
    
    # Test deletion of non-existent record
    result = await service.delete_record(phone)
    
    # Should return False for non-existent records
    assert result is False
    
    # Verify repository was called correctly
    mock_repo.delete.assert_called_once_with(phone)


@pytest.mark.asyncio
@given(phone_number_strategy(), address_strategy())
async def test_successful_record_creation(phone, address):
    """
    **Feature: phone-address-service, Property 4: Successful record creation**
    **Validates: Requirements 2.1**
    
    For any valid phone and address data for a new phone number, 
    creating the record should store it in Redis and return HTTP status 201.
    """
    # Create the expected record that would be created
    expected_record = PhoneAddressRecord(
        phone=phone,
        address=address,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create mock repository
    mock_repo = AsyncMock(spec=PhoneAddressRepository)
    mock_repo.create.return_value = expected_record
    
    # Create service
    service = PhoneAddressService(mock_repo)
    
    # Create request
    create_request = CreatePhoneAddressRequest(phone=phone, address=address)
    
    # Test record creation
    result = await service.create_record(create_request)
    
    # Verify correct record is returned
    assert result is not None
    assert result.phone == phone
    assert result.address == address.strip()  # Address gets stripped during validation
    assert isinstance(result.created_at, datetime)
    assert isinstance(result.updated_at, datetime)
    
    # Verify repository was called correctly
    mock_repo.create.assert_called_once()
    
    # Verify the record passed to repository has correct data
    call_args = mock_repo.create.call_args[0][0]
    assert call_args.phone == phone
    assert call_args.address == address.strip()  # Address gets stripped during validation
    assert isinstance(call_args.created_at, datetime)
    assert isinstance(call_args.updated_at, datetime)

@pytest.mark.asyncio
@given(phone_number_strategy(), address_strategy())
async def test_duplicate_prevention(phone, address):
    """
    **Feature: phone-address-service, Property 5: Duplicate prevention**
    **Validates: Requirements 2.2**
    
    For any phone number that already exists in the system, 
    attempting to create a new record should return HTTP status 409.
    """
    # Create mock repository that raises ValueError for duplicate
    mock_repo = AsyncMock(spec=PhoneAddressRepository)
    mock_repo.create.side_effect = ValueError(f"Phone number {phone} already exists")
    
    # Create service
    service = PhoneAddressService(mock_repo)
    
    # Create request
    create_request = CreatePhoneAddressRequest(phone=phone, address=address)
    
    # Test duplicate creation - should raise ValueError
    with pytest.raises(ValueError) as exc_info:
        await service.create_record(create_request)
    
    # Verify the error message indicates duplicate
    assert "already exists" in str(exc_info.value)
    
    # Verify repository was called correctly
    mock_repo.create.assert_called_once()
    
    # Verify the record passed to repository has correct data
    call_args = mock_repo.create.call_args[0][0]
    assert call_args.phone == phone
    assert call_args.address == address.strip()  # Address gets stripped during validation

@pytest.mark.asyncio
@given(phone_number_strategy(), address_strategy(), address_strategy())
async def test_successful_record_update(phone, old_address, new_address):
    """
    **Feature: phone-address-service, Property 7: Successful record update**
    **Validates: Requirements 3.1**
    
    For any existing phone number and valid new address, 
    updating the record should modify the stored data and return HTTP status 200.
    """
    # Assume addresses are different to make the test meaningful
    assume(old_address != new_address)
    
    # Create the updated record that would be returned
    updated_record = PhoneAddressRecord(
        phone=phone,
        address=new_address,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    # Create mock repository
    mock_repo = AsyncMock(spec=PhoneAddressRepository)
    mock_repo.update.return_value = updated_record
    
    # Create service
    service = PhoneAddressService(mock_repo)
    
    # Create update request
    update_request = UpdateAddressRequest(address=new_address)
    
    # Test record update
    result = await service.update_address(phone, update_request)
    
    # Verify correct updated record is returned
    assert result is not None
    assert result.phone == phone
    assert result.address == new_address.strip()  # Address gets stripped during validation
    assert isinstance(result.created_at, datetime)
    assert isinstance(result.updated_at, datetime)
    
    # Verify repository was called correctly
    mock_repo.update.assert_called_once_with(phone, new_address.strip())
@pytest.mark.asyncio
@given(phone_number_strategy())
async def test_successful_record_deletion(phone):
    """
    **Feature: phone-address-service, Property 8: Successful record deletion**
    **Validates: Requirements 4.1**
    
    For any existing phone number, deleting the record should remove it 
    from Redis and return HTTP status 204 (represented by True return value).
    """
    # Create mock repository that returns True (successful deletion)
    mock_repo = AsyncMock(spec=PhoneAddressRepository)
    mock_repo.delete.return_value = True
    
    # Create service
    service = PhoneAddressService(mock_repo)
    
    # Test record deletion
    result = await service.delete_record(phone)
    
    # Verify successful deletion
    assert result is True
    
    # Verify repository was called correctly
    mock_repo.delete.assert_called_once_with(phone)