from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_ASYNCPG_SSL_MODES = {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}


def normalize_db_url(url: str) -> tuple[str, dict[str, Any]]:
    """Turn a libpq-style URL (e.g. Neon's) into an asyncpg URL + connect_args.

    asyncpg rejects `sslmode` and `channel_binding` query params, so they are stripped and
    sslmode is passed as `ssl`. Neon pooled hosts (`-pooler`) run PgBouncer in transaction
    mode, which breaks prepared-statement caching, so both caches are disabled there.
    """
    parts = urlsplit(url)
    scheme = "postgresql+asyncpg"
    query = dict(parse_qsl(parts.query))
    connect_args: dict[str, Any] = {}
    sslmode = query.pop("sslmode", None)
    query.pop("channel_binding", None)
    if sslmode in _ASYNCPG_SSL_MODES:
        connect_args["ssl"] = sslmode
    if "-pooler" in (parts.hostname or ""):
        connect_args["statement_cache_size"] = 0
        query["prepared_statement_cache_size"] = "0"
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)), connect_args


def _make_engine(url: str):  # type: ignore[no-untyped-def]
    async_url, connect_args = normalize_db_url(url)
    return create_async_engine(async_url, connect_args=connect_args, pool_pre_ping=True)


engine = _make_engine(get_settings().database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
