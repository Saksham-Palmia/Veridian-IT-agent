"""security package"""
"""Security, authentication, and identity provider abstractions."""

from app.security.identity_service import (
    DemoIdentityProvider,
    GoogleIdentityProvider,
    IdentityProvider,
    MicrosoftIdentityProvider,
    SlackIdentityProvider,
    create_access_token,
    decode_token,
    get_current_employee,
)

__all__ = [
    "DemoIdentityProvider",
    "GoogleIdentityProvider",
    "IdentityProvider",
    "MicrosoftIdentityProvider",
    "SlackIdentityProvider",
    "create_access_token",
    "decode_token",
    "get_current_employee",
]
