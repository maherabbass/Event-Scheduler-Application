import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.event import EventStatus


class EventCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500, description="Event title.")
    description: str | None = Field(None, description="Event description.")
    location: str | None = Field(None, description="Event location.")
    start_datetime: datetime = Field(..., description="Event start time (timezone-aware).")
    end_datetime: datetime | None = Field(None, description="Event end time (optional).")
    tags: list[str] = Field(default_factory=list, description="List of tags.")
    status: EventStatus = Field(EventStatus.DRAFT, description="Event status.")


class EventUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    location: str | None = None
    start_datetime: datetime | None = None
    end_datetime: datetime | None = None
    tags: list[str] | None = None
    status: EventStatus | None = None


class EventResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    location: str | None
    start_datetime: datetime
    end_datetime: datetime | None
    created_by: uuid.UUID
    tags: list[str]
    status: EventStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int
    page: int
    page_size: int
    pages: int
