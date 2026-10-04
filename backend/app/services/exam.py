"""Practice-exam lifecycle: assemble modules, server-side timing, routing, scoring."""

import random
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import exam as bp
from app.engine import irt
from app.models import ExamItem, ExamModule, ExamSession, Question, Response, Skill
from app.services import questions as qs

# Autosaves that race the deadline by a network round-trip are still accepted.
GRACE = timedelta(seconds=3)


def now() -> datetime:
    return datetime.now(UTC)


def module_seconds(section: str) -> int:
    return bp.MODULE_SPEC[section][1]


async def modules_of(db: AsyncSession, session_id: int) -> list[ExamModule]:
    mods = (await db.scalars(select(ExamModule).where(ExamModule.session_id == session_id))).all()
    return sorted(mods, key=lambda m: (bp.SECTION_ORDER.index(m.section), m.stage))


async def items_of(db: AsyncSession, module_id: int) -> list[tuple[ExamItem, Question, Response | None]]:
    rows = (
        await db.execute(
            select(ExamItem, Question, Response)
            .join(Question, Question.id == ExamItem.question_id)
            .outerjoin(Response, Response.exam_item_id == ExamItem.id)
            .where(ExamItem.module_id == module_id)
            .order_by(ExamItem.position)
        )
    ).all()
    return [(i, q, r) for i, q, r in rows]


async def _assemble(db: AsyncSession, sess: ExamSession, mod: ExamModule, stage_key: str) -> None:
    rng = random.Random(secrets.randbits(64))
    leaves = [
        (s.id, s.weight)
        for s in (
            await db.scalars(select(Skill).where(Skill.level == "subskill", Skill.section == mod.section))
        ).all()
    ]
    used = list(
        await db.scalars(
            select(ExamItem.question_id).join(ExamModule).where(ExamModule.session_id == sess.id)
        )
    )
    picked: list[tuple[Question, bool]] = []
    for slot in bp.slots(mod.section, sess.difficulty_setting, stage_key, leaves, rng):  # type: ignore[arg-type]
        q = await qs.pick(db, sess.user_id, [slot.leaf], slot.difficulty, used)
        if q is None:  # sub-skill has no usable stored items: any sub-skill in the same domain
            domain_leaves = [leaf for leaf, _ in leaves if bp.domain_of(leaf) == slot.domain]
            q = await qs.pick(db, sess.user_id, domain_leaves, slot.difficulty, used)
        if q is None:
            raise RuntimeError(f"question bank has nothing left for {slot.domain}")
        used.append(q.id)
        picked.append((q, slot.pretest))
    ordering = bp.order(mod.section, [(q.skill_id, q.difficulty_rating) for q, _ in picked], rng)
    for pos, idx in enumerate(ordering, start=1):
        q, pretest = picked[idx]
        db.add(ExamItem(module_id=mod.id, position=pos, question_id=q.id, pretest=pretest))


async def create(db: AsyncSession, user_id: int, setting: str, sections: list[str]) -> ExamSession:
    for old in (
        await db.scalars(
            select(ExamSession).where(ExamSession.user_id == user_id, ExamSession.status == "in_progress")
        )
    ).all():
        old.status = "abandoned"
    sess = ExamSession(user_id=user_id, difficulty_setting=setting, status="in_progress")
    db.add(sess)
    await db.flush()
    mods = [ExamModule(session_id=sess.id, section=s, stage=st) for s in sections for st in (1, 2)]
    db.add_all(mods)
    await db.flush()
    for m in mods:
        if m.stage == 1:
            await _assemble(db, sess, m, "1")
    await db.commit()
    return sess


def current(mods: list[ExamModule]) -> ExamModule | None:
    return next((m for m in mods if m.submitted_at is None), None)


async def close_module(db: AsyncSession, sess: ExamSession, mod: ExamModule, mods: list[ExamModule]) -> None:
    """Lock the module, grade it (blanks are wrong), route Module 2, and finish the exam if done."""
    mod.submitted_at = now()
    scored: list[tuple[float, bool]] = []
    for item, q, r in await items_of(db, mod.id):
        if r is None:
            r = Response(user_id=sess.user_id, question_id=q.id, mode="exam", exam_item_id=item.id)
            r.time_ms, r.flagged, r.eliminated = 0, False, []
            db.add(r)
        r.correct = r.answer is not None and qs.grade(q, r.answer)[0]
        if not item.pretest:
            scored.append((q.difficulty_rating, r.correct))
    if mod.stage == 1:
        nxt = next(m for m in mods if m.section == mod.section and m.stage == 2)
        nxt.route = irt.route(scored)
        await _assemble(db, sess, nxt, nxt.route)
    if current(mods) is None:
        await db.flush()
        await _finish(db, sess, mods)
    await db.commit()


async def _finish(db: AsyncSession, sess: ExamSession, mods: list[ExamModule]) -> None:
    for section in {m.section for m in mods}:
        scored: list[tuple[float, bool]] = []
        for m in mods:
            if m.section == section:
                scored += [
                    (q.difficulty_rating, bool(r and r.correct))
                    for item, q, r in await items_of(db, m.id)
                    if not item.pretest
                ]
        route = next(m.route for m in mods if m.section == section and m.stage == 2)
        score = irt.section_score(scored, route)
        if section == "RW":
            sess.rw_score = score
        else:
            sess.math_score = score
    sess.status = "completed"
    sess.completed_at = now()


async def tick(db: AsyncSession, sess: ExamSession) -> list[ExamModule]:
    """Close a module whose time ran out (the server, not the client, enforces the deadline)."""
    mods = await modules_of(db, sess.id)
    mod = current(mods)
    if sess.status == "in_progress" and mod and mod.deadline_at and now() > mod.deadline_at + GRACE:
        await close_module(db, sess, mod, mods)
    return mods
