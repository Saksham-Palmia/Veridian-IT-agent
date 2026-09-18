"""Policy service — loads KB from JSON, scores relevance against a message."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "policies.json"


class PolicyMatch:
    def __init__(self, policy: dict, relevance: float):
        self.policy = policy
        self.relevance = relevance

    @property
    def policy_id(self) -> str:
        return self.policy["id"]

    @property
    def title(self) -> str:
        return self.policy["title"]

    @property
    def content(self) -> str:
        return self.policy["content"]


class PolicyService:
    def __init__(self):
        self._policies: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            self._policies = json.loads(DATA_PATH.read_text(encoding="utf-8"))
            logger.info("PolicyService: loaded %d policies.", len(self._policies))
        except Exception as exc:
            logger.error("PolicyService: failed to load policies: %s", exc)
            self._policies = []

    def get_all(self) -> list[dict]:
        return self._policies

    def get_by_id(self, policy_id: str) -> Optional[dict]:
        for p in self._policies:
            if p["id"] == policy_id:
                return p
        return None

    def find_by_intent(self, intent: str) -> Optional[dict]:
        """Direct intent→policy mapping (deterministic)."""
        mapping = {
            "PASSWORD_RESET":   "KB-01",
            "VPN_ACCESS":       "KB-02",
            "SOFTWARE_REQUEST": "KB-03",
            "WFH_EQUIPMENT":    "KB-04",
            "LAPTOP_ISSUE":     "KB-05",
            "ADMIN_ACCESS":     "KB-06",
            "GUEST_WIFI":       "KB-07",
            "ONBOARDING":       "KB-08",
            "SECURITY_INCIDENT": "KB-09",
        }
        kb_id = mapping.get(intent)
        return self.get_by_id(kb_id) if kb_id else None

    def search(self, message: str, top_k: int = 1) -> list[PolicyMatch]:
        """Keyword-based relevance scoring — returns top_k matches."""
        msg_lower = message.lower()
        scored: list[tuple[dict, float]] = []

        for policy in self._policies:
            keywords: list[str] = policy.get("keywords", [])
            hits = sum(1 for kw in keywords if kw.lower() in msg_lower)
            if hits > 0:
                relevance = min(hits / max(len(keywords), 1), 1.0)
                scored.append((policy, relevance))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [PolicyMatch(p, r) for p, r in scored[:top_k]]

