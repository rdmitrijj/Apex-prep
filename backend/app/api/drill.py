from fastapi import APIRouter, HTTPException
from sqlalchemy import case, func, select

from app.api.deps import DB, CurrentUser
from app.generators import REGISTRY
from app.generators.spr import is_valid_entry
from app.models import Question, QuestionReport, Response, Skill
from app.schemas.question import AnswerIn, Feedback, NextIn, QuestionOut, ReportIn, SkillNode
from app.services import questions as qs

router = APIRouter(tags=["drill"])


@router.get("/skills", response_model=list[SkillNode])
async def skills(db: DB, user: CurrentUser) -> list[SkillNode]:
    nodes = (await db.scalars(select(Skill))).all()
    available = dict(
        (
            await db.execute(
                select(Question.skill_id, func.count())
                .where(Question.status == "active", Question.source != "generator")
                .group_by(Question.skill_id)
            )
        ).all()
    )
    stats = {
        sid: (n, c)
        for sid, n, c in (
            await db.execute(
                select(Question.skill_id, func.count(), func.sum(case((Response.correct, 1), else_=0)))
                .join(Response, Response.question_id == Question.id)
                .where(Response.user_id == user.id)
                .group_by(Question.skill_id)
            )
        ).all()
    }
    out = []
    for s in nodes:
        leaves = [
            n.id for n in nodes if n.level == "subskill" and (n.id == s.id or n.id.startswith(s.id + "."))
        ]
        att = sum(stats.get(leaf, (0, 0))[0] for leaf in leaves)
        cor = sum(int(stats.get(leaf, (0, 0))[1] or 0) for leaf in leaves)
        out.append(
            SkillNode(
                id=s.id,
                parent_id=s.parent_id,
                name=s.name,
                level=s.level,
                section=s.section,
                weight=s.weight,
                generated=any(leaf in REGISTRY for leaf in leaves),
                available=sum(available.get(leaf, 0) for leaf in leaves),
                attempts=att,
                correct=cor,
            )
        )
    return out


@router.post("/drill/next", response_model=QuestionOut)
async def next_question(body: NextIn, db: DB, user: CurrentUser) -> QuestionOut:
    leaves = await qs.leaves_under(db, body.skill_ids)
    if not leaves:
        raise HTTPException(422, "Pick at least one skill")
    q = await qs.pick(db, user.id, leaves, body.difficulty, body.exclude_ids)
    if q is None:
        raise HTTPException(404, "No questions are available for this selection yet")
    skill = await db.get(Skill, q.skill_id)
    assert skill is not None
    return qs.public(q, skill.name)


@router.post("/drill/answer", response_model=Feedback)
async def answer(body: AnswerIn, db: DB, user: CurrentUser) -> Feedback:
    q = await db.get(Question, body.question_id)
    if q is None:
        raise HTTPException(404, "Question not found")
    if q.format == "spr" and not is_valid_entry(body.answer.strip()):
        raise HTTPException(
            422, "Enter a number, fraction (like 7/2), or decimal; at most 5 characters (6 if negative)"
        )
    correct, key = qs.grade(q, body.answer)
    db.add(
        Response(
            user_id=user.id,
            question_id=q.id,
            mode="drill",
            answer=body.answer.strip(),
            correct=correct,
            time_ms=body.time_ms,
        )
    )
    await db.commit()
    return Feedback(
        correct=correct,
        answer=key,
        explanation=q.content["explanation"],
        rationales=q.content.get("rationales") or {},
    )


@router.post("/questions/{question_id}/report", status_code=204)
async def report(question_id: int, body: ReportIn, db: DB, user: CurrentUser) -> None:
    q = await db.get(Question, question_id)
    if q is None:
        raise HTTPException(404, "Question not found")
    db.add(QuestionReport(user_id=user.id, question_id=q.id, reason=body.reason))
    q.status = "quarantined"
    await db.commit()
