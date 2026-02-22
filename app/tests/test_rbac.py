"""RBAC boundary tests.

No-DB tests: override get_current_user only — never touch Postgres.
DB tests: use `client` + `db` fixtures (skipped if no DB).
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


def _make_user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role.value.lower()}@example.com",
        name=role.value.title(),
        role=role,
        oauth_provider=None,
        oauth_subject=None,
    )


@pytest_asyncio.fixture
async def anon_client():
    """Client with no auth override — all auth deps run normally."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def member_client():
    member = _make_user(UserRole.MEMBER)

    async def _override():
        return member

    app.dependency_overrides[get_current_user] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ── Unauthenticated ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_event_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.post(
        "/api/v1/events",
        json={"title": "T", "start_datetime": "2027-01-01T10:00:00Z"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_event_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.put(f"/api/v1/events/{uuid.uuid4()}", json={"title": "T"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_event_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.delete(f"/api/v1/events/{uuid.uuid4()}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invite_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.post(
        f"/api/v1/events/{uuid.uuid4()}/invite",
        json={"invited_email": "x@x.com"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_suggest_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.post(f"/api/v1/events/{uuid.uuid4()}/ai/suggest-invitees")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_list_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.get("/api/v1/admin/users")
    assert resp.status_code == 401


# ── Member — forbidden on management endpoints ────────────────────────────────


@pytest.mark.asyncio
async def test_create_event_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.post(
        "/api/v1/events",
        json={"title": "T", "start_datetime": "2027-01-01T10:00:00Z"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_event_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.put(f"/api/v1/events/{uuid.uuid4()}", json={"title": "T"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_event_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.delete(f"/api/v1/events/{uuid.uuid4()}")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_invite_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.post(
        f"/api/v1/events/{uuid.uuid4()}/invite",
        json={"invited_email": "x@x.com"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ai_suggest_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.post(f"/api/v1/events/{uuid.uuid4()}/ai/suggest-invitees")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.get("/api/v1/admin/users")
    assert resp.status_code == 403


# ── Organizer — allowed on event management ───────────────────────────────────


@pytest_asyncio.fixture
async def organizer_client(db):
    organizer = _make_user(UserRole.ORGANIZER)

    async def _override_user():
        return organizer

    async def _override_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_create_event_organizer_allowed(organizer_client: AsyncClient) -> None:
    resp = await organizer_client.post(
        "/api/v1/events",
        json={"title": "RBAC Test Event", "start_datetime": "2027-06-01T10:00:00Z"},
    )
    assert resp.status_code == 201
    assert resp.json()["title"] == "RBAC Test Event"


# ── Admin — allowed on user management ───────────────────────────────────────


@pytest_asyncio.fixture
async def admin_client(db):
    admin = _make_user(UserRole.ADMIN)

    async def _override_user():
        return admin

    async def _override_db():
        yield db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_admin_list_users_allowed(admin_client: AsyncClient, db) -> None:
    resp = await admin_client.get("/api/v1/admin/users")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_update_role_allowed(admin_client: AsyncClient, db) -> None:
    result = await db.scalars(select(User).limit(1))
    target = result.first()
    if target is None:
        pytest.skip("No users in DB")

    resp = await admin_client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "ORGANIZER"},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "ORGANIZER"
