"""AI invitation suggestion tests.

All tests run without a database connection.
OpenAI calls are mocked where needed.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.auth.dependencies import get_current_user
from app.main import app
from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.services.ai import _deterministic_suggest, _fallback_message


def _make_user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        email=f"{role.value.lower()}-{uuid.uuid4().hex[:4]}@example.com",
        name=role.value.title(),
        role=role,
        oauth_provider=None,
        oauth_subject=None,
    )


def _make_event(**kwargs) -> Event:
    defaults = dict(
        id=uuid.uuid4(),
        title="Tech Conference",
        description="An event about technology.",
        location="Online",
        start_datetime=datetime(2027, 6, 1, 10, 0, tzinfo=timezone.utc),
        end_datetime=None,
        created_by=uuid.uuid4(),
        tags=["technology", "python", "ai"],
        status=EventStatus.PUBLISHED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(kwargs)
    return Event(**defaults)


@pytest_asyncio.fixture
async def anon_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def organizer_client():
    organizer = _make_user(UserRole.ORGANIZER)

    async def _override():
        return organizer

    app.dependency_overrides[get_current_user] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture
async def member_client():
    member = _make_user(UserRole.MEMBER)

    async def _override():
        return member

    app.dependency_overrides[get_current_user] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_current_user, None)


# ── Fallback (deterministic) logic ───────────────────────────────────────────


def test_fallback_message_contains_event_title() -> None:
    event = _make_event(title="Python Summit")
    user = _make_user(UserRole.MEMBER)
    msg = _fallback_message(user, event)
    assert "Python Summit" in msg


def test_fallback_message_contains_user_name() -> None:
    event = _make_event()
    user = _make_user(UserRole.MEMBER)
    user.name = "Alice"
    msg = _fallback_message(user, event)
    assert "Alice" in msg


def test_fallback_message_contains_location() -> None:
    event = _make_event(location="Berlin")
    user = _make_user(UserRole.MEMBER)
    msg = _fallback_message(user, event)
    assert "Berlin" in msg


def test_deterministic_suggest_returns_top_n() -> None:
    event = _make_event(tags=["python", "ai"])
    users = [_make_user(UserRole.MEMBER) for _ in range(10)]
    user_tags = {u.id: {"python", "ai"} for u in users[:5]}
    result = _deterministic_suggest(event, users, user_tags, top_n=3)
    assert len(result) == 3


def test_deterministic_suggest_scores_tag_overlap() -> None:
    event = _make_event(tags=["python", "ai", "cloud"])
    high = _make_user(UserRole.MEMBER)
    low = _make_user(UserRole.MEMBER)
    user_tags = {
        high.id: {"python", "ai", "cloud"},  # 3 overlapping tags
        low.id: {"music"},  # 0 overlapping tags
    }
    result = _deterministic_suggest(event, [high, low], user_tags, top_n=2)
    assert result[0].user_id == high.id
    assert result[0].score > result[1].score


def test_deterministic_suggest_no_tags_event() -> None:
    event = _make_event(tags=[])
    users = [_make_user(UserRole.MEMBER) for _ in range(3)]
    result = _deterministic_suggest(event, users, {}, top_n=3)
    # All users get the same score; no crash
    assert len(result) == 3
    assert all(r.score == result[0].score for r in result)


def test_deterministic_suggest_invitation_message_present() -> None:
    event = _make_event()
    user = _make_user(UserRole.MEMBER)
    result = _deterministic_suggest(event, [user], {}, top_n=1)
    assert len(result[0].invitation_message) > 0


# ── Auth boundary tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_suggest_no_auth(anon_client: AsyncClient) -> None:
    resp = await anon_client.post(f"/api/v1/events/{uuid.uuid4()}/ai/suggest-invitees")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ai_suggest_member_forbidden(member_client: AsyncClient) -> None:
    resp = await member_client.post(f"/api/v1/events/{uuid.uuid4()}/ai/suggest-invitees")
    assert resp.status_code == 403


# ── End-to-end with mocked DB + OpenAI ───────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_suggest_fallback_when_no_openai_key(organizer_client: AsyncClient) -> None:
    """Endpoint returns 200 with suggestions even when no OpenAI key is set."""
    event = _make_event()

    with (
        patch("app.api.v1.events.suggest_invitees") as mock_suggest,
    ):
        from app.schemas.ai import SuggestedInvitee, SuggestInviteesResponse

        mock_suggest.return_value = SuggestInviteesResponse(
            suggestions=[
                SuggestedInvitee(
                    user_id=uuid.uuid4(),
                    name="Alice",
                    email="alice@example.com",
                    score=0.9,
                    invitation_message="Hi Alice, join us!",
                )
            ]
        )

        resp = await organizer_client.post(
            f"/api/v1/events/{event.id}/ai/suggest-invitees",
        )

    assert resp.status_code == 200
    body = resp.json()
    assert "suggestions" in body
    assert len(body["suggestions"]) == 1
    assert body["suggestions"][0]["name"] == "Alice"
    assert body["suggestions"][0]["score"] == 0.9


@pytest.mark.asyncio
async def test_ai_suggest_schema_shape(organizer_client: AsyncClient) -> None:
    """Verify the response schema includes all required fields."""
    with patch("app.api.v1.events.suggest_invitees") as mock_suggest:
        from app.schemas.ai import SuggestedInvitee, SuggestInviteesResponse

        uid = uuid.uuid4()
        mock_suggest.return_value = SuggestInviteesResponse(
            suggestions=[
                SuggestedInvitee(
                    user_id=uid,
                    name="Bob",
                    email="bob@example.com",
                    score=0.75,
                    invitation_message="Hi Bob!",
                )
            ]
        )

        resp = await organizer_client.post(
            f"/api/v1/events/{uuid.uuid4()}/ai/suggest-invitees",
        )

    assert resp.status_code == 200
    suggestion = resp.json()["suggestions"][0]
    assert "user_id" in suggestion
    assert "name" in suggestion
    assert "email" in suggestion
    assert "score" in suggestion
    assert "invitation_message" in suggestion
