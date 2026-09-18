"""Request ORM model — every IT support issue submitted by an employee."""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, JSON
from app.db.database import Base


class RequestStatus(str, PyEnum):
    OPEN = "OPEN"
    WAITING_FOR_EMPLOYEE = "WAITING_FOR_EMPLOYEE"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


# Valid state transitions
VALID_TRANSITIONS: dict[RequestStatus, set[RequestStatus]] = {
    RequestStatus.OPEN: {RequestStatus.WAITING_FOR_EMPLOYEE, RequestStatus.IN_PROGRESS, RequestStatus.RESOLVED, RequestStatus.ESCALATED},
    RequestStatus.WAITING_FOR_EMPLOYEE: {RequestStatus.IN_PROGRESS, RequestStatus.CLOSED},
    RequestStatus.IN_PROGRESS: {RequestStatus.RESOLVED, RequestStatus.ESCALATED, RequestStatus.WAITING_FOR_EMPLOYEE},
    RequestStatus.RESOLVED: {RequestStatus.CLOSED, RequestStatus.OPEN},
    RequestStatus.ESCALATED: {RequestStatus.IN_PROGRESS, RequestStatus.CLOSED},
    RequestStatus.CLOSED: set(),
}


class Request(Base):
    __tablename__ = "requests"

    request_id = Column(String, primary_key=True, default=lambda: f"REQ-{uuid.uuid4().hex[:6].upper()}")
    employee_id = Column(String, nullable=False, index=True)
    employee_name = Column(String, nullable=True)
    message = Column(String, nullable=False)
    category = Column(String, nullable=True)
    status = Column(String, default=RequestStatus.OPEN)
    risk = Column(String, nullable=True)
    intent = Column(String, nullable=True)
    entities = Column(JSON, default=dict)
    source_policy = Column(String, nullable=True)
    ticket_id = Column(String, nullable=True)
    conversation_id = Column(String, nullable=True)
    agent_response = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

