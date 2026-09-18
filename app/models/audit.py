"""AuditEvent ORM model — immutable record of all workflow events."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from app.db.database import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    event_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    actor = Column(String, default="agent")   # agent | employee | system
    metadata_ = Column("metadata", JSON, default=dict)

