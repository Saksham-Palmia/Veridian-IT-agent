"""SQLAlchemy database setup — engine, session factory, and table initialisation."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

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
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


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
    # Import models to register them with Base metadata.
    from app.models import (  # noqa: F401
        audit,
        conversation,
        employee,
        notification,
        request,
        ticket,
    )

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")

    _seed_employees()
    _seed_requests_and_tickets()


# ── Seeding helpers ───────────────────────────────────────────────────────────


def _seed_employees() -> None:
    """Seed the demo employees and keep existing records in sync."""
    from app.models.employee import Employee

    # Keep this list unique by employee_id.
    demo_employees = [
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
        target_ids = {emp["employee_id"] for emp in demo_employees}

        # Remove employees that are no longer part of the demo seed data.
        db.query(Employee).filter(
            Employee.employee_id.notin_(target_ids)
        ).delete(synchronize_session=False)

        # Insert new employees or update existing ones.
        for emp_data in demo_employees:
            existing = (
                db.query(Employee)
                .filter(Employee.employee_id == emp_data["employee_id"])
                .first()
            )

            if existing is None:
                db.add(Employee(**emp_data))
            else:
                for key, value in emp_data.items():
                    setattr(existing, key, value)

        db.commit()

        logger.info(
            "Seeded %d demo employees.",
            len(demo_employees),
        )


def _seed_requests_and_tickets() -> None:
    """Seed historical requests and tickets from JSON files if tables are empty."""
    from app.models.request import Request
    from app.models.ticket import Ticket

    data_dir = Path(__file__).parent.parent.parent / "data"

    with SessionLocal() as db:
        # ── Historical requests ──────────────────────────────────────────────
        req_count = db.query(Request).count()

        if req_count == 0:
            seed_requests_path = data_dir / "seed_requests.json"

            if seed_requests_path.exists():
                seed_requests = json.loads(
                    seed_requests_path.read_text(encoding="utf-8")
                )

                for r in seed_requests:
                    db.add(
                        Request(
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
                        )
                    )

                db.commit()
                logger.info(
                    "Seeded %d historical requests.",
                    len(seed_requests),
                )

        # ── Historical tickets ───────────────────────────────────────────────
        ticket_count = db.query(Ticket).count()

        if ticket_count == 0:
            seed_tickets_path = data_dir / "seed_tickets.json"

            if seed_tickets_path.exists():
                seed_tickets = json.loads(
                    seed_tickets_path.read_text(encoding="utf-8")
                )

                for t in seed_tickets:
                    db.add(
                        Ticket(
                            ticket_id=t["ticket_id"],
                            request_id=t["request_id"],
                            employee_id=t["employee_id"],
                            category=t["category"],
                            description=t["description"],
                            risk=t["risk"],
                            status=t["status"],
                            assigned_team=t["assigned_team"],
                            source_policy=t["source_policy"],
                            notification_sent=t.get(
                                "notification_sent",
                                False,
                            ),
                        )
                    )

                db.commit()
                logger.info(
                    "Seeded %d historical tickets.",
                    len(seed_tickets),
                )
