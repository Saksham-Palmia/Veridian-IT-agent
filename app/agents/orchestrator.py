"""Agent Orchestrator — the complete IT support decision pipeline.

Flow:
  1. Gather employee context in parallel (ThreadPoolExecutor)
  2. Classify intent (LLM or keyword fallback)
  3. Extract entities (LLM or regex fallback)
  4. Retrieve relevant policy (deterministic KB lookup)
  5. Evaluate deterministic rules → RESOLVE / CLARIFY / ESCALATE
  6. Classify risk (deterministic)
  7. If ESCALATE → create ITSM ticket → send notification
  8. Generate natural-language response (LLM or template fallback)
  9. Record full audit trail
  10. Return structured ChatResponse
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.core.executor import executor
from app.core.rules import evaluate, Intent, RuleOutcome
from app.integrations.llm import LLMClient
from app.models.request import RequestStatus
from app.repositories.repositories import (
    ConversationRepository,
    EmployeeRepository,
    RequestRepository,
    TicketRepository,
)
from app.schemas.chat import ChatResponse, PolicySource
from app.services.audit_service import AuditService, AuditEventType
from app.services.itsm_service import SQLiteITSMAdapter
from app.services.notification_service import NotificationService
from app.services.policy_service import PolicyService

logger = logging.getLogger(__name__)
settings = get_settings()

# Singleton LLM client (shared across requests)
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient(api_key=settings.gemini_api_key)
    return _llm_client


class AgentOrchestrator:
    """Runs the full IT support agent pipeline for a single employee message."""

    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm_client()
        self.policy_service = PolicyService()
        self.employee_repo = EmployeeRepository(db)
        self.conv_repo = ConversationRepository(db)
        self.request_repo = RequestRepository(db)
        self.ticket_repo = TicketRepository(db)
        self.itsm = SQLiteITSMAdapter(db)
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)

    async def process(
        self,
        employee_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> ChatResponse:
        """Entry point — runs the full pipeline and returns a structured response."""

        # ── Step 0: Get / create conversation ─────────────────────────────────
        if conversation_id:
            conv = self.conv_repo.get(conversation_id)
            if not conv:
                conv = self.conv_repo.create(employee_id)
        else:
            conv = self.conv_repo.create(employee_id)

        # ── Step 1: Create initial request record ──────────────────────────────
        employee = self.employee_repo.get(employee_id)
        request = self.request_repo.create(
            employee_id=employee_id,
            employee_name=employee.name,
            message=message,
            conversation_id=conv.conversation_id,
        )
        self.conv_repo.set_current_request(conv.conversation_id, request.request_id)

        self.audit.log(request.request_id, AuditEventType.REQUEST_RECEIVED,
                       actor="employee",
                       message=message[:200],
                       conversation_id=conv.conversation_id)

        # Save employee message to conversation
        self.conv_repo.append_message(conv.conversation_id, "employee", message)

        # ── Step 2: Parallel context gather (ThreadPoolExecutor) ───────────────
        # Fetch employee record + active tickets concurrently — independent blocking ops
        future_employee = executor.submit(self.employee_repo.get, employee_id)
        future_active_tickets = executor.submit(self.itsm.get_active_tickets, employee_id)

        emp = future_employee.result()
        active_tickets = future_active_tickets.result()

        # ── Step 3: Intent classification ──────────────────────────────────────
        intent_str = self.llm.classify_intent(message)
        intent = Intent(intent_str) if intent_str in Intent._value2member_map_ else Intent.UNKNOWN

        self.audit.log(request.request_id, AuditEventType.INTENT_CLASSIFIED,
                       intent=intent.value, llm_enabled=self.llm.enabled)

        self.request_repo.update(request.request_id, intent=intent.value)

        # ── Step 4: Entity extraction ──────────────────────────────────────────
        entities = self.llm.extract_entities(message, intent.value)
        # Inject employee type from DB (authoritative source, not LLM)
        entities["employee_type"] = emp.employee_type

        self.audit.log(request.request_id, AuditEventType.ENTITY_EXTRACTED,
                       entities=entities)
        self.request_repo.update(request.request_id, entities=entities)

        # ── Step 5: Policy retrieval ───────────────────────────────────────────
        policy = self.policy_service.find_by_intent(intent.value)
        if not policy:
            matches = self.policy_service.search(message)
            policy = matches[0].policy if matches else None

        policy_id = policy["id"] if policy else None
        self.audit.log(request.request_id, AuditEventType.POLICY_RETRIEVED,
                       policy_id=policy_id,
                       policy_title=policy["title"] if policy else None)

        if policy_id:
            self.request_repo.update(request.request_id,
                                     category=policy.get("category"),
                                     source_policy=policy_id)

        # ── Step 6: Deterministic rule evaluation ──────────────────────────────
        rule_result = evaluate(intent, entities)

        self.audit.log(request.request_id, AuditEventType.RULE_EVALUATED,
                       outcome=rule_result.outcome.value,
                       reason=rule_result.reason,
                       risk=rule_result.risk.value)

        # ── Step 7: Risk classification ────────────────────────────────────────
        self.request_repo.update(request.request_id, risk=rule_result.risk.value)

        self.audit.log(request.request_id, AuditEventType.RISK_CLASSIFIED,
                       risk=rule_result.risk.value)

        # ── Step 8: Execute outcome ────────────────────────────────────────────
        ticket_id: str | None = None
        notification_sent = False
        new_status: str

        if rule_result.outcome == RuleOutcome.ESCALATE:
            new_status = RequestStatus.ESCALATED

            # Create ITSM ticket
            ticket = self.itsm.create_ticket(
                request_id=request.request_id,
                employee_id=employee_id,
                category=intent.value,
                description=f"Employee: {emp.name}\n\nMessage: {message}\n\nReason: {rule_result.reason}",
                risk=rule_result.risk.value,
                assigned_team=rule_result.assigned_team,
                contact_email=rule_result.contact_email,
                source_policy=policy_id,
            )
            ticket_id = ticket.ticket_id

            self.audit.log(request.request_id, AuditEventType.TICKET_CREATED,
                           ticket_id=ticket_id,
                           assigned_team=rule_result.assigned_team)

            self.request_repo.update(request.request_id, ticket_id=ticket_id)

            # Send notification to support team
            if rule_result.assigned_team and rule_result.contact_email:
                notification_sent = self.notifications.notify_escalation(
                    request_id=request.request_id,
                    ticket_id=ticket_id,
                    team=rule_result.assigned_team,
                    contact_email=rule_result.contact_email,
                    employee_name=emp.name,
                    category=intent.value,
                    description=message,
                    risk=rule_result.risk.value,
                )
                if notification_sent:
                    self.audit.log(request.request_id, AuditEventType.NOTIFICATION_SENT,
                                   ticket_id=ticket_id,
                                   recipient=rule_result.contact_email)
                    self.ticket_repo.mark_notification_sent(ticket_id)

            self.audit.log(request.request_id, AuditEventType.ESCALATED,
                           ticket_id=ticket_id,
                           assigned_team=rule_result.assigned_team)

        elif rule_result.outcome == RuleOutcome.CLARIFY:
            new_status = RequestStatus.WAITING_FOR_EMPLOYEE
            self.audit.log(request.request_id, AuditEventType.FOLLOWUP_QUESTION)

        else:  # RESOLVE
            new_status = RequestStatus.RESOLVED

        # Transition request status
        try:
            self.request_repo.transition_status(request.request_id, RequestStatus(new_status))
        except Exception as exc:
            logger.warning("Status transition failed: %s — forcing update", exc)
            self.request_repo.update(request.request_id, status=new_status)

        # ── Step 9: Generate natural-language response ─────────────────────────
        if rule_result.outcome == RuleOutcome.CLARIFY:
            response_text = self.llm.generate_clarification(message, intent.value, emp.name)
        else:
            response_text = self.llm.generate_response(
                message=message,
                intent=intent.value,
                rule_result=rule_result,
                policy=policy,
                employee_name=emp.name,
            )

        # Save agent response
        self.request_repo.update(request.request_id, agent_response=response_text)
        self.conv_repo.append_message(conv.conversation_id, "agent", response_text)

        self.audit.log(request.request_id, AuditEventType.RESPONSE_SENT,
                       outcome=rule_result.outcome.value,
                       status=new_status)

        # ── Step 10: Build structured response ────────────────────────────────
        policy_source = None
        if policy:
            policy_source = PolicySource(
                id=policy["id"],
                title=policy["title"],
                relevance=1.0,
            )

        return ChatResponse(
            request_id=request.request_id,
            conversation_id=conv.conversation_id,
            message=response_text,
            intent=intent.value,
            risk=rule_result.risk.value,
            status=new_status,
            outcome=rule_result.outcome.value,
            source=policy_source,
            ticket_id=ticket_id,
            assigned_team=rule_result.assigned_team,
            notification_sent=notification_sent,
            self_service_steps=rule_result.self_service_steps,
        )

