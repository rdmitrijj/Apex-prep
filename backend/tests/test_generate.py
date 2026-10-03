import random
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select

from app.core.db import SessionLocal
from app.generate import BlindSolve, Pipeline, jaccard, ngrams, run, shuffle
from app.models import Question
from app.schemas.question import RWItem
from app.services.questions import seed

ITEM = {
    "skill": "RW.SEC.BND.LINK",
    "difficulty": "medium",
    "passage": "Tardigrades survive drying out by forming a glass-like ______ protects their cells until water returns.",
    "stem": "Which choice completes the text so that it conforms to the conventions of Standard English?",
    "choices": [
        "matrix, this matrix",
        "matrix this matrix",
        "matrix; this matrix",
        "matrix, consequently, this matrix",
    ],
    "answer": "C",
    "explanation": "Two independent clauses can be joined with a semicolon.",
    "rationales": {"A": "Comma splice.", "B": "Run-on.", "C": "Correct. Semicolon.", "D": "Comma splice."},
}


class FakeClient:
    """Stands in for anthropic.Anthropic: returns queued parsed outputs in order."""

    def __init__(self, outputs: list[Any]) -> None:
        self.outputs = outputs
        self.calls: list[dict[str, Any]] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

    def parse(self, **kw: Any) -> Any:
        self.calls.append(kw)
        out = self.outputs.pop(0)
        if out == "refusal":
            return SimpleNamespace(
                stop_reason="refusal", stop_details=SimpleNamespace(category="cyber"), parsed_output=None
            )
        return SimpleNamespace(stop_reason="end_turn", parsed_output=out)


def solve(answer: str, *, ambiguous: bool = False, confident: bool = True) -> BlindSolve:
    return BlindSolve(answer=answer, justification="x", confident=confident, ambiguous=ambiguous)  # type: ignore[arg-type]


def test_ngram_jaccard() -> None:
    a = ngrams("The quick brown fox jumps over the lazy dog.")
    assert jaccard(a, ngrams("the quick  brown fox jumps over the lazy dog")) == 1.0
    assert jaccard(a, ngrams("Photosynthesis converts light into chemical energy.")) < 0.1


def test_shuffle_keeps_key_and_rationales_aligned() -> None:
    item = RWItem.model_validate(ITEM)
    for seed_ in range(20):
        s = shuffle(item, random.Random(seed_))
        assert s.choices[" ABCD".index(s.answer) - 1] == "matrix; this matrix"
        assert getattr(s.rationales, s.answer).startswith("Correct.")
        assert sorted(s.choices) == sorted(item.choices)


async def test_pipeline_accepts_verified_and_rejects_bad_items() -> None:
    async with SessionLocal() as db:
        await seed(db)
    good = RWItem.model_validate(ITEM)
    other = RWItem.model_validate(
        {
            **ITEM,
            "passage": "Bats in Texas forage far from the roost; GPS tags ______ showed trips of sixty kilometers.",
        }
    )
    fake = FakeClient(
        [
            good,
            None,  # blind solve returns nothing -> rejected
            good,
            "refusal",  # safeguard refusal on solve -> rejected
            good,
            solve("A", ambiguous=True),  # ambiguous -> rejected
            good,
            "WRONG",  # blind solver disagrees with the key -> rejected
            good,
            "RIGHT",  # accepted
            good,
            "RIGHT",  # near duplicate of the accepted one -> rejected
            other,
            "RIGHT",  # accepted
        ]
    )
    pipe = Pipeline(fake, "test-model")
    orig_generate = pipe.generate

    def generate(*a: Any) -> RWItem | None:
        item = orig_generate(*a)
        # Keys are shuffled after generation, so resolve RIGHT/WRONG solver outputs against the actual key.
        if item is not None and fake.outputs[0] == "RIGHT":
            fake.outputs[0] = solve(item.answer)
        elif item is not None and fake.outputs[0] == "WRONG":
            fake.outputs[0] = solve(next(c for c in "ABCD" if c != item.answer))
        return item

    pipe.generate = generate  # type: ignore[method-assign]
    stats = await run(pipe, ["RW.SEC.BND.LINK"], 7, "medium", dry_run=False, seed_items=[good])
    assert stats.inserted == 2
    assert stats.rejected == {
        "blind solve failed: end_turn": 1,
        "blind solve failed: refusal (cyber)": 1,
        "ambiguous": 1,
        "answer mismatch": 1,
        "near duplicate": 1,
    }
    async with SessionLocal() as db:
        rows = (await db.scalars(select(Question).where(Question.source == "llm"))).all()
        assert len(rows) == 2 and all(r.skill_id == "RW.SEC.BND.LINK" for r in rows)
    # Generation calls carry the key-free style examples and the fallback beta; solve calls never see the key.
    gen_call, solve_call = fake.calls[0], fake.calls[1]
    assert "fallbacks" in gen_call and "server-side-fallback-2026-07-01" in gen_call["betas"]
    assert "Correct." not in solve_call["messages"][0]["content"]
