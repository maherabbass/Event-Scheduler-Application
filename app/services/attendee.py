import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_attendee import EventAttendee, RSVPStatus
from app.models.user import User
from app.schemas.attendee import AttendeeResponse


async def upsert_rsvp(
    db: AsyncSession,
    event_id: uuid.UUID,
    user_id: uuid.UUID,
    status: RSVPStatus,
) -> EventAttendee:
    now = datetime.now(timezone.utc)

    # Try to find existing record first
    existing = await db.scalar(
        select(EventAttendee).where(
            EventAttendee.event_id == event_id,
            EventAttendee.user_id == user_id,
        )
    )

    if existing:
        existing.rsvp_status = status
        existing.responded_at = now
        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        attendee = EventAttendee(
            id=uuid.uuid4(),
            event_id=event_id,
            user_id=user_id,
            rsvp_status=status,
            responded_at=now,
        )
        db.add(attendee)
        await db.commit()
        await db.refresh(attendee)
        return attendee


async def get_attendees(db: AsyncSession, event_id: uuid.UUID) -> list[AttendeeResponse]:
    stmt = (
        select(EventAttendee, User)
        .join(User, EventAttendee.user_id == User.id)
        .where(EventAttendee.event_id == event_id)
        .order_by(EventAttendee.created_at)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        AttendeeResponse(
            user_id=attendee.user_id,
            email=user.email,
            name=user.name,
            rsvp_status=attendee.rsvp_status,
            responded_at=attendee.responded_at,
        )
        for attendee, user in rows
    ]


async def get_user_rsvp(
    db: AsyncSession, event_id: uuid.UUID, user_id: uuid.UUID
) -> EventAttendee | None:
    result = await db.scalar(
        select(EventAttendee).where(
            EventAttendee.event_id == event_id, EventAttendee.user_id == user_id
        )
    )
    return result
