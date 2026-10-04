"""Question storage, selection, and grading (shared by drill, exams, and training)."""

import hashlib
import json
import random
import re
import secrets
from fractions import Fraction
from pathlib import Path
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.generators import REGISTRY, generate
from app.generators.core import DIFFICULTY_RATING
from app.generators.spr import canonical_entry, is_correct
from app.models import Question, Response, Skill
from app.schemas.question import QuestionOut, RWItem

SEED_DIR = Path(__file__).resolve().parents[1] / "seed"
PUBLIC_KEYS = ("passage", "passage2", "notes", "figure")


def content_hash(content: dict[str, Any]) -> str:
    parts = [content.get(k) for k in ("passage", "passage2", "stem", "choices", "spr_answers")]
    norm = re.sub(r"\s+", " ", json.dumps(parts, sort_keys=True).lower())
    return hashlib.sha256(norm.encode()).hexdigest()


def rw_content(item: RWItem) -> dict[str, Any]:
    c = item.model_dump(exclude={"skill", "difficulty"}, exclude_none=True)
    c["explanation"] = [item.explanation]
    return c


def load_taxonomy() -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = json.loads((SEED_DIR / "taxonomy.json").read_text())["nodes"]
    return nodes


def load_rw_seed() -> list[RWItem]:
    items: list[RWItem] = []
    for path in sorted((SEED_DIR / "rw").glob("*.json")):
        items += [RWItem.model_validate(raw) for raw in json.loads(path.read_text())]
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


async def seed(db: AsyncSession) -> dict[str, int]:
    """Idempotent: upsert the taxonomy, insert any seed-bank items not already stored."""
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
    items = load_rw_seed()
    for item in items:
        await insert_question(
            db,
            skill_id=item.skill,
            fmt="mc",
            difficulty=item.difficulty,
            content=rw_content(item),
            source="seed",
        )
    await db.commit()
    return {"skills": len(load_taxonomy()), "seed_items": len(items)}


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
        if leaf in REGISTRY:
            g = generate(leaf, diff, random.Random(secrets.randbits(64)))  # type: ignore[arg-type]
            qid = await insert_question(
                db, skill_id=leaf, fmt=g.format, difficulty=diff, content=g.content(), source="generator"
            )
            return await db.get(Question, qid)
        seen = exists().where(Response.user_id == user_id, Response.question_id == Question.id)
        q = await db.scalar(
            select(Question)
            .where(Question.skill_id == leaf, Question.status == "active", Question.id.not_in(exclude or [0]))
            .order_by(seen, Question.difficulty != diff, func.random())
            .limit(1)
        )
        if q is not None:
            return q
    return None


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
