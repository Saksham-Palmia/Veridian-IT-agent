"""Chat API — main employee interaction endpoint."""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.db.database import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.common import ApiResponse
from app.agents.orchestrator import AgentOrchestrator
from app.security.identity_service import get_current_employee
from app.core.exceptions import AuthenticationError, NotFoundError

router = APIRouter(prefix="/api", tags=["chat"])


def _get_employee(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token = authorization.split(" ", 1)[1]
    try:
        return get_current_employee(token)
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.post("/chat", response_model=ApiResponse[ChatResponse])
async def chat(
    request: ChatRequest,
    employee: dict = Depends(_get_employee),
    db: Session = Depends(get_db),
):
    """Submit an IT support request. The agent processes it and returns a structured response."""
    try:
        orchestrator = AgentOrchestrator(db)
        result = await orchestrator.process(
            employee_id=employee["employee_id"],
            message=request.message,
            conversation_id=request.conversation_id,
        )
        return ApiResponse.ok(result)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")

