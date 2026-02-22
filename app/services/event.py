import logging
import math
import uuid
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import cast, func, or_, select
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event, EventStatus
from app.models.user import User, UserRole
from app.schemas.event import EventCreate, EventListResponse, EventResponse, EventUpdate

logger = logging.getLogger(__name__)


async def list_events(
    db: AsyncSession,
    *,
    query: str | None = None,
    location: str | None = None,
    tags: list[str] | None = None,
    status: EventStatus | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User | None = None,
) -> EventListResponse:
    stmt = select(Event)

    # Text search: ILIKE on title, location, description
    if query:
        pattern = f"%{query}%"
        stmt = stmt.where(
            or_(
                Event.title.ilike(pattern),
                Event.location.ilike(pattern),
                Event.description.ilike(pattern),
            )
        )

    if location:
        stmt = stmt.where(Event.location.ilike(f"%{location}%"))

    if tags:
        # Event must have at least one overlapping tag (PostgreSQL && operator)
        from sqlalchemy import String

        stmt = stmt.where(Event.tags.overlap(cast(tags, PG_ARRAY(String))))

    if status:
        stmt = stmt.where(Event.status == status)
    else:
        # Apply visibility rules
        if current_user is None:
            # Public: only PUBLISHED
            stmt = stmt.where(Event.status == EventStatus.PUBLISHED)
        elif current_user.role == UserRole.ADMIN:
            # Admin: all events
            pass
        else:
            # Authenticated non-admin: PUBLISHED + their own DRAFTs + CANCELLED
            stmt = stmt.where(
                or_(
                    Event.status == EventStatus.PUBLISHED,
                    Event.status == EventStatus.CANCELLED,
                    (Event.status == EventStatus.DRAFT) & (Event.created_by == current_user.id),
                )
            )

    if date_from:
        stmt = stmt.where(Event.start_datetime >= date_from)

    if date_to:
        stmt = stmt.where(Event.start_datetime <= date_to)

    stmt = stmt.order_by(Event.start_datetime)

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await db.scalar(count_stmt) or 0

    # Pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.scalars(stmt)
    events = list(result.all())

    pages = math.ceil(total / page_size) if page_size > 0 else 0

    return EventListResponse(
        items=[EventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


async def get_event(db: AsyncSession, event_id: uuid.UUID) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


async def create_event(db: AsyncSession, data: EventCreate, user_id: uuid.UUID) -> Event:
    event = Event(
        title=data.title,
        description=data.description,
        location=data.location,
        start_datetime=data.start_datetime,
        end_datetime=data.end_datetime,
        created_by=user_id,
        tags=data.tags,
        status=data.status,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    logger.info("Event created: id=%s title=%r user=%s", event.id, event.title, user_id)
    return event


async def update_event(
    db: AsyncSession, event_id: uuid.UUID, data: EventUpdate, user: User
) -> Event:
    event = await get_event(db, event_id)

    # Ownership check: ORGANIZER can only edit their own events
    if user.role == UserRole.ORGANIZER and event.created_by != user.id:
        logger.warning("Forbidden update attempt: user=%s event=%s", user.id, event_id)
        raise HTTPException(status_code=403, detail="Cannot modify another organizer's event")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    logger.info("Event updated: id=%s user=%s", event_id, user.id)
    return event


async def delete_event(db: AsyncSession, event_id: uuid.UUID, user: User) -> None:
    event = await get_event(db, event_id)

    # Ownership check: ORGANIZER can only delete their own events
    if user.role == UserRole.ORGANIZER and event.created_by != user.id:
        logger.warning("Forbidden delete attempt: user=%s event=%s", user.id, event_id)
        raise HTTPException(status_code=403, detail="Cannot delete another organizer's event")

    await db.delete(event)
    await db.commit()
    logger.info("Event deleted: id=%s user=%s", event_id, user.id)
