import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_attendee import EventAttendee, RSVPStatus
from app.models.invitation import Invitation

logger = logging.getLogger(__name__)


async def create_invitation(
    db: AsyncSession,
    event_id: uuid.UUID,
    invited_by: uuid.UUID,
    invited_email: str,
) -> Invitation:
    # Check if invitation already exists
    existing = await db.scalar(
        select(Invitation).where(
            Invitation.event_id == event_id,
            Invitation.invited_email == invited_email,
        )
    )
    if existing:
        logger.warning("Duplicate invitation: event=%s email=%s", event_id, invited_email)
        raise HTTPException(
            status_code=409,
            detail=f"Invitation already sent to {invited_email} for this event",
        )

    token = secrets.token_urlsafe(24)  # 32+ chars url-safe
    invitation = Invitation(
        event_id=event_id,
        invited_by=invited_by,
        invited_email=invited_email,
        token=token,
        accepted=False,
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    logger.info("Invitation created: event=%s email=%s by=%s", event_id, invited_email, invited_by)
    return invitation


async def accept_invitation(db: AsyncSession, token: str) -> dict:
    invitation = await db.scalar(select(Invitation).where(Invitation.token == token))
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.accepted:
        raise HTTPException(status_code=409, detail="Invitation already accepted")

    # Find the user by email (if registered)
    from app.models.user import User

    user = await db.scalar(select(User).where(User.email == invitation.invited_email))

    if user:
        # Create RSVP
        existing_rsvp = await db.scalar(
            select(EventAttendee).where(
                EventAttendee.event_id == invitation.event_id,
                EventAttendee.user_id == user.id,
            )
        )
        if not existing_rsvp:
            attendee = EventAttendee(
                event_id=invitation.event_id,
                user_id=user.id,
                rsvp_status=RSVPStatus.ATTENDING,
                responded_at=datetime.now(timezone.utc),
            )
            db.add(attendee)

    # Mark invitation accepted
    invitation.accepted = True
    await db.commit()

    logger.info(
        "Invitation accepted: event=%s email=%s user_registered=%s",
        invitation.event_id,
        invitation.invited_email,
        user is not None,
    )
    return {"message": "Invitation accepted successfully", "event_id": str(invitation.event_id)}
