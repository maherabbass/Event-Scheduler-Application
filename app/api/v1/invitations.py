from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.invitation import accept_invitation

router = APIRouter(prefix="/api/v1/invitations", tags=["invitations"])


@router.get(
    "/accept/{token}",
    summary="Accept invitation",
    description=(
        "Validates the invitation token, marks the invitation as accepted, "
        "and creates an RSVP (ATTENDING) if the invited email is a registered user."
    ),
)
async def accept_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await accept_invitation(db, token)
