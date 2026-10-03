import os

# Must be set before app modules create the engine.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://apex:apex@localhost:5432/apex_test"
)
os.environ["SECRET_KEY"] = "test-secret-" + "x" * 32

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
async def _schema() -> None:
    url = os.environ["DATABASE_URL"]
    admin, dbname = url.rsplit("/", 1)
    conn = await asyncpg.connect(f"{admin}/postgres")
    if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname):
        await conn.execute(f'CREATE DATABASE "{dbname}"')
    await conn.close()
    async with engine.begin() as c:
        await c.run_sync(Base.metadata.drop_all)
        await c.run_sync(Base.metadata.create_all)


@pytest.fixture(autouse=True)
async def _clean() -> None:
    async with engine.begin() as c:
        for table in reversed(Base.metadata.sorted_tables):
            await c.execute(table.delete())


@pytest.fixture
async def client() -> AsyncClient:
    # https base URL so the Secure session cookie is sent back.
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as c:
        yield c
