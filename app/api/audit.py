"""Audit API — full decision trail for a request."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.schemas.common import ApiResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _require_admin(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Admin authentication required.")
    return True


@router.get("/{request_id}", response_model=ApiResponse[list])
def get_audit_trail(
    request_id: str,
    db: Session = Depends(get_db),
    _admin: bool = Depends(_require_admin),
):
    """Returns the complete decision audit trail for a request."""
    audit_service = AuditService(db)
    trail = audit_service.get_trail(request_id)
    return ApiResponse.ok(trail)

