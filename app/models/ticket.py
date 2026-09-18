"""Ticket ORM model — ITSM ticket created when escalation is required."""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Boolean
from app.db.database import Base


class TicketStatus(str, PyEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(String, primary_key=True, default=lambda: f"TK-{uuid.uuid4().hex[:6].upper()}")
    request_id = Column(String, nullable=False, index=True)
    employee_id = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False)
    description = Column(String, nullable=False)
    risk = Column(String, nullable=False)
    status = Column(String, default=TicketStatus.OPEN)
    assigned_team = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    source_policy = Column(String, nullable=True)
    notification_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

