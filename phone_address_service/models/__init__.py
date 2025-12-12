"""Data models for the phone address service."""

from .schemas import (
    PhoneAddressRecord,
    CreatePhoneAddressRequest,
    UpdateAddressRequest,
    PhoneAddressResponse,
    ErrorResponse,
    HealthCheckResponse,
)

__all__ = [
    "PhoneAddressRecord",
    "CreatePhoneAddressRequest", 
    "UpdateAddressRequest",
    "PhoneAddressResponse",
    "ErrorResponse",
    "HealthCheckResponse",
]