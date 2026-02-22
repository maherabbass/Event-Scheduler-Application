"""Auth endpoint tests — no DB required."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def anon_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_me_unauthenticated(anon_client: AsyncClient) -> None:
    resp = await anon_client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(anon_client: AsyncClient) -> None:
    resp = await anon_client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not.a.valid.token"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unsupported_provider(anon_client: AsyncClient) -> None:
    resp = await anon_client.get("/api/v1/auth/login/twitter", follow_redirects=False)
    assert resp.status_code == 400
    assert "Unsupported provider" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_login_unconfigured_provider(anon_client: AsyncClient) -> None:
    """When credentials are empty strings the provider won't be in SUPPORTED_PROVIDERS."""
    from app.auth import oauth as oauth_module

    original = oauth_module.SUPPORTED_PROVIDERS.copy()
    oauth_module.SUPPORTED_PROVIDERS.discard("google")
    try:
        resp = await anon_client.get("/api/v1/auth/login/google", follow_redirects=False)
        assert resp.status_code == 503
        assert "not configured" in resp.json()["detail"]
    finally:
        oauth_module.SUPPORTED_PROVIDERS.update(original)
