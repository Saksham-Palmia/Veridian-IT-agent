"""Policies API — returns all KB policy entries."""

from fastapi import APIRouter
from app.schemas.common import ApiResponse
from app.services.policy_service import PolicyService

router = APIRouter(prefix="/api/policies", tags=["policies"])


@router.get("", response_model=ApiResponse[list])
def list_policies():
    """Returns all Veridian Corp knowledge base policies."""
    service = PolicyService()
    return ApiResponse.ok(service.get_all())

