import re
from collections import Counter

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models import Question
from app.services.questions import content_hash, load_rw_seed, load_taxonomy, rw_content, seed

ITEMS = load_rw_seed()  # validates every item against the RWItem schema
HIGH_WEIGHT = ("RW.CAS.WIC.", "RW.SEC.", "RW.EOI.", "RW.INI.COET.", "RW.INI.COEQ.")


def test_coverage_targets() -> None:
    counts = Counter(i.skill for i in ITEMS)
    leaves = [n["id"] for n in load_taxonomy() if n["level"] == "subskill" and n["section"] == "RW"]
    assert set(counts) <= set(leaves), set(counts) - set(leaves)
    for leaf in leaves:
        need = 10 if leaf.startswith(HIGH_WEIGHT) else 9
        assert counts[leaf] >= need, (leaf, counts[leaf])


def test_items_are_consistent() -> None:
    letters = Counter(i.answer for i in ITEMS)
    assert all(0.15 <= letters[c] / len(ITEMS) <= 0.35 for c in "ABCD"), letters
    hashes = [content_hash(rw_content(i)) for i in ITEMS]
    assert len(set(hashes)) == len(hashes), "duplicate items"
    for i in ITEMS:
        r = i.rationales.model_dump()
        assert r[i.answer].startswith("Correct."), i.passage[:50]
        assert not any(v.startswith("Correct.") for k, v in r.items() if k != i.answer), i.passage[:50]
        assert len(i.passage.split()) + len((i.passage2 or "").split()) <= 170, i.passage[:50]
        text = " ".join([i.passage, i.passage2 or "", i.stem, *i.choices, *(i.notes or [])])
        assert not re.search(r"\b(SAT|College Board|Bluebook)\b", text), i.passage[:50]
        if i.skill.startswith(("RW.SEC.", "RW.CAS.WIC.FILL", "RW.EOI.TRN.", "RW.INI.COEQ.")):
            assert "______" in i.passage, i.passage[:50]


async def test_seed_is_idempotent() -> None:
    async with SessionLocal() as db:
        await seed(db)
        n1 = await db.scalar(select(func.count()).select_from(Question))
        await seed(db)
        n2 = await db.scalar(select(func.count()).select_from(Question))
    assert n1 == n2 == len(ITEMS)
