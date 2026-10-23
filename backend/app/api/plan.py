from collections import Counter
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.api.training import compute
from app.engine import irt
from app.engine.goals import priority
from app.engine.plan import Focus, monday, week_plan
from app.models import ExamSession, Response, StudyPlan, User

router = APIRouter(tags=["plan"])
FOCUS_SIZE, MIN_PER_SECTION = 6, 2
# Answers needed in a day for a training/drill task to count as done.
DONE_AT = {"training": 15, "drill": 8}


def _zone(tz: str) -> ZoneInfo:
    try:
        return ZoneInfo(tz)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


async def _build(db: DB, user: User, week_start: Any, today: Any) -> dict[str, Any]:
    assert user.test_date is not None
    ranked = await compute(db, user)
    focus = ranked[:FOCUS_SIZE]
    for section in ("MATH", "RW"):
        have = [p for p in focus if p[1].section == section]
        extra = [p for p in ranked if p[1].section == section and p not in focus]
        for p in extra[: max(0, MIN_PER_SECTION - len(have))]:
            # Swap out the weakest pick from the over-represented section.
            other = [q for q in focus if q[1].section != section]
            focus.remove(other[-1])
            focus.append(p)
    focus.sort(key=lambda p: p[0].score, reverse=True)
    has_exam = (
        await db.scalar(
            select(ExamSession.id)
            .where(ExamSession.user_id == user.id, ExamSession.status == "completed")
            .limit(1)
        )
    ) is not None
    return week_plan(
        week_start,
        today,
        [Focus(s.id, s.name, s.section, irt.target_difficulty(w.theta)) for w, s in focus],
        has_exam,
        user.test_date,
        priority(user.section_targets),
    )


@router.get("/plan")
async def get_plan(db: DB, user: CurrentUser, tz: str = "UTC", rebuild: bool = False) -> dict[str, Any]:
    """This week's plan (built once per week, or on request), with tasks marked done from activity."""
    if user.test_date is None:
        raise HTTPException(409, "Set your test date and goals first")
    zone = _zone(tz)
    today = datetime.now(zone).date()
    week_start = monday(min(today, user.test_date))
    row = await db.scalar(
        select(StudyPlan).where(StudyPlan.user_id == user.id, StudyPlan.week_start == week_start)
    )
    if row is None or rebuild:
        plan = await _build(db, user, week_start, today)
        if row is None:
            row = StudyPlan(user_id=user.id, week_start=week_start, plan=plan)
            db.add(row)
        else:
            row.plan = plan
        await db.commit()

    start = datetime.combine(week_start, time(), tzinfo=zone).astimezone(UTC)
    end = start + timedelta(days=7)
    answers = Counter(
        (r.created_at.astimezone(zone).date().isoformat(), r.mode)
        for r in (
            await db.scalars(
                select(Response).where(
                    Response.user_id == user.id,
                    Response.created_at >= start,
                    Response.created_at < end,
                    Response.mode != "exam",
                )
            )
        ).all()
    )
    exams = {
        e.completed_at.astimezone(zone).date().isoformat()
        for e in (
            await db.scalars(
                select(ExamSession).where(
                    ExamSession.user_id == user.id,
                    ExamSession.status == "completed",
                    ExamSession.completed_at >= start,
                    ExamSession.completed_at < end,
                )
            )
        ).all()
        if e.completed_at
    }
    plan = dict(row.plan)
    plan["today"] = today.isoformat()
    plan["test_date"] = user.test_date.isoformat()
    plan["days"] = [
        {
            **day,
            "tasks": [
                {
                    **t,
                    "done": (
                        day["date"] in exams
                        if t["kind"] == "exam"
                        else answers[(day["date"], t["kind"])] >= DONE_AT[t["kind"]]
                        if t["kind"] in DONE_AT
                        else None
                    ),
                }
                for t in day["tasks"]
            ],
        }
        for day in plan["days"]
    ]
    return plan
