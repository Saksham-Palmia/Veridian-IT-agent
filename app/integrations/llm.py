"""Gemini LLM integration with deterministic fallback.

The LLM is used ONLY for:
  - Intent classification
  - Entity extraction
  - Natural-language response generation
  - Clarification question generation

It does NOT make business decisions — those live in app/core/rules.py.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Intent keyword map for deterministic fallback
KEYWORD_INTENT_MAP: dict[str, list[str]] = {
    "PASSWORD_RESET": ["password", "reset", "locked", "lockout", "login", "credentials", "forgot", "expire", "unlock", "account locked"],
    "VPN_ACCESS": ["vpn", "remote access", "vpn credentials", "vpn expired", "connect remotely", "tunnel"],
    "SOFTWARE_REQUEST": ["install", "software", "application", "app", "program", "tool", "download", "licence", "license", "catalog", "catalogue"],
    "SECURITY_INCIDENT": ["phishing", "malware", "virus", "suspicious email", "hack", "breach", "unauthorized", "clicked link", "ransomware", "infected", "suspicious link", "weird email"],
    "GUEST_WIFI": ["guest wifi", "guest wi-fi", "visitor wifi", "visitor internet", "client wifi", "guest network", "wifi for visitor", "wi-fi for guest"],
    "WFH_EQUIPMENT": ["work from home", "wfh", "home office", "monitor", "keyboard", "mouse", "desk", "chair", "headset", "ergonomic", "remote work equipment"],
    "LAPTOP_ISSUE": ["laptop", "computer", "device", "hardware", "screen", "broken", "slow", "freezing", "macbook", "windows laptop", "replace laptop", "laptop replacement"],
    "ADMIN_ACCESS": ["admin access", "administrator", "root access", "sudo", "privileged", "server access", "database admin", "production access", "elevated access", "superuser"],
    "ONBOARDING": ["new employee", "first day", "onboarding", "joining", "start date", "new starter", "new hire"],
}


class LLMClient:
    """Wraps the Gemini API. Falls back gracefully when no key is configured."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._client = None

        if api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=api_key)
                self._model = "gemini-2.0-flash"
                logger.info("LLM: Gemini client initialised with model %s", self._model)
            except Exception as exc:
                logger.warning("LLM: Failed to initialise Gemini client: %s — using fallback", exc)
                self._client = None
        else:
            logger.info("LLM: No GEMINI_API_KEY set — using keyword-rule fallback mode")

    @property
    def enabled(self) -> bool:
        return self._client is not None

    # ── Intent classification ─────────────────────────────────────────────────

    def classify_intent(self, message: str) -> str:
        """Classify message intent. Returns one of the Intent enum string values."""
        if self.enabled:
            try:
                return self._llm_classify_intent(message)
            except Exception as exc:
                logger.warning("LLM intent classification failed: %s — using fallback", exc)

        return self._keyword_classify_intent(message)

    def _llm_classify_intent(self, message: str) -> str:
        prompt = f"""You are an IT support intent classifier for Veridian Corp.

Classify the following employee message into EXACTLY ONE of these categories:
PASSWORD_RESET, VPN_ACCESS, SOFTWARE_REQUEST, SECURITY_INCIDENT, GUEST_WIFI,
WFH_EQUIPMENT, LAPTOP_ISSUE, ADMIN_ACCESS, ONBOARDING, GENERAL, UNKNOWN

Rules:
- SECURITY_INCIDENT: any mention of phishing, malware, suspicious email, clicking links, hacking, ransomware
- ADMIN_ACCESS: requests for admin/root/privileged/server/database access
- UNKNOWN: message is too vague to classify

Respond with ONLY the category name, nothing else.

Employee message: "{message}"
"""
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        result = response.text.strip().upper()
        valid = {"PASSWORD_RESET", "VPN_ACCESS", "SOFTWARE_REQUEST", "SECURITY_INCIDENT",
                 "GUEST_WIFI", "WFH_EQUIPMENT", "LAPTOP_ISSUE", "ADMIN_ACCESS",
                 "ONBOARDING", "GENERAL", "UNKNOWN"}
        return result if result in valid else "UNKNOWN"

    def _keyword_classify_intent(self, message: str) -> str:
        msg_lower = message.lower()
        scores: dict[str, int] = {}
        for intent, keywords in KEYWORD_INTENT_MAP.items():
            score = sum(1 for kw in keywords if kw in msg_lower)
            if score > 0:
                scores[intent] = score
        if not scores:
            return "UNKNOWN"
        return max(scores, key=lambda k: scores[k])

    # ── Entity extraction ─────────────────────────────────────────────────────

    def extract_entities(self, message: str, intent: str) -> dict:
        """Extract structured entities from message. Returns a dict."""
        if self.enabled:
            try:
                return self._llm_extract_entities(message, intent)
            except Exception as exc:
                logger.warning("LLM entity extraction failed: %s — using fallback", exc)

        return self._keyword_extract_entities(message, intent)

    def _llm_extract_entities(self, message: str, intent: str) -> dict:
        prompt = f"""You are an entity extractor for an IT support system at Veridian Corp.

Given the employee message and its classified intent, extract relevant entities as JSON.

Intent: {intent}
Message: "{message}"

Extract these entities (only include fields that are clearly present or inferable):
- employee_type: "full_time" | "contractor" | "temp" (default "full_time" if not mentioned)
- is_locked: boolean — true if account is locked/unable to login
- failed_attempts: integer — number of failed login attempts mentioned
- credentials_expired: boolean — true if VPN/password credentials are expired
- software_name: string — name of software being requested
- in_catalog: boolean | null — null if unknown
- issue_type: string — brief description of the specific issue
- damage_type: "performance" | "accidental" | "theft" | "lost"
- tenure_days: integer — days at company if mentioned

Respond with ONLY valid JSON, no explanation.
"""
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        text = response.text.strip()
        # Strip markdown code fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text)

    def _keyword_extract_entities(self, message: str, intent: str) -> dict:
        msg_lower = message.lower()
        entities: dict = {}

        if "contractor" in msg_lower or "contract" in msg_lower:
            entities["employee_type"] = "contractor"
        elif "temp" in msg_lower:
            entities["employee_type"] = "temp"

        if any(w in msg_lower for w in ["locked", "lock out", "lockout", "locked out"]):
            entities["is_locked"] = True

        if any(w in msg_lower for w in ["expired", "expire"]):
            entities["credentials_expired"] = True
            if intent == "VPN_ACCESS":
                entities["issue_type"] = "expired"

        if intent == "SOFTWARE_REQUEST":
            # Try to extract software name from common patterns
            patterns = [r"install\s+(\w[\w\s]+?)(?:\s+on|\s+for|\.|$)",
                        r"need\s+(\w[\w\s]+?)\s+(?:software|tool|app)"]
            for pat in patterns:
                m = re.search(pat, msg_lower)
                if m:
                    entities["software_name"] = m.group(1).strip()
                    break

        if any(w in msg_lower for w in ["stolen", "theft", "stolen laptop", "missing"]):
            entities["damage_type"] = "theft"
        elif any(w in msg_lower for w in ["lost", "can't find"]):
            entities["damage_type"] = "lost"
        elif any(w in msg_lower for w in ["dropped", "crack", "damaged", "spill"]):
            entities["damage_type"] = "accidental"
        elif intent == "LAPTOP_ISSUE":
            entities["damage_type"] = "performance"

        return entities

    # ── Response generation ───────────────────────────────────────────────────

    def generate_response(self, message: str, intent: str, rule_result,
                          policy: dict | None, employee_name: str) -> str:
        """Generate a natural-language response. Falls back to templates."""
        if self.enabled:
            try:
                return self._llm_generate_response(message, intent, rule_result, policy, employee_name)
            except Exception as exc:
                logger.warning("LLM response generation failed: %s — using template fallback", exc)

        return self._template_response(intent, rule_result, policy, employee_name)

    def _llm_generate_response(self, message: str, intent: str, rule_result,
                                policy: dict | None, employee_name: str) -> str:
        policy_content = policy.get("content", "") if policy else "No specific policy retrieved."
        outcome = rule_result.outcome.value
        reason = rule_result.reason
        steps = rule_result.self_service_steps or ""

        prompt = f"""You are the Veridian Corp internal IT Support Agent. 

Your job: give {employee_name} a helpful, concise, professional response to their IT request.

Employee's message: "{message}"
Intent classified: {intent}
Decision: {outcome}
Reasoning: {reason}
Self-service steps (if any): {steps}
Relevant policy: {policy_content[:500] if policy_content else "N/A"}

Rules:
- Be warm and professional, not robotic
- For RESOLVE: explain what they can do themselves
- For ESCALATE: explain what will happen next (ticket created, team notified)
- For CLARIFY: ask ONE clear follow-up question
- Do NOT mention risk scores or internal system IDs in your response
- Keep it under 4 sentences
- If security incident: immediately advise them to disconnect from network
"""
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
        )
        return response.text.strip()

    def _template_response(self, intent: str, rule_result, policy: dict | None,
                           employee_name: str) -> str:
        outcome = rule_result.outcome.value
        team = rule_result.assigned_team or "IT Support"

        templates: dict[tuple, str] = {
            ("SECURITY_INCIDENT", "ESCALATE"): (
                f"Hi {employee_name}, this looks like a potential security incident. "
                "Please disconnect your device from all networks immediately and do NOT power it off. "
                "I've escalated this to our Security team who will contact you within the hour."
            ),
            ("PASSWORD_RESET", "RESOLVE"): (
                f"Hi {employee_name}, you can reset your password anytime via the Self-Service Portal at "
                "https://portal.veridian-corp.example/password-reset. "
                "Verify your identity and follow the on-screen steps."
            ),
            ("PASSWORD_RESET", "ESCALATE"): (
                f"Hi {employee_name}, your account appears to be locked after too many failed attempts. "
                "Self-service reset is unavailable — I've raised a ticket with IT Support who will manually unlock your account."
            ),
            ("GUEST_WIFI", "RESOLVE"): (
                f"Hi {employee_name}, guest Wi-Fi credentials can be generated from the front-desk kiosk "
                "in any Veridian office — no IT ticket needed! Credentials are valid for 24 hours."
            ),
            ("VPN_ACCESS", "RESOLVE"): (
                f"Hi {employee_name}, VPN credentials expire every 90 days and can be renewed via the Self-Service Portal "
                "at https://portal.veridian-corp.example/vpn-renewal. "
                "If renewal fails, please contact IT Support."
            ),
            ("ADMIN_ACCESS", "ESCALATE"): (
                f"Hi {employee_name}, admin and privileged access requests require approval from your manager "
                "and the IT Security team. I've raised a ticket — you'll be contacted once it's reviewed."
            ),
            ("UNKNOWN", "CLARIFY"): (
                f"Hi {employee_name}, I want to help but could use a bit more detail. "
                "Could you describe the specific issue — for example, is your device not powering on, "
                "are you having a login problem, or is it a network/connectivity issue?"
            ),
        }

        key = (intent, outcome)
        if key in templates:
            return templates[key]

        if outcome == "RESOLVE":
            steps = rule_result.self_service_steps or "Please follow the self-service instructions on the portal."
            return f"Hi {employee_name}, good news — you can handle this yourself! {steps}"
        elif outcome == "ESCALATE":
            return (
                f"Hi {employee_name}, I've logged this with {team} and created a support ticket. "
                f"The team will be in touch shortly. {rule_result.reason}"
            )
        else:  # CLARIFY
            return (
                f"Hi {employee_name}, I need a bit more information to help you. "
                "Could you describe what isn't working in more detail?"
            )

    def generate_clarification(self, message: str, intent: str, employee_name: str) -> str:
        """Generate a targeted clarification question."""
        if self.enabled:
            try:
                prompt = f"""You are the Veridian Corp IT Support Agent.

The employee sent: "{message}"
Classified intent: {intent}

Generate ONE clear, friendly follow-up question to get the specific details needed to help them.
Keep it under 2 sentences. Do not ask multiple questions.
"""
                response = self._client.models.generate_content(
                    model=self._model, contents=prompt
                )
                return response.text.strip()
            except Exception as exc:
                logger.warning("LLM clarification failed: %s", exc)

        clarifications = {
            "SOFTWARE_REQUEST": f"Hi {employee_name}, which software are you looking to install, and is it for a specific project?",
            "LAPTOP_ISSUE": f"Hi {employee_name}, could you describe the laptop issue in more detail — is it not powering on, running slowly, physically damaged, or something else?",
            "UNKNOWN": f"Hi {employee_name}, I want to help — could you describe what's not working? For example, is it a login issue, network problem, hardware fault, or something else?",
        }
        return clarifications.get(intent, f"Hi {employee_name}, could you provide more details about your IT issue so I can assist you better?")

