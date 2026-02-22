# Testing Guide

This document covers manual and automated testing for the Event Scheduler Application.

---

## Automated Tests

```bash
pip install -e ".[dev]"
pytest
```

Tests skip automatically when PostgreSQL is unavailable — no DB needed for most checks.

### Test files

| File | What it covers |
|---|---|
| `test_health.py` | `/health` smoke test (no DB) |
| `test_auth.py` | JWT validation, OAuth error cases (no DB) |
| `test_db.py` | DB connectivity, enum values (DB optional) |
| `test_events.py` | Events CRUD, search, schema validation |
| `test_rbac.py` | Role enforcement — 401/403 boundary cases |
| `test_ai.py` | AI fallback logic, suggestion endpoint |

---

## Manual Test Scenarios

Start the stack first:

```bash
docker-compose up -d
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload
```

### 1. Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "version": "0.1.0"}
```

### 2. Public Event Browsing

```bash
# List all published events
curl http://localhost:8000/api/v1/events

# Search by title
curl "http://localhost:8000/api/v1/events?query=python"

# Filter by location
curl "http://localhost:8000/api/v1/events?location=online"

# Filter by tags
curl "http://localhost:8000/api/v1/events?tags=ai&tags=cloud"

# Filter by status
curl "http://localhost:8000/api/v1/events?status=PUBLISHED"

# Date range
curl "http://localhost:8000/api/v1/events?date_from=2026-03-01&date_to=2026-12-31"

# Pagination
curl "http://localhost:8000/api/v1/events?page=1&page_size=5"

# Expected: EventListResponse with items, total, page, page_size, pages
```

### 3. Authentication

```bash
# Open in browser — completes OAuth flow and redirects with ?token=<jwt>
open http://localhost:8000/api/v1/auth/login/google
open http://localhost:8000/api/v1/auth/login/github

# Store the token
TOKEN="<jwt from redirect>"

# Verify token
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/auth/me
# Expected: user profile JSON with role, email, name

# Invalid token
curl -H "Authorization: Bearer bad.token.here" http://localhost:8000/api/v1/auth/me
# Expected: 401

# Unsupported provider
curl http://localhost:8000/api/v1/auth/login/twitter
# Expected: 400 Unsupported provider
```

### 4. RSVP Flow (authenticated)

```bash
EVENT_ID="<uuid from event list>"

# RSVP attending
curl -X POST "http://localhost:8000/api/v1/events/$EVENT_ID/rsvp" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rsvp_status": "ATTENDING"}'
# Expected: 200 with attendee record

# Update to maybe
curl -X POST "http://localhost:8000/api/v1/events/$EVENT_ID/rsvp" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rsvp_status": "MAYBE"}'
# Expected: 200 — same record updated (upsert)

# View attendees
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/events/$EVENT_ID/attendees"
# Expected: array of attendees with name, email, rsvp_status

# RSVP without auth
curl -X POST "http://localhost:8000/api/v1/events/$EVENT_ID/rsvp" \
  -H "Content-Type: application/json" \
  -d '{"rsvp_status": "ATTENDING"}'
# Expected: 401
```

### 5. RBAC Boundary Tests

```bash
# Member token — create event (should fail)
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer $MEMBER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "start_datetime": "2027-01-01T10:00:00Z"}'
# Expected: 403

# Member token — admin users list (should fail)
curl -H "Authorization: Bearer $MEMBER_TOKEN" http://localhost:8000/api/v1/admin/users
# Expected: 403

# No token — admin users list
curl http://localhost:8000/api/v1/admin/users
# Expected: 401
```

### 6. Organizer Flows

Use an Organizer or Admin token (`organizer@example.com` after seeding, promoted via Admin).

```bash
# Create event
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "New Meetup",
    "description": "A test event",
    "location": "Online",
    "start_datetime": "2027-06-01T18:00:00Z",
    "tags": ["python", "fastapi"],
    "status": "PUBLISHED"
  }'
# Expected: 201 with event JSON

EVENT_ID="<id from above>"

# Update event
curl -X PUT "http://localhost:8000/api/v1/events/$EVENT_ID" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "CANCELLED"}'
# Expected: 200

# Delete event
curl -X DELETE "http://localhost:8000/api/v1/events/$EVENT_ID" \
  -H "Authorization: Bearer $ORG_TOKEN"
# Expected: 204
```

### 7. Invitations

```bash
EVENT_ID="<published event uuid>"

# Send invitation
curl -X POST "http://localhost:8000/api/v1/events/$EVENT_ID/invite" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invited_email": "guest@example.com"}'
# Expected: 201 with invitation token

TOKEN_VAL="<token from response>"

# Accept invitation (public)
curl "http://localhost:8000/api/v1/invitations/accept/$TOKEN_VAL"
# Expected: {"message": "Invitation accepted successfully", "event_id": "..."}

# Duplicate invitation
curl -X POST "http://localhost:8000/api/v1/events/$EVENT_ID/invite" \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"invited_email": "guest@example.com"}'
# Expected: 409 Conflict

# Invalid token
curl "http://localhost:8000/api/v1/invitations/accept/invalid-token"
# Expected: 404
```

### 8. AI Invite Suggestions

```bash
EVENT_ID="<published event uuid>"

# With OPENAI_API_KEY set — calls gpt-4o-mini
curl -X POST "http://localhost:8000/api/v1/events/$EVENT_ID/ai/suggest-invitees" \
  -H "Authorization: Bearer $ORG_TOKEN"
# Expected: {"suggestions": [{user_id, name, email, score, invitation_message}, ...]}

# Without OPENAI_API_KEY — deterministic fallback
# Expected: same response shape, source is tag-overlap scoring

# Member token — forbidden
curl -X POST "http://localhost:8000/api/v1/events/$EVENT_ID/ai/suggest-invitees" \
  -H "Authorization: Bearer $MEMBER_TOKEN"
# Expected: 403

# Limit results
curl -X POST "http://localhost:8000/api/v1/events/$EVENT_ID/ai/suggest-invitees?top_n=3" \
  -H "Authorization: Bearer $ORG_TOKEN"
# Expected: at most 3 suggestions
```

### 9. Admin Flows

```bash
# List all users
curl -H "Authorization: Bearer $ADMIN_TOKEN" http://localhost:8000/api/v1/admin/users

# Promote member to organizer
USER_ID="<uuid>"
curl -X PATCH "http://localhost:8000/api/v1/admin/users/$USER_ID/role" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "ORGANIZER"}'
# Expected: 200 with updated user

# Invalid role value
curl -X PATCH "http://localhost:8000/api/v1/admin/users/$USER_ID/role" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"role": "SUPERUSER"}'
# Expected: 422
```

### 10. Event Visibility Rules

```bash
# DRAFT event — visible to creator, not to public
curl "http://localhost:8000/api/v1/events?status=DRAFT"
# As public (no token): Expected — empty or only PUBLISHED events
# As creator (with token): Expected — their DRAFT events appear

# CANCELLED event — visible to all authenticated
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/events?status=CANCELLED"
# Expected: cancelled events listed
```

### 11. Input Validation

```bash
# Missing required field
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "No datetime"}'
# Expected: 422 Unprocessable Entity

# Invalid status value
curl -X POST http://localhost:8000/api/v1/events \
  -H "Authorization: Bearer $ORG_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "T", "start_datetime": "2027-01-01T10:00:00Z", "status": "INVALID"}'
# Expected: 422

# Invalid UUID path param
curl http://localhost:8000/api/v1/events/not-a-uuid
# Expected: 422

# Page size out of bounds
curl "http://localhost:8000/api/v1/events?page_size=999"
# Expected: 422
```

---

## Seed Accounts

After running `python -m app.db.seed`:

| Email | Role | Password |
|---|---|---|
| `admin@example.com` | ADMIN | OAuth only |
| `organizer@example.com` | ORGANIZER | OAuth only |
| `member@example.com` | MEMBER | OAuth only |
| `alice@example.com` | MEMBER | OAuth only |
| `bob@example.com` | MEMBER | OAuth only |

To get a token for a seed user, log in via OAuth with the matching email address, or use the admin panel to promote an account after first OAuth login.
