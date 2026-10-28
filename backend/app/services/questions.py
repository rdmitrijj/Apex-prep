"""Question storage, selection, and grading (shared by drill, exams, and training)."""

import hashlib
import json
import random
import re
import secrets
from datetime import UTC, datetime, time
from fractions import Fraction
from pathlib import Path
from typing import Any

from sqlalchemy import exists, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine import srs
from app.generators import REGISTRY, generate
from app.generators.core import DIFFICULTY_RATING
from app.generators.spr import canonical_entry, is_correct
from app.models import Question, Response, ReviewSchedule, Skill
from app.schemas.question import MathItem, QuestionOut, RWItem, RWSeedItem

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
PUBLIC_KEYS = ("passage", "passage2", "notes", "figure")


def content_hash(content: dict[str, Any]) -> str:
    parts = [content.get(k) for k in ("passage", "passage2", "stem", "choices", "spr_answers")]
    norm = re.sub(r"\s+", " ", json.dumps(parts, sort_keys=True).lower())
    return hashlib.sha256(norm.encode()).hexdigest()


def rw_content(item: RWItem) -> dict[str, Any]:
    c = item.model_dump(
        exclude={"id", "modeled_on", "skill", "difficulty", "steps", "strategy_tip"}, exclude_none=True
    )
    steps = getattr(item, "steps", None) or [item.explanation]
    tip = getattr(item, "strategy_tip", None)
    c["explanation"] = [*steps, f"Strategy: {tip}"] if tip else steps
    return c


def math_content(item: MathItem) -> dict[str, Any]:
    return {
        "stem": item.stem,
        "choices": item.choices,
        "answer": item.answer,
        "spr_answers": item.spr_answers,
        "explanation": item.explanation,
        "rationales": item.rationales.model_dump() if item.rationales else {},
        "figure": item.figure,
    }


def load_taxonomy() -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = json.loads((SEED_DIR / "taxonomy.json").read_text())["nodes"]
    return nodes


def load_rw_seed() -> list[RWSeedItem]:
    items: list[RWSeedItem] = []
    for path in sorted((SEED_DIR / "rw").glob("*.json")):
        items += [RWSeedItem.model_validate(raw) for raw in json.loads(path.read_text())]
    return items


def load_math_seed() -> list[MathItem]:
    items: list[MathItem] = []
    for path in sorted((SEED_DIR / "math").glob("*.json")):
        items += [MathItem.model_validate(raw) for raw in json.loads(path.read_text())]
    return items


async def insert_question(
    db: AsyncSession, *, skill_id: str, fmt: str, difficulty: str, content: dict[str, Any], source: str
) -> int:
    h = content_hash(content)
    stmt = (
        insert(Question)
        .values(
            skill_id=skill_id,
            format=fmt,
            difficulty=difficulty,
            difficulty_rating=DIFFICULTY_RATING[difficulty],
            content=content,
            source=source,
            content_hash=h,
        )
        .on_conflict_do_nothing(index_elements=["content_hash"])
        .returning(Question.id)
    )
    qid = await db.scalar(stmt)
    if qid is None:
        qid = await db.scalar(select(Question.id).where(Question.content_hash == h))
    assert qid is not None
    return qid


def seed_items() -> list[tuple[str, str, str, str, dict[str, Any]]]:
    """(external_id, skill, format, difficulty, content) for every seed-file item."""
    out: list[tuple[str, str, str, str, dict[str, Any]]] = []
    for r in load_rw_seed():
        assert r.id, f"seed item without an id: {r.passage[:60]}"
        out.append((r.id, r.skill, "mc", r.difficulty, rw_content(r)))
    out += [(m.id, m.skill, m.format, m.difficulty, math_content(m)) for m in load_math_seed()]
    return out


async def seed(db: AsyncSession) -> dict[str, int]:
    """Idempotent: upsert the taxonomy, then every seed item by its external_id.

    An edited item updates its row in place (answers stay linked). Seed rows that are no longer in
    the files, e.g. old copies from before items had ids, are quarantined, never deleted.
    """
    for n in load_taxonomy():
        values = {
            "id": n["id"],
            "parent_id": n["parent"],
            "name": n["name"],
            "level": n["level"],
            "section": n["section"],
            "weight": n["weight"],
        }
        await db.execute(
            insert(Skill).values(**values).on_conflict_do_update(index_elements=["id"], set_=values)
        )
    items = seed_items()
    stored = {
        q.external_id: q for q in await db.scalars(select(Question).where(Question.external_id.is_not(None)))
    }
    changed = 0
    for eid, skill, fmt, diff, content in items:
        h = content_hash(content)
        q = stored.get(eid)
        if q is None:
            q = await db.scalar(select(Question).where(Question.content_hash == h))
            if q is not None and q.external_id is None:
                q.external_id = eid  # same text already stored (e.g. by the LLM pipeline)
                continue
            db.add(
                Question(
                    skill_id=skill,
                    format=fmt,
                    difficulty=diff,
                    difficulty_rating=DIFFICULTY_RATING[diff],
                    content=content,
                    source="seed",
                    content_hash=h,
                    external_id=eid,
                )
            )
            changed += 1
        elif (q.content, q.skill_id, q.format, q.difficulty) != (content, skill, fmt, diff):
            q.content, q.content_hash, q.skill_id, q.format = content, h, skill, fmt
            q.difficulty, q.difficulty_rating = diff, DIFFICULTY_RATING[diff]
            q.status = "active"  # an edit is the fix for whatever got it quarantined
            changed += 1
    await db.flush()
    ids = [eid for eid, *_ in items]
    stale = await db.execute(
        update(Question)
        .where(
            Question.source == "seed",
            Question.status == "active",
            Question.external_id.is_(None) | Question.external_id.not_in(ids),
        )
        .values(status="quarantined")
    )
    await db.commit()
    return {
        "skills": len(load_taxonomy()),
        "seed_items": len(items),
        "changed": changed,
        "retired": stale.rowcount,  # type: ignore[attr-defined]
    }


async def leaves_under(db: AsyncSession, ids: list[str]) -> list[str]:
    nodes = (await db.execute(select(Skill.id, Skill.level))).all()
    leaves = [nid for nid, level in nodes if level == "subskill"]
    return sorted({leaf for leaf in leaves for i in ids if leaf == i or leaf.startswith(i + ".")})


async def pick(
    db: AsyncSession, user_id: int, leaves: list[str], difficulty: str, exclude: list[int]
) -> Question | None:
    rng = random.Random(secrets.randbits(64))
    order = list(leaves)
    rng.shuffle(order)
    for leaf in order:
        diff = rng.choice(["easy", "medium", "hard"]) if difficulty == "mixed" else difficulty
        seen = exists().where(Response.user_id == user_id, Response.question_id == Question.id)
        if leaf in REGISTRY:
            # Hand-written items (twins of real mistakes) come first while unseen; then the generator.
            q = await db.scalar(
                select(Question)
                .where(
                    Question.skill_id == leaf,
                    Question.source == "seed",
                    Question.status == "active",
                    Question.difficulty == diff,
                    Question.id.not_in(exclude or [0]),
                    ~seen,
                )
                .order_by(func.random())
                .limit(1)
            )
            if q is not None:
                return q
            g = generate(leaf, diff, random.Random(secrets.randbits(64)))  # type: ignore[arg-type]
            qid = await insert_question(
                db, skill_id=leaf, fmt=g.format, difficulty=diff, content=g.content(), source="generator"
            )
            return await db.get(Question, qid)
        q = await db.scalar(
            select(Question)
            .where(Question.skill_id == leaf, Question.status == "active", Question.id.not_in(exclude or [0]))
            .order_by(seen, Question.difficulty != diff, func.random())
            .limit(1)
        )
        if q is not None:
            return q
    return None


async def record_review(db: AsyncSession, user_id: int, skill_id: str, correct: bool) -> None:
    """Advance or reset the skill's spaced-repetition schedule after a graded answer."""
    today = datetime.now(UTC).date()
    row = await db.get(ReviewSchedule, (user_id, skill_id))
    interval, due = srs.next_review(
        row.interval_days if row else None, row.due_at.date() if row else None, today, correct
    )
    due_at = datetime.combine(due, time(), tzinfo=UTC)
    if row is None:
        db.add(ReviewSchedule(user_id=user_id, skill_id=skill_id, interval_days=interval, due_at=due_at))
    else:
        row.interval_days, row.due_at = interval, due_at


async def skill_names(db: AsyncSession) -> dict[str, str]:
    return dict((await db.execute(select(Skill.id, Skill.name))).all())


def public(q: Question, skill_name: str) -> QuestionOut:
    c = q.content
    return QuestionOut(
        id=q.id,
        skill_id=q.skill_id,
        skill_name=skill_name,
        difficulty=q.difficulty,  # type: ignore[arg-type]
        format=q.format,  # type: ignore[arg-type]
        stem=c["stem"],
        choices=c.get("choices"),
        **{k: c.get(k) for k in PUBLIC_KEYS},
    )


def grade(q: Question, answer: str) -> tuple[bool, str]:
    """Returns (correct, the key as shown to the student)."""
    c = q.content
    if q.format == "mc":
        return answer.strip().upper() == c["answer"], c["answer"]
    keys = [Fraction(a) for a in c["spr_answers"]]
    return is_correct(answer, keys), canonical_entry(keys[0])
