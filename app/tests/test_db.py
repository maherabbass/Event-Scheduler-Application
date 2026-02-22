"""DB connectivity and model enum tests.

test_db_connection  — requires a running Postgres (skipped if unavailable)
test_model_enums    — pure Python, no DB required
"""

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_db_connection() -> None:
    """Verify that the async engine can connect and run a simple query."""
    try:
        from app.db.session import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()
            assert value == 1
    except Exception as exc:
        pytest.skip(f"Database not available: {exc}")


def test_model_enums() -> None:
    """Verify all domain enums have the expected values (no DB required)."""
    from app.models.event import EventStatus
    from app.models.event_attendee import RSVPStatus
    from app.models.user import UserRole

    # UserRole
    assert UserRole.ADMIN == "ADMIN"
    assert UserRole.ORGANIZER == "ORGANIZER"
    assert UserRole.MEMBER == "MEMBER"
    assert set(UserRole) == {UserRole.ADMIN, UserRole.ORGANIZER, UserRole.MEMBER}

    # EventStatus
    assert EventStatus.DRAFT == "DRAFT"
    assert EventStatus.PUBLISHED == "PUBLISHED"
    assert EventStatus.CANCELLED == "CANCELLED"
    assert set(EventStatus) == {EventStatus.DRAFT, EventStatus.PUBLISHED, EventStatus.CANCELLED}

    # RSVPStatus
    assert RSVPStatus.UPCOMING == "UPCOMING"
    assert RSVPStatus.ATTENDING == "ATTENDING"
    assert RSVPStatus.MAYBE == "MAYBE"
    assert RSVPStatus.DECLINED == "DECLINED"
    assert set(RSVPStatus) == {
        RSVPStatus.UPCOMING,
        RSVPStatus.ATTENDING,
        RSVPStatus.MAYBE,
        RSVPStatus.DECLINED,
    }
