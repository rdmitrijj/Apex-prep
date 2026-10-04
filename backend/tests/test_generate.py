import json
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select

from app.core.db import SessionLocal
from app.generate import BlindSolve, Pipeline, Stats, jaccard, ngrams, run, shuffle, strip_labels
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
        usage = SimpleNamespace(input_tokens=2_000, output_tokens=4_000)  # $0.088 per call at Opus 5.5 prices
        return SimpleNamespace(stop_reason="end_turn", parsed_output=out, usage=usage)


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


async def test_budget_cap_and_seed_file_export(tmp_path: Path) -> None:
    async with SessionLocal() as db:
        await seed(db)
    good = RWItem.model_validate(ITEM)
    fake = FakeClient([good, "RIGHT"] * 5)
    pipe = Pipeline(fake, "claude-opus-5-5")
    orig_generate = pipe.generate

    def generate(*a: Any) -> RWItem | None:
        item = orig_generate(*a)
        if item is not None:
            fake.outputs[0] = solve(item.answer)
        return item

    pipe.generate = generate  # type: ignore[method-assign]
    out = tmp_path / "llm.json"
    # Each item costs 2 calls = $0.176; a $0.10 budget allows one item, then stops before starting another.
    stats = await run(pipe, ["RW.SEC.BND.LINK"], 5, "medium", True, [good], budget_usd=0.10, out=out)
    assert stats.inserted == 1 and len(fake.calls) == 2
    assert round(pipe.cost, 3) == 0.176
    saved = [RWItem.model_validate(x) for x in json.loads(out.read_text())]
    assert len(saved) == 1 and saved[0].skill == "RW.SEC.BND.LINK"


def test_overlong_items_are_rejected_before_the_blind_solve() -> None:
    long = RWItem.model_validate({**ITEM, "passage": "word " * 120, "passage2": "word " * 60})
    fake = FakeClient([])
    stats = Stats()
    assert not Pipeline(fake, "m").check(long, [], stats)
    assert stats.rejected == {"too long": 1} and fake.calls == []


def test_strip_text_labels() -> None:
    item = RWItem.model_validate(
        {**ITEM, "passage": "Text 1: Some critics say a thing.", "passage2": "Text 2\nOthers disagree."}
    )
    s = strip_labels(item)
    assert s.passage == "Some critics say a thing." and s.passage2 == "Others disagree."
    assert strip_labels(RWItem.model_validate(ITEM)).passage == ITEM["passage"]


async def test_out_of_credits_stops_the_run() -> None:
    import anthropic
    import httpx

    async with SessionLocal() as db:
        await seed(db)

    class Broke(FakeClient):
        def parse(self, **kw: Any) -> Any:
            self.calls.append(kw)
            resp = httpx.Response(400, request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))
            raise anthropic.BadRequestError("Your credit balance is too low", response=resp, body=None)

    fake = Broke([])
    stats = await run(Pipeline(fake, "claude-opus-5-5"), ["RW.SEC.BND"], 5, "medium", True, [])
    assert stats.inserted == 0 and len(fake.calls) == 1  # stopped at the first refusal, no retries per item
