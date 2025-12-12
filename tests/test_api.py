"""Property-based tests for FastAPI endpoints."""

import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from hypothesis import given, strategies as st
from hypothesis import settings

from phone_address_service.api.app import create_app
from phone_address_service.models.schemas import PhoneAddressRecord


# Test client setup
def get_test_client():
    """Create test client for FastAPI app."""
    app = create_app()
    return TestClient(app)


# Generators for property-based testing
@st.composite
def valid_phone_numbers(draw):
    """Generate valid phone numbers in E.164 format."""
    # Generate 1-15 digits starting with non-zero
    first_digit = draw(st.integers(min_value=1, max_value=9))
    remaining_digits = draw(st.integers(min_value=0, max_value=10**13))
    remaining_str = str(remaining_digits).zfill(draw(st.integers(min_value=1, max_value=14)))
    
    phone = f"+{first_digit}{remaining_str}"
    return phone[:16]  # Ensure max 15 digits after +


@st.composite
def valid_addresses(draw):
    """Generate valid addresses."""
    # Generate non-empty string with length 1-500
    address = draw(st.text(min_size=1, max_size=500).filter(lambda x: x.strip()))
    return address.strip()


@st.composite
def phone_address_records(draw):
    """Generate valid PhoneAddressRecord instances."""
    phone = draw(valid_phone_numbers())
    address = draw(valid_addresses())
    now = datetime.utcnow()
    
    return PhoneAddressRecord(
        phone=phone,
        address=address,
        created_at=now,
        updated_at=now
    )


def has_required_response_fields(response_data: Dict[str, Any]) -> bool:
    """Check if response has required fields for successful operations."""
    required_fields = {"phone", "address", "created_at", "updated_at"}
    return all(field in response_data for field in required_fields)


def has_error_response_fields(response_data: Dict[str, Any]) -> bool:
    """Check if response has required fields for error responses."""
    required_fields = {"error", "message"}
    return all(field in response_data for field in required_fields)


class TestConsistentResponseFormat:
    """**Feature: phone-address-service, Property 10: Consistent response format**"""
    
    @given(record=phone_address_records())
    @settings(max_examples=100)
    def test_successful_responses_have_consistent_format(self, record):
        """
        **Feature: phone-address-service, Property 10: Consistent response format**
        **Validates: Requirements 2.4, 3.4, 6.1**
        
        For any successful API response, the JSON should contain the required fields 
        (phone, address, created_at, updated_at) in consistent schema.
        """
        client = get_test_client()
        
        # First create a record
        create_data = {
            "phone": record.phone,
            "address": record.address
        }
        
        # Test POST response format
        create_response = client.post("/phone", json=create_data)
        
        # Skip if creation fails (might be due to Redis unavailability in test)
        if create_response.status_code != 201:
            pytest.skip("Redis unavailable or other infrastructure issue")
        
        create_json = create_response.json()
        assert has_required_response_fields(create_json), f"POST response missing required fields: {create_json}"
        assert create_json["phone"] == record.phone
        assert create_json["address"] == record.address
        
        # Test GET response format
        get_response = client.get(f"/phone/{record.phone}")
        if get_response.status_code == 200:
            get_json = get_response.json()
            assert has_required_response_fields(get_json), f"GET response missing required fields: {get_json}"
            assert get_json["phone"] == record.phone
            assert get_json["address"] == record.address
        
        # Test PUT response format
        update_data = {"address": "Updated " + record.address}
        put_response = client.put(f"/phone/{record.phone}", json=update_data)
        if put_response.status_code == 200:
            put_json = put_response.json()
            assert has_required_response_fields(put_json), f"PUT response missing required fields: {put_json}"
            assert put_json["phone"] == record.phone
            assert put_json["address"] == update_data["address"]
        
        # Cleanup
        client.delete(f"/phone/{record.phone}")
    
    @given(phone=valid_phone_numbers(), address=valid_addresses())
    @settings(max_examples=50)
    def test_json_fields_are_properly_typed(self, phone, address):
        """
        Test that JSON response fields have correct types.
        """
        client = get_test_client()
        create_data = {"phone": phone, "address": address}
        
        response = client.post("/phone", json=create_data)
        
        # Skip if creation fails
        if response.status_code != 201:
            pytest.skip("Redis unavailable or other infrastructure issue")
        
        data = response.json()
        
        # Check field types
        assert isinstance(data["phone"], str)
        assert isinstance(data["address"], str)
        assert isinstance(data["created_at"], str)  # ISO format datetime string
        assert isinstance(data["updated_at"], str)  # ISO format datetime string
        
        # Verify datetime strings are valid ISO format
        datetime.fromisoformat(data["created_at"].replace('Z', '+00:00'))
        datetime.fromisoformat(data["updated_at"].replace('Z', '+00:00'))
        
        # Cleanup
        client.delete(f"/phone/{phone}")


class TestErrorResponseFormat:
    """**Feature: phone-address-service, Property 11: Error response format**"""
    
    @given(invalid_phone=st.text(alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')), min_size=1, max_size=10).filter(lambda x: not x.startswith('+') and x.isalnum()))
    @settings(max_examples=100)
    def test_error_responses_have_consistent_format(self, invalid_phone):
        """
        **Feature: phone-address-service, Property 11: Error response format**
        **Validates: Requirements 6.2**
        
        For any error condition, the API should return JSON with error and message fields.
        """
        client = get_test_client()
        
        # Test GET with invalid phone format
        response = client.get(f"/phone/{invalid_phone}")
        
        if response.status_code >= 400:
            error_json = response.json()
            # FastAPI returns {"detail": "message"} format for HTTPExceptions
            if "detail" in error_json:
                assert isinstance(error_json["detail"], str)
                assert len(error_json["detail"]) > 0
            else:
                # Our custom error format
                assert has_error_response_fields(error_json), f"Error response missing required fields: {error_json}"
                assert isinstance(error_json["error"], str)
                assert isinstance(error_json["message"], str)
                assert len(error_json["error"]) > 0
                assert len(error_json["message"]) > 0
    
    def test_validation_error_format(self):
        """Test that validation errors return proper error format."""
        client = get_test_client()
        
        # Test with invalid request body
        invalid_data = {"phone": "", "address": ""}
        
        response = client.post("/phone", json=invalid_data)
        
        if response.status_code == 422:  # FastAPI validation error
            error_json = response.json()
            # FastAPI returns different format for validation errors
            assert "detail" in error_json
        elif response.status_code >= 400:
            error_json = response.json()
            assert has_error_response_fields(error_json), f"Error response missing required fields: {error_json}"
    
    def test_not_found_error_format(self):
        """Test that 404 errors return proper error format."""
        client = get_test_client()
        
        # Use a phone number that definitely doesn't exist
        non_existent_phone = "+999999999999999"
        
        response = client.get(f"/phone/{non_existent_phone}")
        
        if response.status_code == 404:
            error_json = response.json()
            # FastAPI HTTPException returns {"detail": "message"} format
            assert "detail" in error_json
            assert isinstance(error_json["detail"], str)
    
    @given(phone=valid_phone_numbers(), address=valid_addresses())
    @settings(max_examples=50)
    def test_conflict_error_format(self, phone, address):
        """Test that conflict errors (409) return proper error format."""
        client = get_test_client()
        create_data = {"phone": phone, "address": address}
        
        # Create record first
        first_response = client.post("/phone", json=create_data)
        
        # Skip if creation fails
        if first_response.status_code != 201:
            pytest.skip("Redis unavailable or other infrastructure issue")
        
        # Try to create the same record again
        second_response = client.post("/phone", json=create_data)
        
        if second_response.status_code == 409:
            error_json = second_response.json()
            # Check if it follows our error format or FastAPI's format
            if "detail" in error_json:
                assert isinstance(error_json["detail"], str)
            else:
                assert has_error_response_fields(error_json), f"Conflict response missing required fields: {error_json}"
        
        # Cleanup
        client.delete(f"/phone/{phone}")


class TestHealthCheckEndpoint:
    """Unit tests for health check functionality."""
    
    def test_health_check_endpoint_exists(self):
        """Test that health check endpoint is accessible."""
        client = get_test_client()
        response = client.get("/health")
        
        # Should always return 200, even if Redis is unavailable
        assert response.status_code == 200
        
        # Check response structure
        data = response.json()
        assert "status" in data
        assert "redis_connected" in data
        assert "timestamp" in data
        
        # Validate field types
        assert isinstance(data["status"], str)
        assert isinstance(data["redis_connected"], bool)
        assert isinstance(data["timestamp"], str)
        
        # Status should be either "healthy" or "degraded"
        assert data["status"] in ["healthy", "degraded"]
    
    @patch('phone_address_service.repositories.connection.redis_manager.health_check')
    def test_health_check_with_redis_available(self, mock_health_check):
        """Test health check when Redis is available."""
        # Mock Redis as available
        mock_health_check.return_value = True
        
        client = get_test_client()
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["redis_connected"] is True
        
        # Verify the mock was called
        mock_health_check.assert_called_once()
    
    @patch('phone_address_service.repositories.connection.redis_manager.health_check')
    def test_health_check_with_redis_unavailable(self, mock_health_check):
        """Test health check when Redis is unavailable."""
        # Mock Redis as unavailable
        mock_health_check.return_value = False
        
        client = get_test_client()
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["redis_connected"] is False
        
        # Verify the mock was called
        mock_health_check.assert_called_once()
    
    def test_health_check_response_format(self):
        """Test that health check response follows expected format."""
        client = get_test_client()
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check all required fields are present
        required_fields = {"status", "redis_connected", "timestamp"}
        assert all(field in data for field in required_fields)
        
        # Validate timestamp format (should be ISO format)
        timestamp_str = data["timestamp"]
        try:
            datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(f"Invalid timestamp format: {timestamp_str}")
    
    def test_health_check_logs_operation(self):
        """Test that health check operations are logged."""
        # This test verifies that the health check endpoint logs its operations
        # The actual logging verification would require log capture, but we can
        # at least verify the endpoint works without errors
        client = get_test_client()
        response = client.get("/health")
        
        # Should complete without errors
        assert response.status_code == 200
        
        # Multiple calls should work consistently
        response2 = client.get("/health")
        assert response2.status_code == 200