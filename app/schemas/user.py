import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserRole


class UserResponse(BaseModel):
    id: uuid.UUID = Field(..., description="Unique user identifier (UUID v4).")
    email: str = Field(..., description="User's verified email address.")
    name: str = Field(..., description="Display name from the OAuth provider.")
    role: UserRole = Field(
        ...,
        description="RBAC role: `ADMIN` | `ORGANIZER` | `MEMBER`. New users start as `MEMBER`.",
    )
    oauth_provider: str | None = Field(
        None,
        description="OAuth provider used to sign in: `google` or `github`.",
    )
    created_at: datetime = Field(..., description="UTC timestamp when the account was created.")

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str = Field(..., description="JWT Bearer token.")
    token_type: str = Field("bearer", description='Token scheme. Always `"bearer"`.')

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
            }
        }
    )


class RoleUpdate(BaseModel):
    role: UserRole = Field(
        ...,
        description="The new role to assign to the user: `ADMIN` | `ORGANIZER` | `MEMBER`.",
    )
