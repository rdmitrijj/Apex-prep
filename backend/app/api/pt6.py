"""PT6 Replay and Twins+, practice mode: the twins in test order. Answers go through /drill/answer
(instant feedback, "same trap as PT6"); the timed modes are Triage's replay* / twin* modes."""

from typing import Literal

from fastapi import APIRouter

from app.api.deps import DB, CurrentUser
from app.schemas.question import QuestionOut
from app.services import pt6
from app.services import questions as qs

router = APIRouter(prefix="/pt6", tags=["pt6"])


@router.get("/replay", response_model=list[QuestionOut])
async def replay(
    db: DB,
    _: CurrentUser,
    section: Literal["rw", "math"] | None = None,
    kind: Literal["replay", "twin2", "twin3", "twins", "speed"] = "replay",
) -> list[QuestionOut]:
    """`kind=twins`: twin 2 and twin 3 of each record, side by side."""
    kinds = ("twin2", "twin3") if kind == "twins" else (kind,)
    names = await qs.skill_names(db)
    return [qs.public(q, names[q.skill_id]) for q in await pt6.replay(db, section, kinds)]
