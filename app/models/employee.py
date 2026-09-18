"""Employee ORM model."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from app.db.database import Base


class Employee(Base):
    __tablename__ = "employees"

    employee_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    department = Column(String, nullable=True)
    role = Column(String, nullable=True)
    employee_type = Column(String, default="full_time")  # full_time | contractor
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

