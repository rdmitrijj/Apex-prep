"""PT6 Replay, practice mode: the twins in test order. Answers go through /drill/answer (instant
feedback, "same trap as PT6"); the timed mode is Triage's replayrw / replaymath."""

from typing import Literal

from fastapi import APIRouter

from app.api.deps import DB, CurrentUser
from app.schemas.question import QuestionOut
from app.services import pt6
from app.services import questions as qs

router = APIRouter(prefix="/pt6", tags=["pt6"])


@router.get("/replay", response_model=list[QuestionOut])
async def replay(db: DB, _: CurrentUser, section: Literal["rw", "math"] | None = None) -> list[QuestionOut]:
    names = await qs.skill_names(db)
    return [qs.public(q, names[q.skill_id]) for q in await pt6.replay(db, section)]
