import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.event_attendee import RSVPStatus


class RSVPRequest(BaseModel):
    rsvp_status: RSVPStatus = Field(..., description="RSVP status.")


class AttendeeResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    name: str
    rsvp_status: RSVPStatus
    responded_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
