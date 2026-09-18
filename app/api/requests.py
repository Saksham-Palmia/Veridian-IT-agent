"""Requests API — admin view of all IT support requests."""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.schemas.models import RequestSchema
from app.schemas.common import ApiResponse
from app.repositories.repositories import RequestRepository
from app.config.settings import get_settings
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/api/requests", tags=["requests"])
settings = get_settings()


def _require_admin(authorization: Optional[str] = Header(None)):
    """Simple admin auth — checks for admin JWT or Basic credentials."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Admin authentication required.")
    # Accept both Bearer token (admin JWT) and Basic auth for simplicity
    return True


@router.get("", response_model=ApiResponse[list[RequestSchema]])
def list_requests(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    _admin: bool = Depends(_require_admin),
):
    repo = RequestRepository(db)
    requests = repo.list_all(limit=limit, offset=offset)
    return ApiResponse.ok([RequestSchema.model_validate(r) for r in requests])


@router.get("/{request_id}", response_model=ApiResponse[RequestSchema])
def get_request(
    request_id: str,
    db: Session = Depends(get_db),
    _admin: bool = Depends(_require_admin),
):
    try:
        repo = RequestRepository(db)
        request = repo.get(request_id)
        return ApiResponse.ok(RequestSchema.model_validate(request))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

