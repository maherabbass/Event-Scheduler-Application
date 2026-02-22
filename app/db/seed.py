"""Idempotent async seed script.

Run with: python -m app.db.seed
"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.event import Event, EventStatus
from app.models.event_attendee import EventAttendee, RSVPStatus
from app.models.user import User, UserRole

# Seed users
SEED_USERS = [
    {"email": "admin@example.com", "name": "Admin User", "role": UserRole.ADMIN},
    {"email": "organizer@example.com", "name": "Event Organizer", "role": UserRole.ORGANIZER},
    {"email": "member@example.com", "name": "Regular Member", "role": UserRole.MEMBER},
    {"email": "alice@example.com", "name": "Alice Johnson", "role": UserRole.MEMBER},
    {"email": "bob@example.com", "name": "Bob Smith", "role": UserRole.MEMBER},
]

now = datetime.now(timezone.utc)


def _dt(days: int, hour: int = 10) -> datetime:
    return (now + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)


# Seed events (created_by will be filled with organizer UUID at runtime)
SEED_EVENTS_TEMPLATE = [
    {
        "title": "Tech Conference 2026",
        "description": "Annual technology conference covering AI, cloud, and DevOps.",
        "location": "Convention Center, New York",
        "start_datetime": _dt(14, 9),
        "end_datetime": _dt(16, 18),
        "tags": ["technology", "ai", "cloud", "devops"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Python Meetup — FastAPI Deep Dive",
        "description": "Monthly Python meetup focusing on FastAPI best practices.",
        "location": "Tech Hub, San Francisco",
        "start_datetime": _dt(7, 18),
        "end_datetime": _dt(7, 21),
        "tags": ["python", "fastapi", "backend", "meetup"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "UX Design Workshop",
        "description": "Hands-on workshop on user research and design systems.",
        "location": "Design Studio, Austin",
        "start_datetime": _dt(21, 10),
        "end_datetime": _dt(21, 17),
        "tags": ["design", "ux", "workshop"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Startup Pitch Night",
        "description": "Five startups pitch to a panel of investors.",
        "location": "Innovation Hub, Boston",
        "start_datetime": _dt(10, 19),
        "end_datetime": _dt(10, 22),
        "tags": ["startup", "investment", "networking"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Machine Learning Study Group",
        "description": "Bi-weekly study group covering ML fundamentals and papers.",
        "location": "Online (Zoom)",
        "start_datetime": _dt(3, 17),
        "end_datetime": _dt(3, 19),
        "tags": ["machine-learning", "ai", "study-group"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "React 19 Release Party",
        "description": "Celebrating the React 19 release with live demos and talks.",
        "location": "Coworking Space, Seattle",
        "start_datetime": _dt(28, 18),
        "end_datetime": _dt(28, 21),
        "tags": ["react", "frontend", "javascript"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Cloud Architecture Summit",
        "description": "In-depth sessions on AWS, GCP, and Azure architectures.",
        "location": "Grand Hotel, Chicago",
        "start_datetime": _dt(45, 8),
        "end_datetime": _dt(47, 17),
        "tags": ["cloud", "aws", "gcp", "azure", "architecture"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Open Source Hackathon",
        "description": "48-hour hackathon contributing to open source projects.",
        "location": "University Campus, Portland",
        "start_datetime": _dt(35, 9),
        "end_datetime": _dt(37, 9),
        "tags": ["hackathon", "open-source", "coding"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Data Engineering Webinar",
        "description": "Best practices for building data pipelines with dbt and Spark.",
        "location": "Online",
        "start_datetime": _dt(5, 14),
        "end_datetime": _dt(5, 16),
        "tags": ["data", "dbt", "spark", "engineering"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Networking Lunch — Tech Founders",
        "description": "Informal lunch for tech founders to connect and share experiences.",
        "location": "The Restaurant, Miami",
        "start_datetime": _dt(12, 12),
        "end_datetime": _dt(12, 14),
        "tags": ["networking", "startup", "founders"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Internal Planning Session",
        "description": "Q2 planning session for the engineering team.",
        "location": "Office, Room 3B",
        "start_datetime": _dt(2, 10),
        "end_datetime": _dt(2, 12),
        "tags": ["internal", "planning"],
        "status": EventStatus.DRAFT,
    },
    {
        "title": "Blockchain & Web3 Conference",
        "description": "Exploring the future of decentralized applications.",
        "location": "Convention Hall, Las Vegas",
        "start_datetime": _dt(60, 9),
        "end_datetime": _dt(62, 18),
        "tags": ["blockchain", "web3", "crypto"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "DevOps Days",
        "description": "Two-day event covering CI/CD, infrastructure as code, and observability.",
        "location": "Tech Center, Denver",
        "start_datetime": _dt(40, 9),
        "end_datetime": _dt(41, 18),
        "tags": ["devops", "cicd", "infrastructure"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Women in Tech Summit",
        "description": "Empowering women in technology with talks and mentorship.",
        "location": "Conference Center, Los Angeles",
        "start_datetime": _dt(25, 9),
        "end_datetime": _dt(25, 18),
        "tags": ["diversity", "tech", "networking", "mentorship"],
        "status": EventStatus.PUBLISHED,
    },
    {
        "title": "Cancelled: Old Product Launch",
        "description": "This event has been cancelled.",
        "location": "N/A",
        "start_datetime": _dt(-5, 10),
        "end_datetime": _dt(-5, 12),
        "tags": ["product"],
        "status": EventStatus.CANCELLED,
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        print("Seeding users...")
        user_map: dict[str, User] = {}

        for u_data in SEED_USERS:
            existing = await db.scalar(select(User).where(User.email == u_data["email"]))
            if existing:
                user_map[u_data["email"]] = existing
                print(f"  User already exists: {u_data['email']}")
            else:
                user = User(
                    email=u_data["email"],
                    name=u_data["name"],
                    role=u_data["role"],
                )
                db.add(user)
                await db.flush()
                user_map[u_data["email"]] = user
                print(f"  Created user: {u_data['email']}")

        await db.commit()

        # Reload from DB after commit
        for email in list(user_map.keys()):
            user_map[email] = await db.scalar(select(User).where(User.email == email))

        organizer = user_map["organizer@example.com"]
        member = user_map["member@example.com"]
        alice = user_map["alice@example.com"]
        bob = user_map["bob@example.com"]

        print("\nSeeding events...")
        events: list[Event] = []

        for e_data in SEED_EVENTS_TEMPLATE:
            existing = await db.scalar(select(Event).where(Event.title == e_data["title"]))
            if existing:
                events.append(existing)
                print(f"  Event already exists: {e_data['title']}")
            else:
                event = Event(
                    title=e_data["title"],
                    description=e_data["description"],
                    location=e_data["location"],
                    start_datetime=e_data["start_datetime"],
                    end_datetime=e_data.get("end_datetime"),
                    created_by=organizer.id,
                    tags=e_data["tags"],
                    status=e_data["status"],
                )
                db.add(event)
                await db.flush()
                events.append(event)
                print(f"  Created event: {e_data['title']}")

        await db.commit()

        # Reload events
        reloaded_events = []
        for event in events:
            reloaded = await db.get(Event, event.id)
            if reloaded:
                reloaded_events.append(reloaded)
        events = reloaded_events

        print("\nSeeding RSVPs...")
        published_events = [e for e in events if e.status == EventStatus.PUBLISHED]

        rsvp_assignments = [
            (member, published_events[0], RSVPStatus.ATTENDING),
            (member, published_events[1], RSVPStatus.MAYBE),
            (member, published_events[2], RSVPStatus.ATTENDING),
            (alice, published_events[0], RSVPStatus.ATTENDING),
            (alice, published_events[3], RSVPStatus.ATTENDING),
            (alice, published_events[4], RSVPStatus.MAYBE),
            (bob, published_events[1], RSVPStatus.ATTENDING),
            (bob, published_events[5], RSVPStatus.ATTENDING),
            (bob, published_events[6] if len(published_events) > 6 else published_events[0], RSVPStatus.MAYBE),
        ]

        for user, event, rsvp_status in rsvp_assignments:
            existing_rsvp = await db.scalar(
                select(EventAttendee).where(
                    EventAttendee.event_id == event.id,
                    EventAttendee.user_id == user.id,
                )
            )
            if existing_rsvp:
                print(f"  RSVP already exists: {user.email} → {event.title}")
            else:
                attendee = EventAttendee(
                    event_id=event.id,
                    user_id=user.id,
                    rsvp_status=rsvp_status,
                    responded_at=datetime.now(timezone.utc),
                )
                db.add(attendee)
                print(f"  Created RSVP: {user.email} → {event.title} ({rsvp_status})")

        await db.commit()
        print("\nSeed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
