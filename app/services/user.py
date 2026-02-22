import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole


async def get_or_create_user(
    db: AsyncSession,
    *,
    email: str,
    name: str,
    provider: str,
    subject: str,
) -> User:
    # Look up by (provider, subject) first — most reliable
    user = await db.scalar(
        select(User).where(User.oauth_provider == provider, User.oauth_subject == subject)
    )
    if user is None:
        # Fall back to email (links existing seeded / local users)
        user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            name=name,
            oauth_provider=provider,
            oauth_subject=subject,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.scalars(select(User).order_by(User.created_at))
    return list(result.all())


async def update_user_role(db: AsyncSession, user_id: uuid.UUID, role: UserRole) -> User:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user
