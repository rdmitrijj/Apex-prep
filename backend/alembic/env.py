import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.db import normalize_db_url
from app.models import Base

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)

s = get_settings()
# Migrations go through the direct (non-PgBouncer) endpoint when one is configured.
URL, CONNECT_ARGS = normalize_db_url(s.database_url_direct or s.database_url)


def _run(conn: Connection) -> None:
    context.configure(connection=conn, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


async def main() -> None:
    engine = create_async_engine(URL, connect_args=CONNECT_ARGS)
    async with engine.connect() as conn:
        await conn.run_sync(_run)
    await engine.dispose()


asyncio.run(main())
