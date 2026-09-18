"""Notifications API — admin view of notification history."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.schemas.models import NotificationSchema
from app.schemas.common import ApiResponse
from app.repositories.repositories import NotificationRepository

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _require_admin(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Admin authentication required.")
    return True


@router.get("", response_model=ApiResponse[list[NotificationSchema]])
def list_notifications(
    db: Session = Depends(get_db),
    _admin: bool = Depends(_require_admin),
):
    repo = NotificationRepository(db)
    notifications = repo.list_all()
    return ApiResponse.ok([NotificationSchema.model_validate(n) for n in notifications])

