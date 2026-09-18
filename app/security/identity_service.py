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
from app.models.employee import Employee
from app.repositories.repositories import EmployeeRepository
from app.core.exceptions import AuthenticationError, NotFoundError

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
    """Allows reviewer to select any seeded employee and immediately use the app."""
    """Allows reviewer to sign in with email or employee ID."""

    def __init__(self, db: Session):
        self.repo = EmployeeRepository(db)

    def authenticate(self, employee_id: str) -> dict:
    def authenticate(self, identifier: str) -> dict:
        identifier = identifier.strip()
        try:
            emp = self.repo.get(employee_id)
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
            raise AuthenticationError(f"Employee '{employee_id}' not found in demo data.")
            raise AuthenticationError(f"Account '{identifier}' not found in demo employee directory.")


# ─── Stub providers for future OAuth integration ──────────────────────────────
# ─── Stub / OAuth Providers ───────────────────────────────────────────────────

class GoogleIdentityProvider(IdentityProvider):
    """Future: validates Google ID tokens and maps to Veridian employee records."""
    def authenticate(self, google_token: str) -> dict:
        raise NotImplementedError("Google OAuth not configured for this environment.")
    """Google Workspace SSO provider."""

    def __init__(self, db: Session):
        self.repo = EmployeeRepository(db)

    def authenticate(self, credential: str) -> dict:
        credential = credential.strip()
        # Simulated Google Workspace SSO or token
        if "@" in credential:
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
                raise AuthenticationError(f"Google account '{email}' is not provisioned in Veridian Directory.")
        raise AuthenticationError("Invalid Google authentication credential.")


class MicrosoftIdentityProvider(IdentityProvider):
    """Future: validates Microsoft/Azure AD tokens."""
    def authenticate(self, ms_token: str) -> dict:
        raise NotImplementedError("Microsoft OAuth not configured for this environment.")


class SlackIdentityProvider(IdentityProvider):
    """Future: validates Slack identity tokens."""
    def authenticate(self, slack_token: str) -> dict:
        raise NotImplementedError("Slack OAuth not configured for this environment.")


# ─── JWT utilities ────────────────────────────────────────────────────────────

def create_access_token(identity: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        **identity,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}")


def get_current_employee(token: str) -> dict:
    """Decode JWT and return employee identity dict."""
    return decode_token(token)

