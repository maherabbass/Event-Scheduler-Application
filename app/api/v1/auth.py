import hashlib
import hmac
import logging
import secrets
import time

import httpx
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_ALL_PROVIDERS = {"google", "github"}

_AUTH_ERROR_RESPONSES: dict = {
    400: {"description": "Unsupported or unknown OAuth provider."},
    503: {"description": "OAuth provider is not configured on this server."},
}

# ---------------------------------------------------------------------------
# Stateless HMAC-signed OAuth state
# Eliminates the session-cookie dependency that fails on Cloud Run when
# the browser doesn't send the session cookie back on the OAuth redirect.
# ---------------------------------------------------------------------------

_STATE_SEP = "."


def _make_signed_state() -> str:
    """Return a self-verifiable state token: '{nonce}.{ts}.{hmac}'."""
    nonce = secrets.token_hex(16)
    ts = str(int(time.time()))
    raw = f"{nonce}{_STATE_SEP}{ts}"
    sig = hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}{_STATE_SEP}{sig}"


def _verify_signed_state(state: str, max_age: int = 600) -> bool:
    """Return True only if the state was issued by us and is not expired."""
    try:
        # state = nonce.ts.sig  — split from the right to keep nonce intact
        parts = state.rsplit(_STATE_SEP, 1)
        if len(parts) != 2:
            return False
        raw, sig = parts
        expected = hmac.new(settings.SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        # raw = nonce.ts
        ts_str = raw.rsplit(_STATE_SEP, 1)[-1]
        if int(time.time()) - int(ts_str) > max_age:
            return False
        return True
    except Exception:
        return False


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
    state = _make_signed_state()
    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/callback/{provider}"
    logger.info("OAuth login initiated: provider=%s", provider)
    client = oauth.create_client(provider)
    # authorize_redirect also stores state in the session cookie.  That still
    # works when cookies are available (local dev); on Cloud Run we fall back
    # to the HMAC check in the callback.
    return await client.authorize_redirect(request, redirect_uri, state=state)


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

    # --- 1. Validate state (HMAC, no session required) ---------------------
    state = request.query_params.get("state", "")
    if not _verify_signed_state(state):
        logger.warning("OAuth state validation failed: provider=%s", provider)
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    code = request.query_params.get("code")
    if not code:
        logger.warning("OAuth callback missing code: provider=%s", provider)
        raise HTTPException(status_code=400, detail="Missing authorization code")

    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/callback/{provider}"

    # --- 2. Exchange code for token + fetch user info (direct httpx calls) -
    # Bypasses authlib's session-based state check entirely.
    logger.debug("OAuth callback: exchanging code for token, provider=%s", provider)
    async with httpx.AsyncClient() as http:
        if provider == "google":
            token_resp = await http.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Token exchange failed")
            token_data = token_resp.json()

            userinfo_resp = await http.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            if userinfo_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to fetch user info")
            userinfo = userinfo_resp.json()

            email: str = userinfo["email"]
            name: str = userinfo.get("name") or email.split("@")[0]
            subject: str = userinfo["sub"]

        else:  # github
            token_resp = await http.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "code": code,
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            if token_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Token exchange failed")
            gh_token = token_resp.json().get("access_token", "")
            if not gh_token:
                raise HTTPException(status_code=400, detail="Token exchange failed")

            profile_resp = await http.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {gh_token}", "Accept": "application/json"},
            )
            profile_resp.raise_for_status()
            profile = profile_resp.json()

            subject = str(profile["id"])
            name = profile.get("name") or profile.get("login") or "GitHub User"
            email = profile.get("email") or ""

            if not email:
                emails_resp = await http.get(
                    "https://api.github.com/user/emails",
                    headers={
                        "Authorization": f"token {gh_token}",
                        "Accept": "application/json",
                    },
                )
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

    logger.info("OAuth login successful: provider=%s user=%s", provider, email)
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
