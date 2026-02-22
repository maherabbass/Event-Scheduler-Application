import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, get_db
from app.main import app


@pytest_asyncio.fixture
async def db():
    try:
        session = AsyncSessionLocal()
        # Probe the connection eagerly so we skip before the test runs
        await session.execute(text("SELECT 1"))
    except Exception as e:
        await session.close()
        pytest.skip(f"Database not available: {e}")

    try:
        yield session
    finally:
        await session.rollback()
        await session.close()


@pytest_asyncio.fixture
async def client(db):
    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
