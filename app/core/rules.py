"""Deterministic rule engine — all business decisions live here, never in the LLM.

The LLM classifies intent and generates natural language. This module
decides WHAT HAPPENS based on that classified intent + extracted entities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RuleOutcome(str, Enum):
    RESOLVE = "RESOLVE"
    CLARIFY = "CLARIFY"
    ESCALATE = "ESCALATE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Intent(str, Enum):
    PASSWORD_RESET = "PASSWORD_RESET"
    VPN_ACCESS = "VPN_ACCESS"
    SOFTWARE_REQUEST = "SOFTWARE_REQUEST"
    SECURITY_INCIDENT = "SECURITY_INCIDENT"
    GUEST_WIFI = "GUEST_WIFI"
    WFH_EQUIPMENT = "WFH_EQUIPMENT"
    LAPTOP_ISSUE = "LAPTOP_ISSUE"
    ADMIN_ACCESS = "ADMIN_ACCESS"
    ONBOARDING = "ONBOARDING"
    GENERAL = "GENERAL"
    UNKNOWN = "UNKNOWN"


@dataclass
class RuleResult:
    outcome: RuleOutcome
    risk: RiskLevel
    reason: str
    assigned_team: Optional[str] = None
    contact_email: Optional[str] = None
    requires_ticket: bool = False
    self_service_steps: Optional[str] = None
    additional_policies: Optional[list[str]] = None  # when multiple policies interact


def evaluate(intent: Intent, entities: dict) -> RuleResult:
    """Apply deterministic business rules. Returns a RuleResult.

    This function is the single authoritative decision point.
    No LLM involvement here.
    """
    match intent:
        case Intent.PASSWORD_RESET:
            return _rule_password(entities)
        case Intent.VPN_ACCESS:
            return _rule_vpn(entities)
        case Intent.SOFTWARE_REQUEST:
            return _rule_software(entities)
        case Intent.SECURITY_INCIDENT:
            return _rule_security_incident(entities)
        case Intent.GUEST_WIFI:
            return _rule_guest_wifi()
        case Intent.WFH_EQUIPMENT:
            return _rule_wfh_equipment(entities)
        case Intent.LAPTOP_ISSUE:
            return _rule_laptop(entities)
        case Intent.ADMIN_ACCESS:
            return _rule_admin_access()
        case Intent.ONBOARDING:
            return _rule_onboarding()
        case Intent.UNKNOWN:
            return _rule_unknown()
        case _:
            return _rule_general()


# ─── Individual rule implementations ─────────────────────────────────────────

def _rule_password(entities: dict) -> RuleResult:
    locked = entities.get("is_locked", False)
    failed_attempts = entities.get("failed_attempts", 0)

    if locked or failed_attempts >= 5:
        return RuleResult(
            outcome=RuleOutcome.ESCALATE,
            risk=RiskLevel.MEDIUM,
            reason="Account is locked after 5+ failed attempts. IT must manually unlock — self-service not available.",
            assigned_team="IT Support",
            contact_email="itsupport@veridian-corp.example",
            requires_ticket=True,
        )
    # Self-service password reset is available
    return RuleResult(
        outcome=RuleOutcome.RESOLVE,
        risk=RiskLevel.LOW,
        reason="Self-service password reset is available via the company portal.",
        self_service_steps=(
            "Visit https://portal.veridian-corp.example/password-reset, "
            "verify your identity, and follow the on-screen instructions."
        ),
    )


def _rule_vpn(entities: dict) -> RuleResult:
    employee_type = entities.get("employee_type", "full_time").lower()
    issue_type = entities.get("issue_type", "").lower()

    if employee_type in ("contractor", "temp", "temporary"):
        return RuleResult(
            outcome=RuleOutcome.ESCALATE,
            risk=RiskLevel.MEDIUM,
            reason="Contractors require explicit manager approval before VPN access is granted.",
            assigned_team="IT Support",
            contact_email="itsupport@veridian-corp.example",
            requires_ticket=True,
        )

    # Expired credentials — full-time employee can self-renew
    if "expir" in issue_type or entities.get("credentials_expired", False):
        return RuleResult(
            outcome=RuleOutcome.RESOLVE,
            risk=RiskLevel.LOW,
            reason="VPN credentials expire every 90 days. Full-time employees can renew via the Self-Service Portal.",
            self_service_steps=(
                "Log in to https://portal.veridian-corp.example/vpn-renewal "
                "to renew your VPN credentials. If renewal fails, contact IT Support."
            ),
        )

    # Generic VPN issue
    return RuleResult(
        outcome=RuleOutcome.ESCALATE,
        risk=RiskLevel.LOW,
        reason="VPN connectivity issue requires IT Support investigation.",
        assigned_team="IT Support",
        contact_email="itsupport@veridian-corp.example",
        requires_ticket=True,
    )


def _rule_software(entities: dict) -> RuleResult:
    in_catalog = entities.get("in_catalog", None)
    software_name = entities.get("software_name", "the requested software")

    # We don't know — ask
    if in_catalog is None:
        return RuleResult(
            outcome=RuleOutcome.CLARIFY,
            risk=RiskLevel.LOW,
            reason=f"Need to check whether '{software_name}' is in the Approved Software Catalogue.",
        )

    if in_catalog:
        return RuleResult(
            outcome=RuleOutcome.RESOLVE,
            risk=RiskLevel.LOW,
            reason=f"'{software_name}' is in the Approved Software Catalogue and may be self-installed.",
            self_service_steps=(
                "Visit the Approved Software Catalogue on the intranet and follow "
                "the installation guide for your operating system."
            ),
        )

    # Non-catalog software requires IT Security review
    return RuleResult(
        outcome=RuleOutcome.ESCALATE,
        risk=RiskLevel.MEDIUM,
        reason=(
            f"'{software_name}' is not in the Approved Catalogue. "
            "An IT Security Review is required before installation."
        ),
        assigned_team="IT Security",
        contact_email="itsecurity@veridian-corp.example",
        requires_ticket=True,
    )


def _rule_security_incident(_entities: dict) -> RuleResult:
    # All suspected security incidents are HIGH risk and always escalated
    return RuleResult(
        outcome=RuleOutcome.ESCALATE,
        risk=RiskLevel.HIGH,
        reason=(
            "All suspected phishing, malware, or unauthorized access incidents "
            "are treated as HIGH risk and require immediate Security team review."
        ),
        assigned_team="Security",
        contact_email="security@veridian-corp.example",
        requires_ticket=True,
    )


def _rule_guest_wifi() -> RuleResult:
    # No IT ticket ever required
    return RuleResult(
        outcome=RuleOutcome.RESOLVE,
        risk=RiskLevel.LOW,
        reason="Guest Wi-Fi credentials can be generated from the front-desk kiosk — no IT ticket required.",
        self_service_steps=(
            "Visit the front-desk kiosk in any Veridian office location. "
            "Credentials are valid for 24 hours."
        ),
    )


def _rule_wfh_equipment(entities: dict) -> RuleResult:
    employee_type = entities.get("employee_type", "full_time").lower()
    tenure_days = entities.get("tenure_days", 91)  # default: assume eligible

    if employee_type in ("contractor", "temp", "temporary"):
        return RuleResult(
            outcome=RuleOutcome.RESOLVE,
            risk=RiskLevel.LOW,
            reason="Contractors are not eligible for WFH equipment support under company policy.",
        )

    if tenure_days < 90:
        return RuleResult(
            outcome=RuleOutcome.RESOLVE,
            risk=RiskLevel.LOW,
            reason=(
                "WFH equipment support requires completion of the 90-day probationary period. "
                f"You have approximately {90 - tenure_days} days remaining."
            ),
        )

    # Eligible — needs manager approval
    return RuleResult(
        outcome=RuleOutcome.ESCALATE,
        risk=RiskLevel.LOW,
        reason=(
            "WFH equipment request must be approved by your direct manager "
            "before IT can procure equipment (up to £500/year for full-time employees)."
        ),
        assigned_team="IT Support",
        contact_email="itsupport@veridian-corp.example",
        requires_ticket=True,
    )


def _rule_laptop(entities: dict) -> RuleResult:
    # Both Laptop Replacement Policy (KB-05) and Asset Management Policy apply
    damage_type = entities.get("damage_type", "performance")

    reason = (
        "Laptop issues require IT Support assessment. "
        "Both the Laptop Replacement Policy and the Asset Management Policy apply. "
    )

    if damage_type in ("theft", "lost"):
        reason += (
            "Loss or theft must be reported to IT Security and the office manager immediately. "
            "A police report may be required."
        )
        return RuleResult(
            outcome=RuleOutcome.ESCALATE,
            risk=RiskLevel.HIGH,
            reason=reason,
            assigned_team="IT Security",
            contact_email="itsecurity@veridian-corp.example",
            requires_ticket=True,
            additional_policies=["KB-05"],
        )

    if damage_type == "accidental":
        reason += "Accidental damage must be reported within 24 hours and may be covered by corporate insurance."

    return RuleResult(
        outcome=RuleOutcome.ESCALATE,
        risk=RiskLevel.MEDIUM,
        reason=reason,
        assigned_team="IT Support",
        contact_email="itsupport@veridian-corp.example",
        requires_ticket=True,
        additional_policies=["KB-05"],
    )


def _rule_admin_access() -> RuleResult:
    # Always HIGH risk, always requires human review
    return RuleResult(
        outcome=RuleOutcome.ESCALATE,
        risk=RiskLevel.HIGH,
        reason=(
            "Administrative and privileged access requests require formal approval "
            "from your direct manager AND the IT Security team. "
            "All privileged access is time-limited and reviewed quarterly."
        ),
        assigned_team="IT Security",
        contact_email="itsecurity@veridian-corp.example",
        requires_ticket=True,
    )


def _rule_onboarding() -> RuleResult:
    return RuleResult(
        outcome=RuleOutcome.ESCALATE,
        risk=RiskLevel.LOW,
        reason="New employee onboarding IT setup requires coordination with HR and IT Support.",
        assigned_team="IT Support",
        contact_email="itsupport@veridian-corp.example",
        requires_ticket=True,
    )


def _rule_unknown() -> RuleResult:
    return RuleResult(
        outcome=RuleOutcome.CLARIFY,
        risk=RiskLevel.LOW,
        reason="Insufficient information to classify the request. Clarification needed.",
    )


def _rule_general() -> RuleResult:
    return RuleResult(
        outcome=RuleOutcome.ESCALATE,
        risk=RiskLevel.LOW,
        reason="General IT request routed to IT Support for triage.",
        assigned_team="IT Support",
        contact_email="itsupport@veridian-corp.example",
        requires_ticket=True,
    )

