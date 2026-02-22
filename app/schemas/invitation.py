import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InvitationRequest(BaseModel):
    invited_email: str = Field(..., description="Email address to invite.")


class InvitationResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    invited_email: str
    accepted: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
