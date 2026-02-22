import json
import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.event import Event
from app.models.event_attendee import EventAttendee, RSVPStatus
from app.models.user import User
from app.schemas.ai import SuggestedInvitee, SuggestInviteesResponse

logger = logging.getLogger("event_scheduler.ai")


def _fallback_score(user: User, event: Event, user_tags: set[str]) -> float:
    """Deterministic relevance score based on tag overlap."""
    event_tags = set(event.tags or [])
    overlap = len(event_tags & user_tags)
    return float(overlap)


def _fallback_message(user: User, event: Event) -> str:
    date_str = event.start_datetime.strftime("%B %d, %Y")
    return (
        f"Hi {user.name}, we think you might enjoy '{event.title}' on {date_str}!"
        f" Join us{' at ' + event.location if event.location else ''}."
    )


async def suggest_invitees(
    db: AsyncSession,
    event_id: uuid.UUID,
    top_n: int = 10,
) -> SuggestInviteesResponse:
    # 1. Load event details
    event = await db.get(Event, event_id)
    if event is None:
        return SuggestInviteesResponse(suggestions=[])

    # 2. Load all users + their RSVP history (tags from events they attended)
    users_result = await db.scalars(select(User))
    all_users = list(users_result.all())

    # Get RSVP history per user: which events they attended
    attended_stmt = (
        select(EventAttendee, Event)
        .join(Event, EventAttendee.event_id == Event.id)
        .where(EventAttendee.rsvp_status.in_([RSVPStatus.ATTENDING, RSVPStatus.MAYBE]))
    )
    attended_result = await db.execute(attended_stmt)
    attended_rows = attended_result.all()

    # Build per-user tag sets from events they attended
    user_tags: dict[uuid.UUID, set[str]] = {}
    user_event_count: dict[uuid.UUID, int] = {}
    for attendee, attended_event in attended_rows:
        uid = attendee.user_id
        if uid not in user_tags:
            user_tags[uid] = set()
            user_event_count[uid] = 0
        user_tags[uid].update(attended_event.tags or [])
        user_event_count[uid] += 1

    # Exclude the event creator (they're already attending)
    eligible_users = [u for u in all_users if u.id != event.created_by]

    # 3. Try OpenAI first
    if settings.OPENAI_API_KEY:
        try:
            suggestions = await _openai_suggest(
                event=event,
                users=eligible_users,
                user_tags=user_tags,
                user_event_count=user_event_count,
                top_n=top_n,
            )
            return SuggestInviteesResponse(suggestions=suggestions)
        except Exception as e:
            logger.warning(f"OpenAI suggestion failed, using fallback: {e}")

    # 4. Fallback: deterministic scoring
    suggestions = _deterministic_suggest(
        event=event,
        users=eligible_users,
        user_tags=user_tags,
        top_n=top_n,
    )
    return SuggestInviteesResponse(suggestions=suggestions)


async def _openai_suggest(
    event: Event,
    users: list[User],
    user_tags: dict[uuid.UUID, set[str]],
    user_event_count: dict[uuid.UUID, int],
    top_n: int,
) -> list[SuggestedInvitee]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    # Build user summaries (limit to top 50 users to avoid token overflow)
    user_summaries = []
    for user in users[:50]:
        tags = list(user_tags.get(user.id, set()))
        count = user_event_count.get(user.id, 0)
        user_summaries.append(
            {
                "user_id": str(user.id),
                "name": user.name,
                "email": user.email,
                "attended_events": count,
                "interest_tags": tags,
            }
        )

    event_date = event.start_datetime.strftime("%Y-%m-%d %H:%M")
    prompt = f"""You are an event invitation assistant.

Event details:
- Title: {event.title}
- Description: {event.description or 'N/A'}
- Location: {event.location or 'N/A'}
- Date: {event_date}
- Tags: {event.tags}

Users (with their event history):
{json.dumps(user_summaries, indent=2)}

Return a JSON array of the top {top_n} most relevant users with personalised invitation messages.
Format: [{{"user_id": "...", "score": 0.95, "invitation_message": "..."}}]
Score from 0.0 to 1.0 based on tag overlap and interest match.
Return ONLY the JSON array, no other text."""

    response = await client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=2000,
    )

    content = response.choices[0].message.content or "[]"
    # Clean up markdown code blocks if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    raw_suggestions = json.loads(content)

    # Build user lookup
    user_map = {str(u.id): u for u in users}

    results = []
    for item in raw_suggestions[:top_n]:
        uid = item.get("user_id")
        user = user_map.get(uid)
        if user:
            results.append(
                SuggestedInvitee(
                    user_id=user.id,
                    name=user.name,
                    email=user.email,
                    score=float(item.get("score", 0.5)),
                    invitation_message=item.get("invitation_message", _fallback_message(user, event)),
                )
            )
    return results


def _deterministic_suggest(
    event: Event,
    users: list[User],
    user_tags: dict[uuid.UUID, set[str]],
    top_n: int,
) -> list[SuggestedInvitee]:
    event_tags = set(event.tags or [])
    scored = []
    for user in users:
        tags = user_tags.get(user.id, set())
        score = float(len(event_tags & tags)) if event_tags else 0.1
        scored.append(
            SuggestedInvitee(
                user_id=user.id,
                name=user.name,
                email=user.email,
                score=score,
                invitation_message=_fallback_message(user, event),
            )
        )

    scored.sort(key=lambda x: x.score, reverse=True)
    return scored[:top_n]
