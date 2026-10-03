from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.deps import DB

router = APIRouter()


@router.get("/health")
async def health(db: DB) -> dict[str, str]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        raise HTTPException(503, "database unavailable") from e
    return {"status": "ok"}
