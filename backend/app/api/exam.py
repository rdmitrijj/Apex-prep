from datetime import timedelta

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.engine.exam import BREAK_SECONDS, domain_of
from app.generators.spr import is_valid_entry
from app.models import ExamItem, ExamModule, ExamSession, Question, Response, Skill
from app.schemas.exam import (
    BreakdownRow,
    ExamCreate,
    ExamItemOut,
    ExamResults,
    ExamState,
    ExamSummary,
    ItemSave,
    ModuleOut,
    ReviewItem,
)
from app.services import exam as ex
from app.services import questions as qs

router = APIRouter(prefix="/exams", tags=["exam"])
SECTION_NAME = {"RW": "Reading and Writing", "MATH": "Math"}


async def _session(db: DB, user_id: int, exam_id: int) -> ExamSession:
    sess = await db.get(ExamSession, exam_id)
    if sess is None or sess.user_id != user_id:
        raise HTTPException(404, "Exam not found")
    return sess


def _summary(sess: ExamSession, mods: list[ExamModule]) -> ExamSummary:
    return ExamSummary(
        id=sess.id,
        status=sess.status,
        difficulty=sess.difficulty_setting,
        sections=sorted({m.section for m in mods}, key=("RW", "MATH").index),  # type: ignore[arg-type]
        created_at=sess.created_at,
        completed_at=sess.completed_at,
        rw_score=sess.rw_score,
        math_score=sess.math_score,
    )


@router.post("", status_code=201)
async def create(body: ExamCreate, db: DB, user: CurrentUser) -> dict[str, int]:
    sess = await ex.create(db, user.id, body.difficulty, list(body.sections))
    return {"id": sess.id}


@router.get("", response_model=list[ExamSummary])
async def list_exams(db: DB, user: CurrentUser) -> list[ExamSummary]:
    sessions = (
        await db.scalars(
            select(ExamSession)
            .where(ExamSession.user_id == user.id, ExamSession.status != "abandoned")
            .order_by(ExamSession.created_at.desc())
        )
    ).all()
    out = []
    for s in sessions:
        if s.status == "in_progress":
            await ex.tick(db, s)  # a module may have timed out since the last visit
        out.append(_summary(s, await ex.modules_of(db, s.id)))
    return out


@router.get("/{exam_id}", response_model=ExamState)
async def state(exam_id: int, db: DB, user: CurrentUser) -> ExamState:
    sess = await _session(db, user.id, exam_id)
    mods = await ex.tick(db, sess)
    mod = ex.current(mods) if sess.status == "in_progress" else None
    out_mod = None
    break_ms = None
    if mod is not None:
        items: list[ExamItemOut] = []
        remaining = None
        if mod.started_at is not None:
            assert mod.deadline_at is not None
            remaining = max(0, int((mod.deadline_at - ex.now()).total_seconds() * 1000))
            names = await qs.skill_names(db)
            items = [
                ExamItemOut(
                    id=item.id,
                    position=item.position,
                    question=qs.public(q, names[q.skill_id]),
                    answer=r.answer if r else None,
                    flagged=r.flagged if r else False,
                    eliminated=r.eliminated if r else [],
                    time_ms=r.time_ms if r else 0,
                )
                for item, q, r in await ex.items_of(db, mod.id)
            ]
        else:
            prev = mods[mods.index(mod) - 1] if mods.index(mod) else None
            if prev and prev.section != mod.section and prev.submitted_at:
                left = prev.submitted_at + timedelta(seconds=BREAK_SECONDS) - ex.now()
                break_ms = max(0, int(left.total_seconds() * 1000))
        out_mod = ModuleOut(
            id=mod.id,
            section=mod.section,  # type: ignore[arg-type]
            stage=mod.stage,
            index=mods.index(mod) + 1,
            started=mod.started_at is not None,
            remaining_ms=remaining,
            items=items,
        )
    return ExamState(
        id=sess.id,
        status=sess.status,
        difficulty=sess.difficulty_setting,
        sections=_summary(sess, mods).sections,
        total_modules=len(mods),
        module=out_mod,
        break_remaining_ms=break_ms,
    )


@router.post("/{exam_id}/start", response_model=ExamState)
async def start_module(exam_id: int, db: DB, user: CurrentUser) -> ExamState:
    sess = await _session(db, user.id, exam_id)
    mod = ex.current(await ex.tick(db, sess))
    if sess.status != "in_progress" or mod is None:
        raise HTTPException(409, "This exam is over")
    if mod.started_at is None:
        mod.started_at = ex.now()
        mod.deadline_at = mod.started_at + timedelta(seconds=ex.module_seconds(mod.section))
        await db.commit()
    return await state(exam_id, db, user)


@router.put("/{exam_id}/items/{item_id}", status_code=204)
async def save_item(exam_id: int, item_id: int, body: ItemSave, db: DB, user: CurrentUser) -> None:
    sess = await _session(db, user.id, exam_id)
    mod = ex.current(await ex.tick(db, sess))
    item = await db.get(ExamItem, item_id)
    if mod is None or item is None or item.module_id != mod.id or mod.started_at is None:
        raise HTTPException(409, "This module is closed")
    answer = body.answer.strip() if body.answer else None
    if answer is not None:
        q = await db.get(Question, item.question_id)
        assert q is not None
        ok = answer in ("A", "B", "C", "D") if q.format == "mc" else is_valid_entry(answer)
        if not ok:
            raise HTTPException(422, "Invalid answer format")
    r = await db.scalar(select(Response).where(Response.exam_item_id == item.id))
    if r is None:
        r = Response(user_id=user.id, question_id=item.question_id, mode="exam", exam_item_id=item.id)
        db.add(r)
    r.answer, r.flagged, r.eliminated, r.time_ms = answer, body.flagged, list(body.eliminated), body.time_ms
    await db.commit()


@router.post("/{exam_id}/submit-module", response_model=ExamState)
async def submit_module(exam_id: int, db: DB, user: CurrentUser) -> ExamState:
    sess = await _session(db, user.id, exam_id)
    mods = await ex.tick(db, sess)
    mod = ex.current(mods)
    if sess.status == "in_progress" and mod is not None and mod.started_at is not None:
        await ex.close_module(db, sess, mod, mods)
    # Already closed (timer expiry or a double submit) is not an error: just return the new state.
    return await state(exam_id, db, user)


@router.get("/{exam_id}/results", response_model=ExamResults)
async def results(exam_id: int, db: DB, user: CurrentUser) -> ExamResults:
    sess = await _session(db, user.id, exam_id)
    mods = await ex.tick(db, sess)
    if sess.status != "completed":
        raise HTTPException(409, "Finish the exam to see results")
    names = await qs.skill_names(db)
    levels = dict((await db.execute(select(Skill.id, Skill.level))).all())
    items: list[ReviewItem] = []
    tally: dict[str, list[int]] = {}
    for m in mods:
        label = f"{SECTION_NAME[m.section]} · Module {m.stage}" + (f" ({m.route})" if m.route else "")
        for item, q, r in await ex.items_of(db, m.id):
            correct = bool(r and r.correct)
            if not item.pretest:
                for node in (domain_of(q.skill_id), ".".join(q.skill_id.split(".")[:3])):
                    t = tally.setdefault(node, [0, 0])
                    t[0] += correct
                    t[1] += 1
            items.append(
                ReviewItem(
                    module=label,
                    section=m.section,  # type: ignore[arg-type]
                    position=item.position,
                    pretest=item.pretest,
                    question=qs.public(q, names[q.skill_id]),
                    difficulty=q.difficulty,  # type: ignore[arg-type]
                    answer=r.answer if r else None,
                    correct=correct,
                    key=qs.grade(q, "")[1],
                    time_ms=r.time_ms if r else 0,
                    flagged=r.flagged if r else False,
                    explanation=q.content["explanation"],
                    rationales=q.content.get("rationales") or {},
                )
            )
    breakdown = [
        BreakdownRow(
            id=node,
            name=names[node],
            level=levels[node],
            section=node.split(".")[0],  # type: ignore[arg-type]
            correct=c,
            total=n,
        )
        for node, (c, n) in sorted(tally.items())
    ]
    return ExamResults(**_summary(sess, mods).model_dump(), breakdown=breakdown, items=items)
