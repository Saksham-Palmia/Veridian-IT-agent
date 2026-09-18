"""Identity / Authentication service.

Provides an abstraction layer over identity providers.
DemoIdentityProvider is the default for local development.
Google/Microsoft/Slack stubs are available for future real OAuth integration.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.exceptions import AuthenticationError, NotFoundError
from app.models.employee import Employee
from app.repositories.repositories import EmployeeRepository

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Abstract identity provider ───────────────────────────────────────────────


class IdentityProvider(ABC):
    @abstractmethod
    def authenticate(self, credential: str) -> dict:
        """Authenticate and return identity dict with employee_id, name, email."""
        ...


# ─── Demo provider (local development — no external OAuth needed) ─────────────


class DemoIdentityProvider(IdentityProvider):
    """Allows local users to sign in with email or employee ID."""

    def __init__(self, db: Session):
        self.repo = EmployeeRepository(db)

    def authenticate(self, identifier: str) -> dict:
        """Authenticate using an employee ID or email address."""
        identifier = identifier.strip()

        try:
            if "@" in identifier:
                emp = self.repo.get_by_email(identifier.lower())
            else:
                emp = self.repo.get(identifier)

            return {
                "employee_id": emp.employee_id,
                "name": emp.name,
                "email": emp.email,
                "department": emp.department,
                "role": emp.role,
                "employee_type": emp.employee_type,
            }

        except NotFoundError:
            raise AuthenticationError(
                f"Account '{identifier}' not found in demo employee directory."
            )


# ─── OAuth Providers ─────────────────────────────────────────────────────────


class GoogleIdentityProvider(IdentityProvider):
    """Google Workspace SSO provider.

    For local development this simulates Google authentication by accepting
    a provisioned employee email address. Real Google OAuth token validation
    can be added later.
    """

    def __init__(self, db: Session):
        self.repo = EmployeeRepository(db)

    def authenticate(self, credential: str) -> dict:
        """Authenticate a provisioned Google Workspace account."""
        credential = credential.strip()

        if "@" not in credential:
            raise AuthenticationError(
                "Invalid Google authentication credential."
            )

        email = credential.lower()

        try:
            emp = self.repo.get_by_email(email)

            return {
                "employee_id": emp.employee_id,
                "name": emp.name,
                "email": emp.email,
                "department": emp.department,
                "role": emp.role,
                "employee_type": emp.employee_type,
            }

        except NotFoundError:
            raise AuthenticationError(
                f"Google account '{email}' is not provisioned "
                "in Veridian Directory."
            )


class MicrosoftIdentityProvider(IdentityProvider):
    """Future Microsoft/Azure AD identity provider."""

    def authenticate(self, credential: str) -> dict:
        raise NotImplementedError(
            "Microsoft OAuth not configured for this environment."
        )


class SlackIdentityProvider(IdentityProvider):
    """Future Slack identity provider."""

    def authenticate(self, credential: str) -> dict:
        raise NotImplementedError(
            "Slack OAuth not configured for this environment."
        )


# ─── JWT utilities ────────────────────────────────────────────────────────────


def create_access_token(identity: dict) -> str:
    """Create a signed JWT access token for an authenticated employee."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(
        minutes=settings.access_token_expire_minutes
    )

    payload = {
        **identity,
        "exp": expire,
        "iat": now,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload

    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}")


def get_current_employee(token: str) -> dict:
    """Decode JWT and return employee identity dict."""
    return decode_token(token)
