import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_role
from app.auth.jwt import decode_token
from app.db.session import get_db
from app.models.event import EventStatus
from app.models.user import User, UserRole
from app.schemas.attendee import AttendeeResponse, RSVPRequest
from app.schemas.ai import SuggestInviteesResponse
from app.schemas.event import EventCreate, EventListResponse, EventResponse, EventUpdate
from app.schemas.invitation import InvitationRequest, InvitationResponse
from app.services import attendee as attendee_svc
from app.services import event as event_svc
from app.services import invitation as invitation_svc
from app.services.ai import suggest_invitees

router = APIRouter(prefix="/api/v1/events", tags=["events"])

_AUTH_RESPONSES: dict = {
    401: {"description": "Missing, invalid, or expired Bearer token."},
    403: {"description": "Forbidden — insufficient permissions."},
}

_optional_bearer = HTTPBearer(auto_error=False)


async def _optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Return the current user if a valid token is provided, else None."""
    if credentials is None:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user_id: str = payload["sub"]
    except (JWTError, KeyError):
        return None
    return await db.get(User, uuid.UUID(user_id))


# ── Public endpoints ──────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=EventListResponse,
    summary="List / search events",
    description=(
        "Returns events with optional filters. "
        "Public users see only PUBLISHED events. "
        "Authenticated users also see CANCELLED events and their own DRAFTs."
    ),
)
async def list_events(
    query: str | None = Query(None, description="Text search on title, location, description."),
    location: str | None = Query(None),
    tags: list[str] | None = Query(None),
    status: EventStatus | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(_optional_current_user),
) -> EventListResponse:
    return await event_svc.list_events(
        db,
        query=query,
        location=location,
        tags=tags,
        status=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        current_user=current_user,
    )


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Get event detail",
)
async def get_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EventResponse:
    event = await event_svc.get_event(db, event_id)
    return EventResponse.model_validate(event)


# ── Authenticated endpoints ───────────────────────────────────────────────────


@router.post(
    "",
    response_model=EventResponse,
    status_code=201,
    summary="Create event",
    responses={**_AUTH_RESPONSES},
)
async def create_event(
    data: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role(UserRole.ORGANIZER, UserRole.ADMIN),
) -> EventResponse:
    event = await event_svc.create_event(db, data, current_user.id)
    return EventResponse.model_validate(event)


@router.put(
    "/{event_id}",
    response_model=EventResponse,
    summary="Update event",
    responses={**_AUTH_RESPONSES, 404: {"description": "Event not found."}},
)
async def update_event(
    event_id: uuid.UUID,
    data: EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role(UserRole.ORGANIZER, UserRole.ADMIN),
) -> EventResponse:
    event = await event_svc.update_event(db, event_id, data, current_user)
    return EventResponse.model_validate(event)


@router.delete(
    "/{event_id}",
    status_code=204,
    summary="Delete event",
    responses={**_AUTH_RESPONSES, 404: {"description": "Event not found."}},
)
async def delete_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role(UserRole.ORGANIZER, UserRole.ADMIN),
) -> None:
    await event_svc.delete_event(db, event_id, current_user)


@router.post(
    "/{event_id}/rsvp",
    response_model=AttendeeResponse,
    summary="RSVP to event",
    responses={**_AUTH_RESPONSES},
)
async def rsvp_event(
    event_id: uuid.UUID,
    body: RSVPRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AttendeeResponse:
    await event_svc.get_event(db, event_id)
    await attendee_svc.upsert_rsvp(db, event_id, current_user.id, body.rsvp_status)
    attendees = await attendee_svc.get_attendees(db, event_id)
    for a in attendees:
        if a.user_id == current_user.id:
            return a
    return AttendeeResponse(
        user_id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        rsvp_status=body.rsvp_status,
        responded_at=None,
    )


@router.get(
    "/{event_id}/attendees",
    response_model=list[AttendeeResponse],
    summary="List attendees",
    responses={**_AUTH_RESPONSES},
)
async def list_attendees(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AttendeeResponse]:
    await event_svc.get_event(db, event_id)
    return await attendee_svc.get_attendees(db, event_id)


@router.post(
    "/{event_id}/invite",
    response_model=InvitationResponse,
    status_code=201,
    summary="Send invitation",
    responses={**_AUTH_RESPONSES},
)
async def invite_to_event(
    event_id: uuid.UUID,
    body: InvitationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role(UserRole.ORGANIZER, UserRole.ADMIN),
) -> InvitationResponse:
    await event_svc.get_event(db, event_id)
    invitation = await invitation_svc.create_invitation(
        db, event_id, current_user.id, body.invited_email
    )
    return InvitationResponse.model_validate(invitation)


@router.post(
    "/{event_id}/ai/suggest-invitees",
    response_model=SuggestInviteesResponse,
    summary="AI-ranked invitation suggestions",
    description=(
        "Returns a ranked list of users likely to be interested in this event, "
        "with a personalised invitation message per user. "
        "Uses GPT-4o-mini when OPENAI_API_KEY is configured; falls back to deterministic scoring."
    ),
    responses={**_AUTH_RESPONSES},
)
async def ai_suggest_invitees(
    event_id: uuid.UUID,
    top_n: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = require_role(UserRole.ORGANIZER, UserRole.ADMIN),
) -> SuggestInviteesResponse:
    return await suggest_invitees(db, event_id, top_n=top_n)
