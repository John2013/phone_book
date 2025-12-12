"""Pydantic models for phone address service."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
import re


class PhoneAddressRecord(BaseModel):
    """Core model for phone-address records."""
    
    phone: str = Field(
        ..., 
        description="Phone number in international format",
        min_length=1,
        max_length=20
    )
    address: str = Field(
        ..., 
        description="Address associated with the phone number",
        min_length=1, 
        max_length=500
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when record was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when record was last updated"
    )

    @field_validator('phone')
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Validate phone number format using E.164 standard."""
        # Remove any whitespace
        phone = v.strip()
        
        # E.164 format: + followed by 1-15 digits
        pattern = r'^\+?[1-9]\d{1,14}$'
        
        if not re.match(pattern, phone):
            raise ValueError(
                'Phone number must be in E.164 format: + followed by 1-15 digits, '
                'starting with a non-zero digit'
            )
        
        return phone

    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate address is not empty or just whitespace."""
        address = v.strip()
        if not address:
            raise ValueError('Address cannot be empty or contain only whitespace')
        return address


class CreatePhoneAddressRequest(BaseModel):
    """Request model for creating new phone-address records."""
    
    phone: str = Field(
        ..., 
        description="Phone number in international format",
        min_length=1,
        max_length=20
    )
    address: str = Field(
        ..., 
        description="Address to associate with the phone number",
        min_length=1, 
        max_length=500
    )

    @field_validator('phone')
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Validate phone number format using E.164 standard."""
        # Remove any whitespace
        phone = v.strip()
        
        # E.164 format: + followed by 1-15 digits
        pattern = r'^\+?[1-9]\d{1,14}$'
        
        if not re.match(pattern, phone):
            raise ValueError(
                'Phone number must be in E.164 format: + followed by 1-15 digits, '
                'starting with a non-zero digit'
            )
        
        return phone

    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate address is not empty or just whitespace."""
        address = v.strip()
        if not address:
            raise ValueError('Address cannot be empty or contain only whitespace')
        return address


class UpdateAddressRequest(BaseModel):
    """Request model for updating address of existing phone records."""
    
    address: str = Field(
        ..., 
        description="New address to associate with the phone number",
        min_length=1, 
        max_length=500
    )

    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        """Validate address is not empty or just whitespace."""
        address = v.strip()
        if not address:
            raise ValueError('Address cannot be empty or contain only whitespace')
        return address


class PhoneAddressResponse(BaseModel):
    """Standard response model for phone-address data."""
    
    phone: str
    address: str
    created_at: datetime
    updated_at: datetime


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(..., description="Service status")
    redis_connected: bool = Field(..., description="Redis connection status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)