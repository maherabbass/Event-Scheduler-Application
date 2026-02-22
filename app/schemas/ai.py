import uuid

from pydantic import BaseModel, Field


class SuggestedInvitee(BaseModel):
    user_id: uuid.UUID
    name: str
    email: str
    score: float = Field(..., description="Relevance score (higher = more relevant).")
    invitation_message: str = Field(..., description="Personalised invitation message draft.")


class SuggestInviteesResponse(BaseModel):
    suggestions: list[SuggestedInvitee]
