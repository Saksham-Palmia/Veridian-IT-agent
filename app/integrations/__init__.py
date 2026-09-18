"""integrations package"""
"""External service integrations (LLM, email, ticketing, directory)."""

from app.integrations.llm import LLMClient

__all__ = ["LLMClient"]
