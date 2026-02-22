import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.events import router as events_router
from app.api.v1.health import router as health_router
from app.api.v1.invitations import router as invitations_router
from app.core.config import settings
from app.core.logging import setup_logging

logger = logging.getLogger(__name__)

_TAG_METADATA: list[dict[str, Any]] = [
    {
        "name": "health",
        "description": "Server liveness probe. No authentication required.",
    },
    {
        "name": "auth",
        "description": (
            "OAuth 2.0 SSO login via **Google** or **GitHub**.\n\n"
            "The callback endpoint issues a short-lived **JWT Bearer token**. "
            "Pass it in every protected request:\n\n"
            "```\nAuthorization: Bearer <token>\n```"
        ),
    },
    {
        "name": "events",
        "description": (
            "Full CRUD for events plus search and pagination.\n\n"
            "- **GET** endpoints are **public** — no token required.\n"
            "- **POST / PUT / DELETE** require **Organizer** or **Admin** role.\n"
            "- RSVP and attendee endpoints require authentication."
        ),
    },
    {
        "name": "invitations",
        "description": "Invitation acceptance endpoint (public).",
    },
    {
        "name": "admin",
        "description": "User management. Restricted to **Admin** role only.",
    },
]

_APP_DESCRIPTION = """\
An **Event Scheduler Application** built with FastAPI, PostgreSQL, and OpenAI.

## Authentication

All protected endpoints require a **Bearer JWT** obtained through the OAuth login flow:

1. Open `GET /api/v1/auth/login/google` (or `/github`) in your **browser**.
2. Complete the OAuth consent screen.
3. You are redirected to the frontend with `?token=<jwt>` in the URL.
4. Copy the token and paste it into the **Authorize** dialog (🔒 button above).

## Roles & Permissions

| Role | Capabilities |
|------|--------------|
| **Admin** | Full access including user management |
| **Organizer** | Create / edit / delete own events; send invitations |
| **Member** | Browse events; RSVP |

## AI Features

The `POST /events/{id}/ai/suggest-invitees` endpoint uses GPT-4o-mini when
`OPENAI_API_KEY` is configured, with a deterministic fallback when it's not.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    yield


app = FastAPI(
    title="Event Scheduler",
    description=_APP_DESCRIPTION,
    version="0.1.0",
    openapi_tags=_TAG_METADATA,
    contact={
        "name": "Event Scheduler",
        "url": "https://github.com/maherabbass/Event-Scheduler-Application",
    },
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

# CORS — explicit origins + optional regex for dynamic URLs (e.g. Netlify previews)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware (OAuth state storage).
# https_only=True sets the Secure flag on the session cookie, which is required
# on Cloud Run (HTTPS-only) so browsers send the cookie back on the OAuth callback.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=settings.APP_ENV == "production",
    same_site="lax",
)

# Routers
app.include_router(health_router)
app.include_router(events_router)
app.include_router(invitations_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def _custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        tags=app.openapi_tags,
        contact=app.contact,
        license_info=app.license_info,
        routes=app.routes,
    )

    schema.setdefault("components", {}).setdefault("securitySchemes", {})["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": (
            "JWT access token obtained from `GET /api/v1/auth/callback/{provider}`. "
            "Obtain it by completing the OAuth login flow and copying the `token` "
            "query parameter from the redirect URL."
        ),
    }

    app.openapi_schema = schema
    return schema


app.openapi = _custom_openapi
