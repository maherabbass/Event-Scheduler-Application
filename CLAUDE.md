# Event Scheduler Application — Authoritative Build Specification

## Purpose

This document defines the complete implementation rules for building the Event Scheduler Application using the same architecture and infrastructure patterns as the Library Management System.
URL for the Library Management System Public Repository that you should re-use code and structure from: https://github.com/maherabbass/Library-Management-System

Claude must:

- Follow this document strictly.
- Implement phase-by-phase.
- Reuse infrastructure exactly from the other repository.
- Modify only domain-specific layers.
- Avoid architectural drift.
- Avoid speculative refactoring.

This file is the single source of truth.

---

## 1. Architecture Overview

### Backend

- FastAPI
- SQLAlchemy (async)
- PostgreSQL
- Alembic
- JWT Authentication
- Google + GitHub OAuth
- Cloud Run deployment

### Frontend

- React 18
- Vite
- TypeScript
- Vercel deployment

### AI

- OpenAI
- Deterministic fallbacks required for all AI features

---

## 2. Core Principle

Infrastructure is reused. Domain logic is new.

Only these layers are domain-specific:

- `app/models/`
- `app/schemas/`
- `app/services/`
- `app/api/v1/events.py`
- Frontend event pages

All other infrastructure must be copied from the Library project unchanged.

---

## 3. Application Overview

Users can:

- Create events
- RSVP to events
- Invite users by email
- Search events by title, date, location, tags, and status
- Use AI to get smart invitation suggestions with personalised messages

Deployment target:

- Cloud Run (backend)
- Vercel (frontend)

---

## 4. Role System

| Library Role | Event Role |
|---|---|
| ADMIN | ADMIN |
| LIBRARIAN | ORGANIZER |
| MEMBER | MEMBER |

Required change: replace `UserRole.LIBRARIAN` with `UserRole.ORGANIZER`. No other auth logic changes.

---

## 5. Files to Copy Without Modification

Copy these exactly from the Library project:

- `Dockerfile`
- `docker-compose.yml`
- `alembic.ini`
- `app/db/base.py`
- `app/db/session.py`
- `app/auth/jwt.py`
- `app/auth/oauth.py`
- `app/db/__init__.py`
- `app/models/__init__.py`
- `app/schemas/__init__.py`
- `app/services/__init__.py`
- `app/api/__init__.py`
- `app/api/v1/__init__.py`
- `frontend/src/main.tsx`
- `frontend/package.json`
- `frontend/vercel.json`
- `frontend/tsconfig.json`
- `frontend/vite-env.d.ts`

---

## 6. Files With Small Controlled Edits

These must remain minimal changes (< 10 lines each):

- `pyproject.toml` → `name = "event-scheduler"`
- `app/auth/dependencies.py` → `LIBRARIAN` → `ORGANIZER`
- `migrations/env.py` → import Event models
- `frontend/index.html` → update title
- `.github/workflows/deploy.yml` → update project constants
- `.github/workflows/deploy-frontend.yml` → update fallback backend URL

No structural modifications allowed.

---

## 7. Domain Models

### UserRole

```python
class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    ORGANIZER = "ORGANIZER"
    MEMBER = "MEMBER"
```

### EventStatus

```python
class EventStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"
```

### RSVPStatus

```python
class RSVPStatus(str, enum.Enum):
    UPCOMING = "UPCOMING"
    ATTENDING = "ATTENDING"
    MAYBE = "MAYBE"
    DECLINED = "DECLINED"
```

### Event

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `title` | str | Required |
| `description` | str | Optional |
| `location` | str | Optional |
| `start_datetime` | datetime | Timezone-aware, required |
| `end_datetime` | datetime | Optional |
| `created_by` | UUID | FK → `users.id` |
| `tags` | ARRAY[str] | |
| `status` | EventStatus | DRAFT \| PUBLISHED \| CANCELLED |
| `created_at` | datetime | Server default |
| `updated_at` | datetime | Server default + onupdate |

### EventAttendee

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `event_id` | UUID | FK → `events.id`, cascade delete |
| `user_id` | UUID | FK → `users.id` |
| `rsvp_status` | RSVPStatus | |
| `responded_at` | datetime | Nullable |
| `created_at` | datetime | Server default |

Constraint: `UNIQUE(event_id, user_id)`

### Invitation

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Primary key |
| `event_id` | UUID | FK → `events.id`, cascade delete |
| `invited_by` | UUID | FK → `users.id` |
| `invited_email` | str | Required |
| `token` | str | Unique, 32-char random string |
| `accepted` | bool | Default `False` |
| `created_at` | datetime | Server default |

Constraint: `UNIQUE(event_id, invited_email)`

---

## 8. Database Migration

Create a single initial migration that defines:

- `userrole` enum
- `eventstatus` enum
- `rsvpstatus` enum
- `users` table
- `events` table
- `event_attendees` table
- `invitations` table

Enums must be explicitly created in the migration file.

---

## 9. Seed Script

Implement idempotent async seed.

Users to create:

| Email | Role |
|---|---|
| `admin@example.com` | ADMIN |
| `organizer@example.com` | ORGANIZER |
| `member@example.com` | MEMBER |

Also insert:

- 10–15 events
- Sample RSVPs

Seed must not duplicate existing records.

---

## 10. Services Layer

### `event.py`

- `list_events` — ILIKE search on title/location/description, date range filtering, tag filtering, status filtering, pagination
- `create_event`
- `update_event` — enforce ownership
- `delete_event` — enforce ownership

### `attendee.py`

- `upsert_rsvp` — `INSERT ON CONFLICT UPDATE`
- `get_attendees`
- `get_user_rsvp`

### `invitation.py`

- `create_invitation` — secure token generation
- `accept_invitation` — validate token, create RSVP, mark accepted

### `ai.py`

**Smart Invitation Targeting**

When an organizer is about to send invitations for an event, AI analyses the event's title, description, tags, and category against the RSVP history of all registered users on the platform. It returns a ranked list of users most likely to be interested, along with a short personalised invitation message for each suggested user.

Steps:
1. Load the event details and the RSVP history of all users (events they attended, categories they prefer)
2. Score each user by relevance to this event (category match, tag overlap, past attendance rate)
3. Return the top N suggested users with a drafted invitation message per user
4. Organizer reviews and selects who to invite — invitation is then sent via the normal `create_invitation` flow

- Primary: `gpt-4o-mini` — receives event details + user history summaries, returns ranked suggestions + messages as structured JSON
- Fallback: pure Python scoring using tag/category overlap counts; generic invitation message template filled with event title and date

Must work without `OPENAI_API_KEY`.

---

## 11. API Endpoints

Base path: `/api/v1`

### Public

| Method | Path | Description |
|---|---|---|
| GET | `/events` | List/search events |
| GET | `/events/{id}` | Get event detail |
| GET | `/invitations/accept/{token}` | Accept invitation |

### Authenticated

| Method | Path | Description |
|---|---|---|
| POST | `/events` | Create event |
| PUT | `/events/{id}` | Update event |
| DELETE | `/events/{id}` | Delete event |
| POST | `/events/{id}/rsvp` | RSVP to event |
| GET | `/events/{id}/attendees` | List attendees |
| POST | `/events/{id}/invite` | Send invitation |
| POST | `/events/{id}/ai/suggest-invitees` | AI-ranked invite suggestions + draft messages |

---

## 12. RBAC Rules

- `ORGANIZER` — can create events; can edit/delete only their own events.
- `ADMIN` — can edit/delete any event.
- `MEMBER` — cannot create, edit, or delete events.
- RSVP requires authentication.
- Invitations require `ORGANIZER` or `ADMIN`.

---

## 13. Event Visibility Rules

- `DRAFT` — visible only to creator and ADMIN.
- `PUBLISHED` — visible to all authenticated users.
- `CANCELLED` — remains visible but flagged.

---

## 14. Frontend Pages

Build in this order:

1. Login
2. AuthCallback
3. Events list
4. EventDetail
5. CreateEditEvent
6. Admin

Frontend must mirror Library architecture.

---

## 15. Deployment

Same infrastructure pattern as Library project:

- Cloud Run
- Cloud SQL
- Artifact Registry
- Workload Identity Federation
- Vercel

Required secrets:

| Secret | Purpose |
|---|---|
| `WIF_PROVIDER` | Workload Identity Federation |
| `GCP_SERVICE_ACCOUNT` | GCP deployment |
| `DATABASE_URL` | PostgreSQL connection |
| `SECRET_KEY` | JWT signing |
| `GOOGLE_CLIENT_ID` | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | Google OAuth |
| `GH_CLIENT_ID` | GitHub OAuth |
| `GH_CLIENT_SECRET` | GitHub OAuth |
| `FRONTEND_URL` | CORS + redirects |
| `BACKEND_URL` | Frontend API target |
| `OPENAI_API_KEY` | AI features (optional) |
| `VERCEL_TOKEN` | Frontend deploy |
| `VERCEL_ORG_ID` | Frontend deploy |
| `VERCEL_PROJECT_ID` | Frontend deploy |
| `VITE_API_URL` | Frontend env var |

OAuth callback URLs must be updated for the new backend service.

---

## 16. Implementation Phases

Execute sequentially — no skipping phases:

| Phase | Name |
|---|---|
| 0 | Bootstrap |
| 1 | DB Schema |
| 2 | Events CRUD + Search |
| 3 | Auth + RBAC |
| 4 | RSVP + Invitations |
| 5 | AI Features |
| 6 | Deployment |
| 7 | Frontend |

---

## 17. Verification Commands

### Backend

```bash
uvicorn app.main:app --reload
pytest
ruff check .
black .
alembic upgrade head
python -m app.db.seed
```

### Frontend

```bash
npm run dev
npm run build
```

---

## 18. Non-Negotiable Constraints

Claude must not:

- Introduce new frameworks
- Change deployment architecture
- Modify authentication structure
- Remove AI fallbacks
- Refactor infrastructure unnecessarily

---

## Final Instruction

Build the Event Scheduler Application strictly according to this document.

- Follow phases in order.
- Reuse infrastructure exactly.
- Implement only specified domain changes.
- Avoid architectural drift.
