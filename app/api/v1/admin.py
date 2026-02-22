import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_role
from app.db.session import get_db
from app.models.user import UserRole
from app.schemas.user import RoleUpdate, UserResponse
from app.services.user import list_users, update_user_role

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

_ADMIN_RESPONSES: dict = {
    401: {"description": "Missing, invalid, or expired Bearer token."},
    403: {"description": "Forbidden — Admin role required."},
}


@router.get(
    "/users",
    response_model=list[UserResponse],
    dependencies=[require_role(UserRole.ADMIN)],
    summary="List all users",
    responses={**_ADMIN_RESPONSES},
)
async def get_users(db: AsyncSession = Depends(get_db)) -> list[UserResponse]:
    users = await list_users(db)
    return [UserResponse.model_validate(u) for u in users]


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    dependencies=[require_role(UserRole.ADMIN)],
    summary="Change a user's role",
    responses={
        **_ADMIN_RESPONSES,
        404: {"description": "User not found."},
    },
)
async def patch_user_role(
    user_id: uuid.UUID,
    body: RoleUpdate,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await update_user_role(db, user_id, body.role)
    return UserResponse.model_validate(user)
