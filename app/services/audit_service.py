"""Audit service — records all workflow events."""

from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from app.repositories.repositories import AuditRepository

logger = logging.getLogger(__name__)

# Canonical event types
class AuditEventType:
    REQUEST_RECEIVED     = "REQUEST_RECEIVED"
    USER_AUTHENTICATED   = "USER_AUTHENTICATED"
    INTENT_CLASSIFIED    = "INTENT_CLASSIFIED"
    ENTITY_EXTRACTED     = "ENTITY_EXTRACTED"
    POLICY_RETRIEVED     = "POLICY_RETRIEVED"
    RISK_CLASSIFIED      = "RISK_CLASSIFIED"
    RULE_EVALUATED       = "RULE_EVALUATED"
    FOLLOWUP_QUESTION    = "FOLLOWUP_QUESTION"
    TICKET_CREATED       = "TICKET_CREATED"
    TICKET_UPDATED       = "TICKET_UPDATED"
    ESCALATED            = "ESCALATED"
    NOTIFICATION_SENT    = "NOTIFICATION_SENT"
    ACTION_APPROVED      = "ACTION_APPROVED"
    ACTION_REJECTED      = "ACTION_REJECTED"
    RESPONSE_SENT        = "RESPONSE_SENT"


class AuditService:
    def __init__(self, db: Session):
        self.repo = AuditRepository(db)

    def log(self, request_id: str, event_type: str,
            actor: str = "agent", **metadata) -> None:
        try:
            self.repo.log(request_id, event_type, actor, metadata)
            logger.debug("AUDIT [%s] %s — %s", request_id, event_type, metadata)
        except Exception as exc:
            logger.error("Failed to record audit event: %s", exc)

    def get_trail(self, request_id: str) -> list:
        events = self.repo.get_for_request(request_id)
        return [
            {
                "event_id": e.event_id,
                "request_id": e.request_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp.isoformat(),
                "actor": e.actor,
                "metadata": e.metadata_,
            }
            for e in events
        ]

