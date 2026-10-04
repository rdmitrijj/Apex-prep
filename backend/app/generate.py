"""R&W question generation: `python -m app.generate rw --skill RW.SEC --n 3 [--difficulty hard] [--dry-run]`.

Pipeline per item: generate (strict JSON schema, seed items as style examples) -> blind solve by a
fresh call that never sees the key -> reject on mismatch/ambiguity/low confidence -> reject near
duplicates (character 5-gram Jaccard against stored passages of the same skill) -> insert as source='llm'.
Runs locally or from the manual GitHub Action; the web app only serves stored questions.
"""

import argparse
import asyncio
import json
import random
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import anthropic
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal, engine
from app.models import Question
from app.schemas.question import RWItem
from app.services.questions import insert_question, leaves_under, load_rw_seed, load_taxonomy, rw_content

DUP_THRESHOLD = 0.5
MAX_WORDS = 170  # both texts together; the official stimulus is 25-150 words (tests enforce the same cap)
# USD per million (input, output) tokens; unknown models are priced at the top tier to stay safe.
PRICES = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0)}
TOP_PRICE = (10.0, 50.0)
FALLBACK_BETA = "server-side-fallback-2026-07-01"
TOPICS = [
    "natural science",
    "social science",
    "history",
    "literature (prose or poetry)",
    "the arts",
    "technology",
    "economics",
    "linguistics",
]

STEMS = {
    "RW.CAS.WIC.FILL": "Which choice completes the text with the most logical and precise word or phrase?",
    "RW.CAS.WIC.MEANING": 'As used in the text, what does the word "___" most nearly mean?',
    "RW.CAS.TSP.PURPOSE": "Which choice best describes the main purpose of the text?",
    "RW.CAS.TSP.STRUCTURE": "Which choice best describes the overall structure of the text?",
    "RW.CAS.TSP.FUNCTION": "Which choice best describes the function of the underlined sentence in the text as a whole?",
    "RW.CAS.CTC": "Based on the texts, how would the author of Text 2 most likely respond to ... in Text 1?",
    "RW.INI.CID.MAIN": "Which choice best states the main idea of the text?",
    "RW.INI.CID.DETAIL": "According to the text, ...?",
    "RW.INI.COET.SUPPORT": "Which finding, if true, would most directly support the researcher's claim?",
    "RW.INI.COET.WEAKEN": "Which finding, if true, would most directly weaken the researcher's hypothesis?",
    "RW.INI.COET.QUOTE": "Which quotation from [an invented work] most effectively illustrates the claim?",
    "RW.INI.COEQ": "Which choice most effectively uses data from the table/graph to complete the statement?",
    "RW.INI.INF": "Which choice most logically completes the text?",
    "RW.SEC": "Which choice completes the text so that it conforms to the conventions of Standard English?",
    "RW.EOI.RS": "While researching a topic, a student has taken the following notes: ... The student wants to [goal]. Which choice most effectively uses relevant information from the notes to accomplish this goal?",
    "RW.EOI.TRN": "Which choice completes the text with the most logical transition?",
}

SYSTEM = """You write original practice items for the Reading and Writing section of the digital SAT.

Rules:
- Every passage is original. You may invent researchers, studies, and literary works, but keep facts plausible and don't misstate real well-known facts. Never mention the SAT, College Board, or any test maker.
- Vary invented names (across cultures and regions), places, and settings; don't reuse names from the style examples.
- One short passage (25-150 words) per item, academic register, on the requested topic area. Cross-text items have two texts. Rhetorical synthesis items put 4-6 factual bullet notes in `notes` and use `passage` for a one-sentence framing of the student's research.
- Exactly one choice is defensibly correct; a careful expert would agree without hesitation. Each distractor is tempting for a specific reason (e.g. true but irrelevant, too broad, reverses the relationship, wrong punctuation rule) and clearly wrong on inspection.
- Use "______" for a blank in the passage and <u>...</u> to underline a sentence or phrase. Use plain text; no Markdown.
- Quantitative-evidence items include a `figure` (table, bars, or line) whose numbers the correct answer cites accurately; distractors misread or misuse the data.
- Difficulty: easy = familiar vocabulary and an obvious key; medium = denser text and closer distractors; hard = sophisticated text, subtle distinctions, distractors that are partly right.
- `explanation` says why the key is correct. `rationales` gives one sentence per choice; the key's starts with "Correct." and each distractor's names the flaw.
- Put the answer in a random position; don't favor any letter."""


class BlindSolve(BaseModel):
    # Keep this a short justification: a field named like "reasoning" trips the reasoning-extraction safeguard.
    model_config = ConfigDict(extra="forbid")
    answer: Literal["A", "B", "C", "D"]
    justification: str
    confident: bool
    ambiguous: bool


def ngrams(text: str, n: int = 5) -> set[str]:
    t = re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", text.lower()))
    return {t[i : i + n] for i in range(max(1, len(t) - n + 1))}


def jaccard(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a and b else 0.0


def item_text(content: dict[str, Any]) -> str:
    return " ".join(
        [content.get("passage") or "", content.get("passage2") or "", *(content.get("notes") or [])]
    )


def stem_hint(skill: str) -> str:
    for prefix in sorted(STEMS, key=len, reverse=True):
        if skill.startswith(prefix):
            return STEMS[prefix]
    return ""


def strip_labels(item: RWItem) -> RWItem:
    """The renderer prints "Text 1"/"Text 2" headings itself; drop labels the model put in the text."""

    def clean(t: str | None) -> str | None:
        return re.sub(r"^\s*Text [12]\s*[:.\-]?\s*", "", t) if t else t

    return item.model_copy(update={"passage": clean(item.passage), "passage2": clean(item.passage2)})


def shuffle(item: RWItem, rng: random.Random) -> RWItem:
    """Models favor some answer letters; re-deal the choices (and their rationales) uniformly."""
    order = list(range(4))
    rng.shuffle(order)
    letters = "ABCD"
    old = item.rationales.model_dump()
    return item.model_copy(
        update={
            "choices": [item.choices[i] for i in order],
            "answer": letters[order.index(letters.index(item.answer))],
            "rationales": item.rationales.model_validate(
                {letters[j]: old[letters[i]] for j, i in enumerate(order)}
            ),
        }
    )


def gen_prompt(skill: str, name: str, difficulty: str, examples: list[RWItem], topic: str) -> str:
    ex = "\n".join(e.model_dump_json(exclude_none=True) for e in examples) or "(none yet)"
    return (
        f"Write one new {difficulty} item for sub-skill {skill}: {name}.\n"
        f"Topic area: {topic}.\nTypical question wording: {stem_hint(skill)}\n"
        f"Set skill to {skill!r} and difficulty to {difficulty!r}.\n\n"
        f"Style examples (match their format and quality; don't reuse their content):\n{ex}"
    )


def solve_prompt(item: RWItem) -> str:
    parts = []
    if item.passage2:
        parts += [f"Text 1:\n{item.passage}", f"Text 2:\n{item.passage2}"]
    else:
        parts.append(item.passage)
    if item.notes:
        parts.append("Notes:\n" + "\n".join(f"- {n}" for n in item.notes))
    if item.figure:
        parts.append("Figure (JSON):\n" + item.figure.model_dump_json(exclude_none=True))
    parts.append(item.stem)
    parts += [f"{L}) {c}" for L, c in zip("ABCD", item.choices, strict=True)]
    return (
        "\n\n".join(parts)
        + "\n\nAnswer this multiple-choice question with a one-sentence justification. Set `ambiguous` if more "
        "than one choice is defensible or none is; set `confident` only if you are sure."
    )


@dataclass
class Stats:
    inserted: int = 0
    rejected: dict[str, int] = field(default_factory=dict)

    def reject(self, why: str) -> None:
        self.rejected[why] = self.rejected.get(why, 0) + 1


class Pipeline:
    def __init__(self, client: Any, model: str) -> None:
        self.client = client
        self.model = model
        self.last_stop = ""
        self.input_tokens = 0
        self.output_tokens = 0

    @property
    def cost(self) -> float:
        pin, pout = PRICES.get(self.model, TOP_PRICE)
        return (self.input_tokens * pin + self.output_tokens * pout) / 1e6

    def _call(self, system: str, prompt: str, schema: type[BaseModel]) -> Any:
        resp = self.client.beta.messages.parse(
            model=self.model,
            max_tokens=16000,
            betas=[FALLBACK_BETA],
            fallbacks="default",
            output_config={"effort": "high"},
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_format=schema,
        )
        self.last_stop = resp.stop_reason
        usage = getattr(resp, "usage", None)
        if usage is not None:
            self.input_tokens += usage.input_tokens or 0
            self.output_tokens += usage.output_tokens or 0
        if resp.stop_reason == "refusal":
            details = getattr(resp, "stop_details", None)
            self.last_stop = f"refusal ({getattr(details, 'category', None)})"
            return None
        if resp.stop_reason == "max_tokens":
            return None
        return resp.parsed_output

    def generate(
        self, skill: str, name: str, difficulty: str, examples: list[RWItem], topic: str
    ) -> RWItem | None:
        item = self._call(SYSTEM, gen_prompt(skill, name, difficulty, examples, topic), RWItem)
        if item is None:
            return None
        item = strip_labels(item.model_copy(update={"skill": skill, "difficulty": difficulty}))
        return shuffle(item, random.Random())

    def blind_solve(self, item: RWItem) -> BlindSolve | None:
        return self._call("You are a careful, expert test taker.", solve_prompt(item), BlindSolve)  # type: ignore[no-any-return]

    def check(self, item: RWItem, existing: list[set[str]], stats: Stats) -> bool:
        if len(item.passage.split()) + len((item.passage2 or "").split()) > MAX_WORDS:
            stats.reject("too long")
            return False
        solved = self.blind_solve(item)
        if solved is None:
            stats.reject(f"blind solve failed: {self.last_stop}")
            return False
        if solved.ambiguous or not solved.confident:
            stats.reject("ambiguous")
            return False
        if solved.answer != item.answer:
            stats.reject("answer mismatch")
            return False
        grams = ngrams(item_text(rw_content(item)))
        if any(jaccard(grams, g) >= DUP_THRESHOLD for g in existing):
            stats.reject("near duplicate")
            return False
        existing.append(grams)
        return True


async def run(
    pipe: Pipeline,
    skill_ids: list[str],
    n: int,
    difficulty: str,
    dry_run: bool,
    seed_items: list[RWItem],
    budget_usd: float | None = None,
    out: Path | None = None,
) -> Stats:
    names = {node["id"]: node["name"] for node in load_taxonomy()}
    stats = Stats()
    rng = random.Random()
    async with SessionLocal() as db:
        leaves = [leaf for leaf in await leaves_under(db, skill_ids) if leaf.startswith("RW.")]
        if not leaves:
            raise SystemExit(f"No R&W sub-skills under {skill_ids} (did you run `python -m app.seed`?)")
        for leaf in leaves:
            rows = (await db.scalars(select(Question.content).where(Question.skill_id == leaf))).all()
            existing = [ngrams(item_text(c)) for c in rows]
            pool = [s for s in seed_items if s.skill == leaf]
            for _ in range(n):
                if budget_usd is not None and pipe.cost >= budget_usd:
                    print(f"budget of ${budget_usd:.2f} reached; stopping", file=sys.stderr)
                    return stats
                diff = rng.choice(["easy", "medium", "hard"]) if difficulty == "mixed" else difficulty
                examples = rng.sample(pool, min(3, len(pool)))
                try:
                    item = await asyncio.to_thread(
                        pipe.generate, leaf, names[leaf], diff, examples, rng.choice(TOPICS)
                    )
                    ok = item is not None and await asyncio.to_thread(pipe.check, item, existing, stats)
                except anthropic.AuthenticationError:
                    raise SystemExit("ANTHROPIC_API_KEY was rejected") from None
                except (anthropic.APIStatusError, anthropic.APIConnectionError, ValueError) as e:
                    stats.reject(f"error: {type(e).__name__}")
                    continue
                if item is None:
                    stats.reject(f"generation failed: {pipe.last_stop}")
                    continue
                if not ok:
                    continue
                if out is not None:
                    saved = json.loads(out.read_text()) if out.exists() else []
                    saved.append(item.model_dump(mode="json", exclude_none=True))
                    out.write_text(json.dumps(saved, indent=2, ensure_ascii=False) + "\n")
                if dry_run:
                    print(item.model_dump_json(indent=2, exclude_none=True))
                else:
                    await insert_question(
                        db, skill_id=leaf, fmt="mc", difficulty=diff, content=rw_content(item), source="llm"
                    )
                    await db.commit()
                stats.inserted += 1
                print(
                    f"{leaf} [{diff}]: accepted ({stats.inserted} so far, ${pipe.cost:.2f} spent)",
                    file=sys.stderr,
                )
    return stats


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m app.generate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    rw = sub.add_parser("rw", help="generate Reading & Writing items")
    rw.add_argument(
        "--skill",
        action="append",
        required=True,
        help="sub-skill or parent node ID, e.g. RW.SEC (repeatable)",
    )
    rw.add_argument("--n", type=int, default=3, help="items to attempt per sub-skill")
    rw.add_argument("--difficulty", choices=["easy", "medium", "hard", "mixed"], default="mixed")
    rw.add_argument("--dry-run", action="store_true", help="print accepted items instead of inserting them")
    rw.add_argument(
        "--budget-usd", type=float, help="stop starting new items once estimated spend reaches this"
    )
    rw.add_argument("--out", type=Path, help="also append accepted items to this seed-bank JSON file")
    args = ap.parse_args(argv)

    s = get_settings()
    if not s.anthropic_api_key:
        raise SystemExit("ANTHROPIC_API_KEY is not set; R&W practice uses the seed bank only.")
    pipe = Pipeline(anthropic.Anthropic(api_key=s.anthropic_api_key), s.anthropic_model)

    async def go() -> Stats:
        try:
            return await run(
                pipe,
                args.skill,
                args.n,
                args.difficulty,
                args.dry_run,
                load_rw_seed(),
                args.budget_usd,
                args.out,
            )
        finally:
            await engine.dispose()

    stats = asyncio.run(go())
    usage = {"input_tokens": pipe.input_tokens, "output_tokens": pipe.output_tokens}
    print(
        json.dumps(
            {"accepted": stats.inserted, "rejected": stats.rejected, **usage, "usd": round(pipe.cost, 2)}
        )
    )


if __name__ == "__main__":
    main()
