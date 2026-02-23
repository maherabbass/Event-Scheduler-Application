# Event Scheduler Application

A full-stack event management platform built with **FastAPI**, **PostgreSQL**, and **React 18**.

Users can create events, RSVP, invite others by email, and get AI-powered invitation suggestions — all secured with Google and GitHub OAuth.

**Live URLs**
- Backend API: https://event-scheduler-api-ew.a.run.app
- Frontend: https://event-scheduler-application.vercel.app
- API docs: https://event-scheduler-api-ew.a.run.app/docs

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, SQLAlchemy (async), PostgreSQL, Alembic |
| Auth | JWT, Google OAuth, GitHub OAuth |
| AI | OpenAI `gpt-4o-mini` with deterministic fallback |
| Frontend | React 18, Vite, TypeScript |
| Deployment | Cloud Run (backend), Vercel (frontend) |

---

## Local Setup

### Prerequisites
- Python 3.10+
- Node 20+
- Docker (for PostgreSQL)

### 1. Clone and configure

```bash
cp .env.example .env
# Fill in .env with your secrets (OAuth keys, etc.)
```

### 2. Start PostgreSQL

```bash
docker-compose up -d
```

### 3. Install backend dependencies

```bash
pip install -e ".[dev]"
```

### 4. Run migrations and seed

```bash
alembic upgrade head
python -m app.db.seed
```

### 5. Start the backend

```bash
uvicorn app.main:app --reload
# API at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
```

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
# App at http://localhost:5173
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | JWT signing secret |
| `DATABASE_URL` | PostgreSQL async connection string |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth app credentials |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth app credentials |
| `FRONTEND_URL` | Frontend origin (for CORS + OAuth redirect) |
| `BACKEND_URL` | Backend origin (for OAuth callback URI) |
| `OPENAI_API_KEY` | Optional — AI features fall back gracefully without it |

See `.env.example` for the full list.

---

## Roles & Permissions

| Role | Capabilities |
|---|---|
| **Admin** | Full access including user management |
| **Organizer** | Create / edit / delete own events; send invitations; use AI suggestions |
| **Member** | Browse events; RSVP |

New OAuth users start as **Member**. An Admin promotes them via `PATCH /api/v1/admin/users/{id}/role`.

---

## API Endpoints

Base path: `/api/v1`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/events` | Public | List / search events |
| GET | `/events/{id}` | Public | Event detail |
| POST | `/events` | Organizer / Admin | Create event |
| PUT | `/events/{id}` | Organizer / Admin | Update event |
| DELETE | `/events/{id}` | Organizer / Admin | Delete event |
| POST | `/events/{id}/rsvp` | Authenticated | RSVP to event |
| GET | `/events/{id}/attendees` | Authenticated | List attendees |
| POST | `/events/{id}/invite` | Organizer / Admin | Send invitation |
| POST | `/events/{id}/ai/suggest-invitees` | Organizer / Admin | AI invite suggestions |
| GET | `/invitations/accept/{token}` | Public | Accept invitation |
| GET | `/api/v1/auth/login/{provider}` | Public | Start OAuth (google / github) |
| GET | `/api/v1/auth/me` | Authenticated | Current user profile |
| GET | `/api/v1/admin/users` | Admin | List all users |
| PATCH | `/api/v1/admin/users/{id}/role` | Admin | Change user role |

Full interactive docs at `http://localhost:8000/docs`. The exported OpenAPI spec is at [`docs/swagger.json`](docs/swagger.json).

---

## OAuth Setup

Register your OAuth apps with the callback URL:

```
{BACKEND_URL}/api/v1/auth/callback/{provider}
```

- **Google**: [console.cloud.google.com](https://console.cloud.google.com) → APIs & Services → Credentials
- **GitHub**: Settings → Developer settings → OAuth Apps

---

## AI Features

`POST /events/{id}/ai/suggest-invitees` analyses the event's title, description, and tags against the RSVP history of all registered users and returns a ranked list with a personalised invitation message per user.

- **Primary**: `gpt-4o-mini` (requires `OPENAI_API_KEY`)
- **Fallback**: pure Python tag-overlap scoring — works with no API key

---

## Deployment

Infrastructure mirrors the [Library Management System](https://github.com/maherabbass/Library-Management-System) project:

- **Backend**: Cloud Run + Cloud SQL (PostgreSQL) + Artifact Registry
- **Frontend**: Vercel
- **Auth**: Workload Identity Federation (keyless GCP auth from GitHub Actions)

Push to `main` triggers both pipelines automatically.

### Required GitHub Secrets

```
WIF_PROVIDER          GCP_SERVICE_ACCOUNT    DATABASE_URL
SECRET_KEY            GOOGLE_CLIENT_ID       GOOGLE_CLIENT_SECRET
GH_CLIENT_ID          GH_CLIENT_SECRET       FRONTEND_URL
BACKEND_URL           OPENAI_API_KEY         VERCEL_TOKEN
VERCEL_ORG_ID         VERCEL_PROJECT_ID      VITE_API_URL
```

---

## Development Commands

```bash
# Linting
ruff check .
black .

# Tests
pytest

# New migration (after model changes)
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```
