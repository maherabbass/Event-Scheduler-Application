from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = Field(..., description='Always `"ok"` when the server is running.')
    version: str = Field(..., description="Deployed application version.")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Lightweight liveness probe. Returns `200 OK` whenever the server process is alive.",
)
async def health_check() -> dict:
    return {"status": "ok", "version": "0.1.0"}
