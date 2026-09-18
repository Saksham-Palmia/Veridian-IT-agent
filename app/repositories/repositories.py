"""Repository layer — database CRUD for all domain objects.

All queries go through these repositories so the DB backend
can be swapped (SQLite → PostgreSQL) without touching services.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.conversation import Conversation
from app.models.request import Request, RequestStatus, VALID_TRANSITIONS
from app.models.ticket import Ticket, TicketStatus
from app.models.audit import AuditEvent
from app.models.notification import Notification
from app.core.exceptions import NotFoundError, InvalidStateTransitionError


# ─── Employee Repository ──────────────────────────────────────────────────────

class EmployeeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, employee_id: str) -> Employee:
        emp = self.db.query(Employee).filter(Employee.employee_id == employee_id).first()
        if not emp:
            raise NotFoundError(f"Employee '{employee_id}' not found.")
        return emp

    def get_by_email(self, email: str) -> Employee:
        emp = self.db.query(Employee).filter(Employee.email == email).first()
        if not emp:
            raise NotFoundError(f"Employee with email '{email}' not found.")
        return emp

    def list_all(self) -> list[Employee]:
        return self.db.query(Employee).all()


# ─── Conversation Repository ──────────────────────────────────────────────────

class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, employee_id: str) -> Conversation:
        conv = Conversation(employee_id=employee_id)
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get(self, conversation_id: str) -> Optional[Conversation]:
        return self.db.query(Conversation).filter(Conversation.conversation_id == conversation_id).first()

    def append_message(self, conversation_id: str, role: str, content: str) -> Conversation:
        conv = self.get(conversation_id)
        if not conv:
            raise NotFoundError(f"Conversation '{conversation_id}' not found.")
        messages = list(conv.messages or [])
        messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        conv.messages = messages
        conv.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def set_current_request(self, conversation_id: str, request_id: str) -> None:
        conv = self.get(conversation_id)
        if conv:
            conv.current_request_id = request_id
            self.db.commit()


# ─── Request Repository ───────────────────────────────────────────────────────

class RequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, employee_id: str, employee_name: str, message: str,
               conversation_id: str | None = None) -> Request:
        req = Request(
            employee_id=employee_id,
            employee_name=employee_name,
            message=message,
            conversation_id=conversation_id,
        )
        self.db.add(req)
        self.db.commit()
        self.db.refresh(req)
        return req

    def get(self, request_id: str) -> Request:
        req = self.db.query(Request).filter(Request.request_id == request_id).first()
        if not req:
            raise NotFoundError(f"Request '{request_id}' not found.")
        return req

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Request]:
        return (self.db.query(Request)
                .order_by(Request.created_at.desc())
                .offset(offset).limit(limit).all())

    def update(self, request_id: str, **kwargs) -> Request:
        req = self.get(request_id)
        for key, value in kwargs.items():
            if hasattr(req, key):
                setattr(req, key, value)
        req.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(req)
        return req

    def transition_status(self, request_id: str, new_status: RequestStatus) -> Request:
        req = self.get(request_id)
        current = RequestStatus(req.status)
        if new_status not in VALID_TRANSITIONS.get(current, set()):
            raise InvalidStateTransitionError(
                f"Cannot transition '{request_id}' from {current} to {new_status}."
            )
        req.status = new_status
        req.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(req)
        return req


# ─── Ticket Repository ────────────────────────────────────────────────────────

class TicketRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, request_id: str, employee_id: str, category: str, description: str,
               risk: str, assigned_team: str | None = None, contact_email: str | None = None,
               source_policy: str | None = None) -> Ticket:
        ticket = Ticket(
            request_id=request_id,
            employee_id=employee_id,
            category=category,
            description=description,
            risk=risk,
            assigned_team=assigned_team,
            contact_email=contact_email,
            source_policy=source_policy,
        )
        self.db.add(ticket)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def get(self, ticket_id: str) -> Ticket:
        ticket = self.db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
        if not ticket:
            raise NotFoundError(f"Ticket '{ticket_id}' not found.")
        return ticket

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Ticket]:
        return (self.db.query(Ticket)
                .order_by(Ticket.created_at.desc())
                .offset(offset).limit(limit).all())

    def get_active_for_employee(self, employee_id: str) -> list[Ticket]:
        """Used by ThreadPoolExecutor for parallel context fetch."""
        return (self.db.query(Ticket)
                .filter(Ticket.employee_id == employee_id,
                        Ticket.status.notin_([TicketStatus.CLOSED, TicketStatus.RESOLVED]))
                .all())

    def update(self, ticket_id: str, **kwargs) -> Ticket:
        ticket = self.get(ticket_id)
        for key, value in kwargs.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)
        ticket.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(ticket)
        return ticket

    def mark_notification_sent(self, ticket_id: str) -> None:
        ticket = self.get(ticket_id)
        ticket.notification_sent = True
        self.db.commit()


# ─── Audit Repository ─────────────────────────────────────────────────────────

class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def log(self, request_id: str, event_type: str,
            actor: str = "agent", metadata: dict | None = None) -> AuditEvent:
        event = AuditEvent(
            request_id=request_id,
            event_type=event_type,
            actor=actor,
            metadata_=metadata or {},
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def get_for_request(self, request_id: str) -> list[AuditEvent]:
        return (self.db.query(AuditEvent)
                .filter(AuditEvent.request_id == request_id)
                .order_by(AuditEvent.timestamp.asc())
                .all())


# ─── Notification Repository ──────────────────────────────────────────────────

class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, request_id: str, channel: str, recipient: str,
               subject: str | None = None, body: str | None = None,
               ticket_id: str | None = None) -> Notification:
        notif = Notification(
            request_id=request_id,
            ticket_id=ticket_id,
            channel=channel,
            recipient=recipient,
            subject=subject,
            body=body,
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)
        return notif

    def mark_sent(self, notification_id: str) -> None:
        notif = self.db.query(Notification).filter(Notification.notification_id == notification_id).first()
        if notif:
            notif.sent = True
            self.db.commit()

    def mark_failed(self, notification_id: str, error: str) -> None:
        notif = self.db.query(Notification).filter(Notification.notification_id == notification_id).first()
        if notif:
            notif.sent = False
            notif.error = error
            self.db.commit()

    def list_all(self, limit: int = 100) -> list[Notification]:
        return (self.db.query(Notification)
                .order_by(Notification.created_at.desc())
                .limit(limit).all())

