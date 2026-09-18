"""Request, Ticket, Audit, Notification Pydantic schemas."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel


class RequestSchema(BaseModel):
    request_id: str
    employee_id: str
    employee_name: Optional[str] = None
    message: str
    category: Optional[str] = None
    status: str
    risk: Optional[str] = None
    intent: Optional[str] = None
    source_policy: Optional[str] = None
    ticket_id: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TicketSchema(BaseModel):
    ticket_id: str
    request_id: str
    employee_id: str
    category: str
    description: str
    risk: str
    status: str
    assigned_team: Optional[str] = None
    contact_email: Optional[str] = None
    source_policy: Optional[str] = None
    notification_sent: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AuditSchema(BaseModel):
    event_id: str
    request_id: str
    event_type: str
    timestamp: datetime
    actor: str
    metadata: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class NotificationSchema(BaseModel):
    notification_id: str
    request_id: str
    ticket_id: Optional[str] = None
    channel: str
    recipient: str
    subject: Optional[str] = None
    body: Optional[str] = None
    sent: bool
    error: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PolicySchema(BaseModel):
    id: str
    title: str
    category: str
    content: str
    keywords: list[str] = []
    source: str
    resolution_type: str
    assigned_team: Optional[str] = None
    contact_email: Optional[str] = None

