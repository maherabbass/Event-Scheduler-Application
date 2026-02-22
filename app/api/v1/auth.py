from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.jwt import create_access_token
from app.auth.oauth import SUPPORTED_PROVIDERS, oauth
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import TokenResponse, UserResponse
from app.services.user import get_or_create_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_ALL_PROVIDERS = {"google", "github"}

_AUTH_ERROR_RESPONSES: dict = {
    400: {"description": "Unsupported or unknown OAuth provider."},
    503: {"description": "OAuth provider is not configured on this server."},
}


@router.get(
    "/login/{provider}",
    summary="Start OAuth login",
    status_code=302,
    responses={**_AUTH_ERROR_RESPONSES},
)
async def login(provider: str, request: Request) -> None:
    if provider not in _ALL_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=503,
            detail=f"Provider '{provider}' is not configured on this server",
        )
    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/callback/{provider}"
    client = oauth.create_client(provider)
    return await client.authorize_redirect(request, redirect_uri)


@router.get(
    "/callback/{provider}",
    response_model=TokenResponse,
    summary="OAuth callback — issues JWT",
    responses={
        302: {"description": "Redirect to frontend SPA with `?token=<jwt>` query parameter."},
        **_AUTH_ERROR_RESPONSES,
    },
)
async def callback(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    if provider not in _ALL_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=503,
            detail=f"Provider '{provider}' is not configured on this server",
        )

    client = oauth.create_client(provider)
    token = await client.authorize_access_token(request)

    if provider == "google":
        userinfo = token.get("userinfo") or await client.userinfo(token=token)
        email: str = userinfo["email"]
        name: str = userinfo.get("name") or email.split("@")[0]
        subject: str = userinfo["sub"]
    else:  # github
        resp = await client.get("user", token=token)
        resp.raise_for_status()
        profile = resp.json()
        subject = str(profile["id"])
        name = profile.get("name") or profile.get("login") or "GitHub User"
        email = profile.get("email") or ""
        if not email:
            emails_resp = await client.get("user/emails", token=token)
            emails_resp.raise_for_status()
            emails = emails_resp.json()
            primary = next(
                (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                None,
            )
            if primary is None:
                primary = next((e["email"] for e in emails if e.get("verified")), None)
            if primary is None:
                raise HTTPException(
                    status_code=400,
                    detail="No verified email found in GitHub account",
                )
            email = primary

    user = await get_or_create_user(db, email=email, name=name, provider=provider, subject=subject)
    access_token = create_access_token({"sub": str(user.id)})

    if settings.FRONTEND_URL:
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/auth/callback?token={access_token}")
    return TokenResponse(access_token=access_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    responses={401: {"description": "Missing, invalid, or expired Bearer token."}},
)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)
