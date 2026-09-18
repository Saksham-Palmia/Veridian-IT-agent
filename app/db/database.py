"""SQLAlchemy database setup — engine, session factory, and table initialisation."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # required for SQLite
    echo=settings.debug,
)

# Enable WAL mode for SQLite — better concurrent read performance
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables and seed data on first run."""
    # Import models to register them with Base metadata
    from app.models import employee, conversation, request, ticket, audit, notification  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    _seed_employees()
    _seed_requests_and_tickets()


# ── Seeding helpers ───────────────────────────────────────────────────────────

def _seed_employees() -> None:
    from app.models.employee import Employee

    demo_employees = [
        {"employee_id": "EMP-001", "name": "Alice Johnson",  "email": "alice.johnson@veridian-corp.example",  "department": "Engineering",  "role": "Software Engineer",     "employee_type": "full_time"},
        {"employee_id": "EMP-002", "name": "Bob Martinez",   "email": "bob.martinez@veridian-corp.example",   "department": "Marketing",    "role": "Marketing Manager",     "employee_type": "full_time"},
        {"employee_id": "EMP-003", "name": "Carol Williams", "email": "carol.williams@veridian-corp.example", "department": "Operations",   "role": "Operations Analyst",    "employee_type": "full_time"},
        {"employee_id": "EMP-004", "name": "David Chen",     "email": "david.chen@veridian-corp.example",     "department": "Finance",      "role": "Financial Analyst",     "employee_type": "full_time"},
        {"employee_id": "EMP-005", "name": "Emma Davis",     "email": "emma.davis@veridian-corp.example",     "department": "Design",       "role": "UX Designer",           "employee_type": "full_time"},
        {"employee_id": "EMP-006", "name": "Frank Thompson", "email": "frank.thompson@veridian-corp.example", "department": "Sales",        "role": "Sales Executive",       "employee_type": "full_time"},
        {"employee_id": "EMP-007", "name": "Grace Lee",      "email": "grace.lee@veridian-corp.example",      "department": "Engineering",  "role": "Senior DBA",            "employee_type": "full_time"},
        {"employee_id": "EMP-008", "name": "Henry Wilson",   "email": "henry.wilson@veridian-corp.example",   "department": "HR",           "role": "HR Business Partner",   "employee_type": "full_time"},
        {"employee_id": "EMP-009", "name": "Iris Brown",     "email": "iris.brown@veridian-corp.example",     "department": "Legal",        "role": "Legal Counsel",         "employee_type": "full_time"},
        {"employee_id": "EMP-010", "name": "James Taylor",   "email": "james.taylor@veridian-corp.example",   "department": "Engineering",  "role": "DevOps Contractor",     "employee_type": "contractor"},
        {
            "employee_id": "EMP-001",
            "name": "Alice Johnson",
            "email": "alice.johnson@veridian-corp.example",
            "department": "Engineering",
            "role": "Software Engineer",
            "employee_type": "full_time",
        },
        {
            "employee_id": "EMP-002",
            "name": "James Taylor",
            "email": "james.taylor@veridian-corp.example",
            "department": "Engineering",
            "role": "DevOps Contractor",
            "employee_type": "contractor",
        },
    ]

    with SessionLocal() as db:
        existing = db.query(Employee).count()
        if existing == 0:
            for emp_data in demo_employees:
        target_ids = {e["employee_id"] for e in demo_employees}
        db.query(Employee).filter(Employee.employee_id.notin_(target_ids)).delete(synchronize_session=False)
        for emp_data in demo_employees:
            existing = db.query(Employee).filter(Employee.employee_id == emp_data["employee_id"]).first()
            if not existing:
                db.add(Employee(**emp_data))
            db.commit()
            logger.info("Seeded %d demo employees.", len(demo_employees))
            else:
                for k, v in emp_data.items():
                    setattr(existing, k, v)
        db.commit()
        logger.info("Seeded %d demo employees (reduced to 2).", len(demo_employees))


def _seed_requests_and_tickets() -> None:
    from app.models.request import Request, RequestStatus
    from app.models.ticket import Ticket, TicketStatus

    data_dir = Path(__file__).parent.parent.parent / "data"

    with SessionLocal() as db:
        req_count = db.query(Request).count()
        if req_count == 0:
            seed_requests_path = data_dir / "seed_requests.json"
            if seed_requests_path.exists():
                seed_requests = json.loads(seed_requests_path.read_text())
                for r in seed_requests:
                    db.add(Request(
                        request_id=r["request_id"],
                        employee_id=r["employee_id"],
                        employee_name=r["employee_name"],
                        message=r["message"],
                        category=r["category"],
                        status=r["status"],
                        risk=r["risk"],
                        intent=r.get("intent"),
                        source_policy=r.get("source_policy"),
                        ticket_id=r.get("ticket_id"),
                    ))
                db.commit()
                logger.info("Seeded %d historical requests.", len(seed_requests))

        ticket_count = db.query(Ticket).count()
        if ticket_count == 0:
            seed_tickets_path = data_dir / "seed_tickets.json"
            if seed_tickets_path.exists():
                seed_tickets = json.loads(seed_tickets_path.read_text())
                for t in seed_tickets:
                    db.add(Ticket(
                        ticket_id=t["ticket_id"],
                        request_id=t["request_id"],
                        employee_id=t["employee_id"],
                        category=t["category"],
                        description=t["description"],
                        risk=t["risk"],
                        status=t["status"],
                        assigned_team=t["assigned_team"],
                        source_policy=t["source_policy"],
                        notification_sent=t.get("notification_sent", False),
                    ))
                db.commit()
                logger.info("Seeded %d historical tickets.", len(seed_tickets))

