"""Conversation ORM model — persists chat thread state."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON
from app.db.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    employee_id = Column(String, nullable=False, index=True)
    state = Column(String, default="ACTIVE")  # ACTIVE | CLOSED
    messages = Column(JSON, default=list)      # list of {role, content, timestamp}
    current_request_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

