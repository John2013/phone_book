"""Test basic project structure and imports."""

import pytest


def test_package_version():
    """Test that package version is accessible."""
    from phone_address_service import __version__
    assert __version__ == "0.1.0"


def test_basic_imports():
    """Test that basic modules can be imported."""
    # Test that modules exist and can be imported
    import phone_address_service.models
    import phone_address_service.services
    import phone_address_service.repositories
    import phone_address_service.api
    import phone_address_service.config
    
    # Basic assertion to ensure imports worked
    assert phone_address_service.models is not None