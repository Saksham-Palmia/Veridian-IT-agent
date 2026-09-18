"""Chat Pydantic schemas."""
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class PolicySource(BaseModel):
    id: str
    title: str
    relevance: float = 1.0


class ChatResponse(BaseModel):
    request_id: str
    conversation_id: str
    message: str          # Agent's natural language response
    intent: Optional[str] = None
    risk: Optional[str] = None
    status: str
    outcome: str          # RESOLVE | CLARIFY | ESCALATE
    source: Optional[PolicySource] = None
    ticket_id: Optional[str] = None
    assigned_team: Optional[str] = None
    notification_sent: bool = False
    self_service_steps: Optional[str] = None

