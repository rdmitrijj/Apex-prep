"""`python -m app.seed`: load the taxonomy and seed bank (idempotent; runs on every deploy)."""

import asyncio

from app.core.db import SessionLocal, engine
from app.services.questions import seed


async def main() -> None:
    async with SessionLocal() as db:
        print("seeded:", await seed(db))
    await engine.dispose()


asyncio.run(main())
