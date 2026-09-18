"""Tickets API — admin view of ITSM tickets."""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.schemas.models import TicketSchema
from app.schemas.common import ApiResponse
from app.repositories.repositories import TicketRepository
from app.core.exceptions import NotFoundError

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def _require_admin(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Admin authentication required.")
    return True


@router.get("", response_model=ApiResponse[list[TicketSchema]])
def list_tickets(
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    _admin: bool = Depends(_require_admin),
):
    repo = TicketRepository(db)
    tickets = repo.list_all(limit=limit)
    return ApiResponse.ok([TicketSchema.model_validate(t) for t in tickets])


@router.get("/{ticket_id}", response_model=ApiResponse[TicketSchema])
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    _admin: bool = Depends(_require_admin),
):
    try:
        repo = TicketRepository(db)
        ticket = repo.get(ticket_id)
        return ApiResponse.ok(TicketSchema.model_validate(ticket))
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

