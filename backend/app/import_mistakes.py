"""`python -m app.import_mistakes --email you@example.com [--file PATH]`: load official-test mistakes
(paraphrases only) for one user. Idempotent: running it again changes nothing but edited text."""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.core.db import SessionLocal, engine
from app.models import User
from app.services import imported
from app.services.questions import SEED_DIR


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--email", required=True)
    ap.add_argument("--file", type=Path, default=SEED_DIR / "imports" / "bluebook_pt4.json")
    args = ap.parse_args()
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == args.email.lower()))
        if user is None:
            raise SystemExit(f"no user with email {args.email}")
        print("imported:", await imported.load(db, user.id, json.loads(args.file.read_text())))
    await engine.dispose()


asyncio.run(main())
