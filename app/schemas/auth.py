"""Auth Pydantic schemas."""
from pydantic import BaseModel


class DemoLoginRequest(BaseModel):
    employee_id: str
    employee_id: str | None = None
    email: str | None = None
    provider: str = "email"  # email | google


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee_id: str
    name: str
    email: str
    employee_type: str


class EmployeeInfo(BaseModel):
    employee_id: str
    name: str
    email: str
    department: str | None = None
    role: str | None = None
    employee_type: str = "full_time"

