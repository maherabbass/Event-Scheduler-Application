"""Events CRUD + search tests.

Schema-only tests run without a DB.
DB-dependent tests skip automatically if Postgres is unavailable.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from app.schemas.event import EventCreate, EventUpdate

# ---------------------------------------------------------------------------
# Schema-only tests (no DB required)
# ---------------------------------------------------------------------------


def test_event_create_requires_title() -> None:
    with pytest.raises(ValidationError):
        EventCreate(start_datetime=datetime.now(timezone.utc))  # type: ignore[call-arg]


def test_event_create_requires_start_datetime() -> None:
    with pytest.raises(ValidationError):
        EventCreate(title="My Event")  # type: ignore[call-arg]


def test_event_update_all_optional() -> None:
    update = EventUpdate()
    assert update.title is None
    assert update.status is None
    assert update.tags is None


def test_event_create_defaults() -> None:
    ev = EventCreate(title="Test", start_datetime=datetime.now(timezone.utc))
    assert ev.status.value == "DRAFT"
    assert ev.tags == []
    assert ev.description is None


# ---------------------------------------------------------------------------
# DB-dependent tests (skip if Postgres is unavailable)
# ---------------------------------------------------------------------------


def _future(days: int = 7) -> str:
    dt = datetime.now(timezone.utc) + timedelta(days=days)
    return dt.isoformat()


EVENT_PAYLOAD = {
    "title": "Test Conference",
    "description": "A test event description.",
    "location": "Test City",
    "start_datetime": _future(7),
    "end_datetime": _future(8),
    "tags": ["testing", "python"],
    "status": "PUBLISHED",
}


@pytest.mark.asyncio
async def test_list_events_public(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "pages" in data


@pytest.mark.asyncio
async def test_list_events_pagination_params(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/events?page=1&page_size=5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5


@pytest.mark.asyncio
async def test_list_events_search_query(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/events?query=conference")
    assert resp.status_code == 200
    assert "items" in resp.json()


@pytest.mark.asyncio
async def test_list_events_filter_status(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/events?status=PUBLISHED")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["status"] == "PUBLISHED" for item in items)


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/events/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_event_requires_auth(client: AsyncClient) -> None:
    # client fixture uses DB override but no auth override — no token provided
    resp = await client.post("/api/v1/events", json=EVENT_PAYLOAD)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_and_get_event(client: AsyncClient, db) -> None:
    """Create via service directly, then fetch via API."""
    import uuid as _uuid

    from app.models.user import User, UserRole
    from app.services.event import create_event
    from app.schemas.event import EventCreate

    # Insert a throwaway organizer directly into the DB session
    organizer = User(
        id=_uuid.uuid4(),
        email=f"org-{_uuid.uuid4().hex[:6]}@test.com",
        name="Test Organizer",
        role=UserRole.ORGANIZER,
    )
    db.add(organizer)
    await db.flush()

    data = EventCreate(
        title="Created Event",
        start_datetime=datetime.now(timezone.utc) + timedelta(days=10),
        status="PUBLISHED",  # type: ignore[arg-type]
        tags=["test"],
    )
    event = await create_event(db, data, organizer.id)

    resp = await client.get(f"/api/v1/events/{event.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["title"] == "Created Event"
    assert body["status"] == "PUBLISHED"
    assert "test" in body["tags"]


@pytest.mark.asyncio
async def test_rsvp_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        f"/api/v1/events/{uuid.uuid4()}/rsvp",
        json={"rsvp_status": "ATTENDING"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_attendees_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(f"/api/v1/events/{uuid.uuid4()}/attendees")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invite_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        f"/api/v1/events/{uuid.uuid4()}/invite",
        json={"invited_email": "someone@example.com"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_accept_invitation_invalid_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/invitations/accept/invalid-token-xyz")
    assert resp.status_code == 404
