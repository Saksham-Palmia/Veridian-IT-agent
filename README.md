# Veridian IT Service Agent

An internal IT support agent for **Veridian Corp** employees. Employees sign in, describe an IT problem in a chat interface, and the agent classifies the request, retrieves the relevant company policy, applies deterministic business rules, and either resolves the issue, asks a clarifying question, or escalates it by creating an ITSM ticket and notifying the right support team — with a full audit trail and an admin dashboard for oversight.

## How it works

```
Employee → Sign in → Chat → Agent Orchestrator
                                 │
                    Intent + Entity Extraction
                                 │
                          Policy Retrieval
                                 │
                        Deterministic Rules
                                 │
                          Risk Evaluation
                                 │
              ┌──────────────┬──────────────┬──────────────┐
              │   RESOLVE    │   CLARIFY    │   ESCALATE   │
              └──────────────┴──────────────┴──────────────┘
                                                    │
                                          Create ITSM ticket
                                                    │
                                          Notify support team
                                                    │
                                             Audit trail
                                                    │
                                          Employee response
                                                    │
                                             Admin Dashboard
```

Every response returned to the employee includes the request ID, status, risk level (when relevant), the policy source used, and a ticket ID if one was created.

## Features

- **Employee chat interface** — sign in as a demo employee and submit IT issues in natural language.
- **Agent orchestrator** — intent classification, entity extraction, policy retrieval, and deterministic rule application (`app/agents`, `app/core/rules.py`).
- **LLM integration (optional)** — uses Google Gemini when a `GEMINI_API_KEY` is configured; falls back to deterministic logic when it isn't (`app/integrations/llm.py`).
- **ITSM ticketing** — automatically creates/updates tickets when a request needs human intervention (`app/services/itsm_service.py`).
- **Notifications** — informs the responsible support team on escalation (`app/services/notification_service.py`), with SMTP support that falls back to console logging when unconfigured.
- **Audit trail** — every step of a request's lifecycle is recorded (`app/services/audit_service.py`, `app/api/audit.py`).
- **Policy knowledge base** — company policies loaded from `data/policies.json` and matched against requests (`app/services/policy_service.py`).
- **Pluggable identity layer** — a `DemoIdentityProvider` for local use, with room for Google/Microsoft/Slack identity providers (`app/security/identity_service.py`).
- **Admin dashboard** — a separate frontend for monitoring requests, tickets, and audit history.
- **Structured JSON API** — built with FastAPI, with typed request/response schemas (`app/schemas`).

## Tech stack

- **Backend:** FastAPI, SQLAlchemy, Pydantic, JWT-based auth (`python-jose`), SQLite
- **Frontend:** Static HTML/JS (employee UI + admin dashboard), served by FastAPI or Nginx
- **LLM:** Google Gemini (optional — the app runs fully without it)
- **Containerization:** Docker + Docker Compose

## Project structure

```
veridian-it-agent/
├── app/
│   ├── agents/         # Agent orchestrator, prompts, extraction logic
│   ├── api/            # FastAPI routes (auth, chat, requests, tickets, audit, notifications, policies)
│   ├── config/         # Settings, loaded from environment variables
│   ├── core/           # Constants, exceptions, deterministic rules, executor
│   ├── db/             # Database engine/session setup
│   ├── integrations/   # External services (LLM, etc.)
│   ├── models/         # SQLAlchemy ORM models
│   ├── repositories/   # CRUD/data-access layer
│   ├── schemas/        # Pydantic request/response models
│   ├── security/       # Identity providers, JWT auth
│   ├── services/       # Business logic (ITSM, audit, notifications, policy)
│   └── main.py         # FastAPI app entry point
├── frontend/
│   ├── employee/        # Employee chat UI
│   └── admin/           # Admin dashboard
├── data/                 # Seed data — policies, tickets, requests
├── docker-compose.yml
├── Dockerfile            # Backend (also serves frontend statics)
├── frontend/Dockerfile   # Nginx container for the frontend
└── requirements.txt
```

See `architecture.txt` for the reasoning behind the folder layout.

## Getting started

### Option 1: Docker Compose (recommended)

```bash
docker compose up --build
```

This starts two containers:

| Service  | URL                         |
|----------|------------------------------|
| Backend  | http://localhost:8000        |
| Frontend | http://localhost:3000        |

The backend serves its own copy of the frontend too, at `http://localhost:8000/` (employee UI) and `http://localhost:8000/admin` (admin dashboard).

To enable live LLM-based intent extraction, set a Gemini key before starting:

```bash
export GEMINI_API_KEY=your-key-here
docker compose up --build
```

Without a key, the agent runs in deterministic fallback mode.

### Option 2: Run the backend locally

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in values as needed
uvicorn app.main:app --reload --port 8000
```

The app initializes and seeds its SQLite database automatically on startup.

### Login

Use the demo login flow — no external OAuth setup is required:

- `GET /api/auth/employees` — lists available demo employees
- `POST /api/auth/demo-login` — logs in as one of them and returns a JWT

## Configuration

All configuration is read from environment variables (see `app/config/settings.py`). Copy `.env.example` to `.env` and adjust as needed:

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy database URL | `sqlite:///./veridian.db` |
| `JWT_SECRET` | Secret used to sign JWTs | — |
| `JWT_ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime | `480` |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Admin dashboard credentials | — |
| `GEMINI_API_KEY` | Enables LLM-based intent/entity extraction when set | *(empty — fallback mode)* |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USER` / `SMTP_PASSWORD` / `SMTP_FROM` | Optional SMTP config for real email notifications | *(empty — logs to console)* |

> **Note:** `.env` is excluded from version control (see `.gitignore`). Never commit real secrets — use `.env.example` as the template and keep actual credentials local or in your deployment platform's secret manager.

## API overview

| Endpoint | Description |
|---|---|
| `POST /api/auth/demo-login` | Log in as a demo employee |
| `GET /api/auth/employees` | List demo employees |
| `POST /api/chat` | Submit an IT issue to the agent |
| `GET/POST /api/requests` | View/manage structured requests |
| `GET/POST /api/tickets` | View/manage ITSM tickets |
| `GET /api/audit` | View the audit trail |
| `GET /api/notifications` | View notifications sent to support teams |
| `GET /api/policies` | View the policy knowledge base |
| `GET /api/health` | Health check |

Interactive API docs are available at `http://localhost:8000/docs` once the backend is running.

## Testing

```bash
pytest
```

## License

Internal project — no license specified.
