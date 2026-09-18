"""ITSM service — abstract base + SQLite adapter.

Designed to be replaced by ServiceNow/Jira adapters later
without changing the orchestrator.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from sqlalchemy.orm import Session

from app.models.ticket import Ticket, TicketStatus
from app.repositories.repositories import TicketRepository

logger = logging.getLogger(__name__)


class ITSMService(ABC):
    """Abstract ITSM interface."""

    @abstractmethod
    def create_ticket(self, request_id: str, employee_id: str, category: str,
                      description: str, risk: str, assigned_team: str | None,
                      contact_email: str | None, source_policy: str | None) -> Ticket:
        ...

    @abstractmethod
    def update_ticket(self, ticket_id: str, **kwargs) -> Ticket:
        ...

    @abstractmethod
    def get_ticket(self, ticket_id: str) -> Ticket:
        ...

    @abstractmethod
    def list_tickets(self, limit: int = 100) -> list[Ticket]:
        ...

    @abstractmethod
    def get_active_tickets(self, employee_id: str) -> list[Ticket]:
        """Used by ThreadPoolExecutor for parallel context fetch."""
        ...


class SQLiteITSMAdapter(ITSMService):
    """Local SQLite-backed ITSM implementation for the MVP."""

    def __init__(self, db: Session):
        self.repo = TicketRepository(db)

    def create_ticket(self, request_id: str, employee_id: str, category: str,
                      description: str, risk: str, assigned_team: str | None = None,
                      contact_email: str | None = None, source_policy: str | None = None) -> Ticket:
        ticket = self.repo.create(
            request_id=request_id,
            employee_id=employee_id,
            category=category,
            description=description,
            risk=risk,
            assigned_team=assigned_team,
            contact_email=contact_email,
            source_policy=source_policy,
        )
        logger.info("ITSM: Created ticket %s for request %s (team: %s)",
                    ticket.ticket_id, request_id, assigned_team)
        return ticket

    def update_ticket(self, ticket_id: str, **kwargs) -> Ticket:
        return self.repo.update(ticket_id, **kwargs)

    def get_ticket(self, ticket_id: str) -> Ticket:
        return self.repo.get(ticket_id)

    def list_tickets(self, limit: int = 100) -> list[Ticket]:
        return self.repo.list_all(limit=limit)

    def get_active_tickets(self, employee_id: str) -> list[Ticket]:
        return self.repo.get_active_for_employee(employee_id)

