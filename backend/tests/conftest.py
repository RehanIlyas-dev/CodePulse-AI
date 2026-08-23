import os
import sys
from pathlib import Path

# Keep test failures out of the real Sentry dashboard (load_dotenv won't
# override an existing value, so main.py sees an empty DSN and skips init)
os.environ["SENTRY_DSN"] = ""

# Make backend/ importable the same way uvicorn sees it (main.py, database.py, app/)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time

import pytest
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture
async def async_client():
    # --> Run the app's real lifespan (DB create_all + Redis init) around the client,
    # so tests exercise the same startup path as production
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    # pytest-asyncio uses a fresh event loop per test; pooled DB connections are
    # loop-bound, so drop them or the next test's lifespan hits "another
    # operation is in progress"
    from database import engine
    await engine.dispose()


@pytest.fixture
def redis_client():
    from app.core import redis as redis_module
    return redis_module.redis_client


@pytest.fixture
async def authed_client(async_client):
    """Client with a valid Bearer token for a throwaway user row."""
    import uuid as _uuid
    from datetime import datetime
    from sqlalchemy import String as _String, DateTime as _DateTime
    from database import AsyncSessionLocal
    from app.models.user import User
    from app.core.security import create_access_token

    async with AsyncSessionLocal() as db:
        user = User(
            email=f"test-{_uuid.uuid4().hex[:8]}@example.com",
            name="Test User",
            provider="test",
            provider_id=_uuid.uuid4().hex,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = create_access_token(user)
    async_client.headers.update({"Authorization": f"Bearer {token}"})
    yield async_client

    async with AsyncSessionLocal() as db:
        await db.delete(user)
        await db.commit()
