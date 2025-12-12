"""Property-based tests for phone address service models."""

import json
from datetime import datetime
from hypothesis import given, strategies as st
from phone_address_service.models import PhoneAddressRecord


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
    return st.text(min_size=1, max_size=500).filter(lambda x: x.strip())


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


@given(phone_address_record_strategy())
def test_json_serialization_round_trip(record):
    """
    **Feature: phone-address-service, Property 9: JSON serialization round-trip**
    **Validates: Requirements 6.3, 6.4**
    
    For any valid PhoneAddressRecord, serializing to JSON and deserializing back 
    should produce an equivalent record with proper UTF-8 encoding.
    """
    # Serialize to JSON
    json_str = record.model_dump_json()
    
    # Verify it's valid JSON and properly encoded
    parsed_json = json.loads(json_str)
    assert isinstance(parsed_json, dict)
    
    # Deserialize back to model
    deserialized_record = PhoneAddressRecord.model_validate(parsed_json)
    
    # Verify equivalence
    assert deserialized_record.phone == record.phone
    assert deserialized_record.address == record.address
    assert deserialized_record.created_at == record.created_at
    assert deserialized_record.updated_at == record.updated_at
    
    # Verify UTF-8 encoding works for international characters
    # The JSON should be properly encoded and decodable
    json_bytes = json_str.encode('utf-8')
    decoded_json_str = json_bytes.decode('utf-8')
    assert decoded_json_str == json_str


# Generator for invalid phone numbers
def invalid_phone_number_strategy():
    """Generate invalid phone numbers that should fail validation."""
    return st.one_of([
        # Empty string
        st.just(""),
        # Only whitespace
        st.text().filter(lambda x: x.isspace() and x),
        # Starting with 0
        st.builds(lambda digits: f"+0{''.join(map(str, digits))}", 
                 digits=st.lists(st.integers(0, 9), min_size=1, max_size=14)),
        # No + sign and starting with 0
        st.builds(lambda digits: f"0{''.join(map(str, digits))}", 
                 digits=st.lists(st.integers(0, 9), min_size=1, max_size=14)),
        # Too long (more than 15 digits)
        st.builds(lambda first, rest: f"+{first}{''.join(map(str, rest))}", 
                 first=st.integers(1, 9),
                 rest=st.lists(st.integers(0, 9), min_size=15, max_size=20)),
        # Contains letters
        st.text().filter(lambda x: any(c.isalpha() for c in x) and x),
        # Contains special characters (except +)
        st.builds(lambda: "+123-456-7890"),
        st.builds(lambda: "+123 456 7890"),
        st.builds(lambda: "+123.456.7890"),
        # Multiple + signs
        st.builds(lambda: "++1234567890"),
        # + not at the beginning
        st.builds(lambda: "1+234567890"),
    ])


@given(invalid_phone_number_strategy())
def test_phone_number_format_validation(invalid_phone):
    """
    **Feature: phone-address-service, Property 2: Phone number format validation**
    **Validates: Requirements 1.3, 4.3**
    
    For any invalid phone number format, all API endpoints should return HTTP status 400 
    with error description. This tests the validation at the model level.
    """
    from pydantic import ValidationError
    from phone_address_service.models import CreatePhoneAddressRequest, PhoneAddressRecord
    
    # Test validation in CreatePhoneAddressRequest
    try:
        CreatePhoneAddressRequest(phone=invalid_phone, address="123 Main St")
        assert False, f"Expected validation error for phone: {invalid_phone!r}"
    except ValidationError as e:
        # Should get a validation error
        assert "phone" in str(e).lower() or "value_error" in str(e)
    
    # Test validation in PhoneAddressRecord
    try:
        PhoneAddressRecord(phone=invalid_phone, address="123 Main St")
        assert False, f"Expected validation error for phone: {invalid_phone!r}"
    except ValidationError as e:
        # Should get a validation error
        assert "phone" in str(e).lower() or "value_error" in str(e)


# Generator for invalid request data
def invalid_request_data_strategy():
    """Generate invalid request data that should fail validation."""
    return st.one_of([
        # Missing phone field
        st.builds(dict, address=address_strategy()),
        # Missing address field  
        st.builds(dict, phone=phone_number_strategy()),
        # Empty phone
        st.builds(dict, phone=st.just(""), address=address_strategy()),
        # Empty address
        st.builds(dict, phone=phone_number_strategy(), address=st.just("")),
        # Whitespace-only address
        st.builds(dict, phone=phone_number_strategy(), address=st.just("   ")),
        # Address too long
        st.builds(dict, phone=phone_number_strategy(), address=st.text(min_size=501, max_size=600)),
        # Invalid phone format
        st.builds(dict, phone=invalid_phone_number_strategy(), address=address_strategy()),
        # Both fields invalid
        st.builds(dict, phone=st.just(""), address=st.just("")),
    ])


@given(invalid_request_data_strategy())
def test_input_validation_for_requests(invalid_data):
    """
    **Feature: phone-address-service, Property 6: Input validation for requests**
    **Validates: Requirements 2.3, 3.3**
    
    For any request with invalid or missing required fields, the API should return 
    HTTP status 400 with validation error details. This tests validation at the model level.
    """
    from pydantic import ValidationError
    from phone_address_service.models import CreatePhoneAddressRequest, UpdateAddressRequest
    
    # Test CreatePhoneAddressRequest validation
    try:
        CreatePhoneAddressRequest(**invalid_data)
        assert False, f"Expected validation error for data: {invalid_data!r}"
    except (ValidationError, TypeError) as e:
        # Should get a validation error or TypeError for missing required fields
        assert True  # Expected behavior
    
    # Test UpdateAddressRequest validation if address field is present
    if "address" in invalid_data:
        try:
            UpdateAddressRequest(address=invalid_data["address"])
            # If address is valid, this should pass
            if invalid_data["address"] and invalid_data["address"].strip() and len(invalid_data["address"]) <= 500:
                assert True  # Valid address should pass
            else:
                assert False, f"Expected validation error for address: {invalid_data['address']!r}"
        except ValidationError as e:
            # Should get a validation error for invalid address
            assert "address" in str(e).lower() or "value_error" in str(e)