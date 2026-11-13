"""PT5 Weakness Drill: mini-sets with rule cards and mastery, and the 5-day plan checklist.
Answers go through /drill/answer, which updates the set's review schedule."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import DB, CurrentUser
from app.engine import weakset as ws
from app.models import ImportedMistake, PlanCheck, Question, Response, SetReview
from app.schemas.question import QuestionOut
from app.services import pt5
from app.services import questions as qs

router = APIRouter(prefix="/pt5", tags=["pt5"])
ORDER = {"easy": 0, "medium": 1, "hard": 2}


class SetOut(BaseModel):
    id: str
    name: str
    section: str
    priority: int
    count: int
    answered: int
    recent_correct: int
    recent_total: int
    days: int
    mastered: bool
    progress: float
    review_due_at: datetime | None  # set once mastered
    review_due: bool
    miss_reason: str
    rule: str  # Markdown rule card


class SetsOut(BaseModel):
    readiness: float
    sets: list[SetOut]


class NextIn(BaseModel):
    exclude_ids: list[int] = Field(default_factory=list, max_length=200)


class NextOut(BaseModel):
    question: QuestionOut
    position: int  # 1-based within this pass
    total: int


class PlanItem(BaseModel):
    key: str
    text: str
    link: str | None
    done: bool


class PlanDay(BaseModel):
    date: str
    title: str
    items: list[PlanItem]


class PlanOut(BaseModel):
    visible: bool  # only for users with PT5 imports
    title: str
    days: list[PlanDay]


class CheckIn(BaseModel):
    done: bool


async def _sets(db: DB, user_id: int) -> list[SetOut]:
    hist = await pt5.history(db, user_id)
    reviews = {r.set_id: r for r in await db.scalars(select(SetReview).where(SetReview.user_id == user_id))}
    now = datetime.now(UTC)
    out = []
    for sid, s in pt5.sets().items():
        st = ws.status(hist.get(sid, []))
        rev = reviews.get(sid)
        out.append(
            SetOut(
                id=sid,
                name=s["name"],
                section=s["section"],
                priority=s["priority"],
                count=s["count"],
                answered=st.answered,
                recent_correct=st.recent_correct,
                recent_total=st.recent_total,
                days=st.days,
                mastered=st.mastered or rev is not None,
                progress=1.0 if rev is not None else st.progress,
                review_due_at=rev.due_at if rev else None,
                review_due=rev is not None and rev.due_at <= now,
                miss_reason=s["miss_reason"],
                rule=pt5.rule(sid),
            )
        )
    return out


@router.get("/sets", response_model=SetsOut)
async def list_sets(db: DB, user: CurrentUser) -> SetsOut:
    rows = await _sets(db, user.id)
    return SetsOut(readiness=ws.readiness([r.progress for r in rows]), sets=rows)


@router.post("/sets/{set_id}/next", response_model=NextOut)
async def next_question(set_id: str, body: NextIn, db: DB, user: CurrentUser) -> NextOut:
    """Unseen questions first, medium before hard; then the least recently answered."""
    if set_id not in pt5.sets():
        raise HTTPException(404, "No such set")
    items = (
        await db.scalars(
            select(Question).where(Question.external_id.like(f"pt5-{set_id}-%"), Question.status == "active")
        )
    ).all()
    last = dict(
        (
            await db.execute(
                select(Response.question_id, func.max(Response.created_at))
                .where(Response.user_id == user.id, Response.question_id.in_([q.id for q in items]))
                .group_by(Response.question_id)
            )
        ).all()
    )
    epoch = datetime.min.replace(tzinfo=UTC)
    order = sorted(
        items, key=lambda q: (q.id in last, last.get(q.id, epoch), ORDER[q.difficulty], q.external_id or "")
    )
    left = [q for q in order if q.id not in body.exclude_ids]
    if not left:
        raise HTTPException(404, "You've answered every question in this set")
    q = left[0]
    return NextOut(
        question=qs.public(q, (await qs.skill_names(db))[q.skill_id]),
        position=len(body.exclude_ids) + 1,
        total=len(items),
    )


@router.get("/plan", response_model=PlanOut)
async def get_plan(db: DB, user: CurrentUser) -> PlanOut:
    p = pt5.plan()
    visible = await db.scalar(
        select(ImportedMistake.id)
        .where(ImportedMistake.user_id == user.id, ImportedMistake.external_id.like("bb-pt5-%"))
        .limit(1)
    )
    done = set(await db.scalars(select(PlanCheck.item_key).where(PlanCheck.user_id == user.id)))
    days = [
        PlanDay(
            date=d["date"],
            title=d["title"],
            items=[PlanItem(**i, done=i["key"] in done) for i in d["items"]],
        )
        for d in p["days"]
    ]
    return PlanOut(visible=visible is not None, title=p["title"], days=days)


@router.put("/plan/{key}", status_code=204)
async def check(key: str, body: CheckIn, db: DB, user: CurrentUser) -> None:
    if key not in {i["key"] for d in pt5.plan()["days"] for i in d["items"]}:
        raise HTTPException(404, "No such plan item")
    if body.done:
        await db.execute(insert(PlanCheck).values(user_id=user.id, item_key=key).on_conflict_do_nothing())
    else:
        await db.execute(delete(PlanCheck).where(PlanCheck.user_id == user.id, PlanCheck.item_key == key))
    await db.commit()
