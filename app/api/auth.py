"""Auth API — demo login endpoint."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.auth import DemoLoginRequest, TokenResponse
from app.schemas.common import ApiResponse
from app.security.identity_service import DemoIdentityProvider, create_access_token
from app.security.identity_service import DemoIdentityProvider, GoogleIdentityProvider, create_access_token
from app.repositories.repositories import EmployeeRepository
from app.core.exceptions import AuthenticationError

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/demo-login", response_model=ApiResponse[TokenResponse])
def demo_login(request: DemoLoginRequest, db: Session = Depends(get_db)):
    """Authenticate as a demo employee — no external OAuth required."""
    """Authenticate as a demo employee via email, employee_id, or simulated Google OAuth."""
    identifier = request.email or request.employee_id
    if not identifier:
        raise HTTPException(status_code=400, detail="Either email or employee_id must be provided.")

    try:
        provider = DemoIdentityProvider(db)
        identity = provider.authenticate(request.employee_id)
        if request.provider == "google":
            provider = GoogleIdentityProvider(db)
        else:
            provider = DemoIdentityProvider(db)

        identity = provider.authenticate(identifier)
        token = create_access_token(identity)
        return ApiResponse.ok(TokenResponse(
            access_token=token,
            employee_id=identity["employee_id"],
            name=identity["name"],
            email=identity["email"],
            employee_type=identity.get("employee_type", "full_time"),
        ))
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail=str(exc))


@router.get("/employees", response_model=ApiResponse[list])
def list_employees(db: Session = Depends(get_db)):
    """List all demo employees for the login picker."""
    repo = EmployeeRepository(db)
    employees = repo.list_all()
    return ApiResponse.ok([
        {
            "employee_id": e.employee_id,
            "name": e.name,
            "email": e.email,
            "department": e.department,
            "role": e.role,
            "employee_type": e.employee_type,
        }
        for e in employees
    ])

