"""`python -m app.validate`: prove the question bank is sound before it is seeded.

Checks the R&W and math seed files, the imported-mistake file, and a sweep of every math generator.
`--db` also audits questions already stored (add `--fix` to quarantine failures), `--report PATH`
writes a Markdown report. Exits 1 on any failure.

Math rule: the key is computed independently (SymPy `check`), and every choice is evaluated, so a
second right answer (the old "8 is also a zero of (x+8)(x+2)(x-8)" bug) fails validation.
"""

import argparse
import asyncio
import difflib
import itertools
import json
import os
import random
import re
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy
from sympy.core.relational import Relational

from app.generators import DIFFICULTIES, REGISTRY, generate
from app.generators.core import MULTI_ANSWER
from app.generators.spr import canonical_entry, is_correct, is_valid_entry
from app.schemas.question import MathItem, RWItem, RWSeedItem
from app.services.questions import SEED_DIR, load_taxonomy

IMPORTS = SEED_DIR / "imports" / "bluebook_pt4.json"
REFERENCES = SEED_DIR / "imports" / "reference_examples.json"
# Blind re-solves of the Triage bank: item id -> the choice TEXT a solver picked without the key.
BLIND = SEED_DIR / "blind_solve.json"
TRIAGE = "rw-tri-"  # Triage-bank ids; the stricter study-field checks apply to these
MAX_SIMILARITY = 0.75
MAX_TOPIC_REPEATS = 3
MAX_KEY_LONGEST = 0.40
MIN_WORDS, MAX_WORDS = 25, 150
BANNED = re.compile(r"\b(SAT|College Board|Bluebook)\b")
X, Y, V = sympy.symbols("X Y v")

Failure = tuple[str, str, str]  # (area, item id, problem)
HISTORY = """## History

- 2026-10-27 baseline (commit 31b3093): 374 R&W seed items, 214 with passages under 25 words
  (149 grammar, 44 evidence, 14 transitions, 7 words in context); math generators clean on a
  3,360-item sweep. The old double-zero `POLYZ` items had been quarantined by migration 0003.
- Fixes: every short passage got context sentences (the tested sentence is unchanged); `build()`
  now requires an independent predicate for multi-answer stems ("Which ... is a ...", "could be").
"""


def words(item: RWItem) -> int:
    text = " ".join([item.passage, item.passage2 or "", *(item.notes or [])])
    return len(re.sub(r"<[^>]+>|_{3,}", " ", text).split())


def norm(s: str) -> str:
    return re.sub(r"\W+", " ", s.lower()).strip()


def check_rw(item: RWItem, leaves: set[str]) -> list[str]:
    errs = []
    if item.id is None:
        errs.append("missing id")
    if item.skill not in leaves:
        errs.append(f"unknown skill {item.skill}")
    n = words(item)
    if not MIN_WORDS <= n <= MAX_WORDS:
        errs.append(f"passage is {n} words (needs {MIN_WORDS}-{MAX_WORDS})")
    r = item.rationales.model_dump()
    if not r[item.answer].startswith("Correct."):
        errs.append("key's rationale doesn't start with 'Correct.'")
    if any(v.startswith("Correct.") for k, v in r.items() if k != item.answer):
        errs.append("more than one choice marked correct")
    if item.skill.startswith("RW.CAS.WIC"):
        key = item.choices["ABCD".index(item.answer)]
        if re.search(rf"\b{re.escape(key.strip().lower())}\b", item.passage.lower()):
            errs.append(f"the key '{key}' appears in the passage")
    text = " ".join([item.passage, item.passage2 or "", item.stem, *item.choices, *(item.notes or [])])
    if BANNED.search(text):
        errs.append("names the test or its maker")
    if item.notes is not None and not 4 <= len(item.notes) <= 6:
        errs.append(f"{len(item.notes)} notes bullets (needs 4-6)")
    if isinstance(item, RWSeedItem):
        errs += check_study_fields(item)
    return errs


def numbers(text: str) -> set[Fraction]:
    return {Fraction(m.replace(",", "")) for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def derivable(fig: dict[str, Any]) -> set[Fraction]:
    """Figure values, plus every pairwise difference, sum, and ratio (rounded as a choice would cite
    it) and percent change: the numbers a correct quantitative choice may state."""
    vals = numbers(json.dumps(fig))
    out = set(vals)
    for a, b in itertools.permutations(vals, 2):
        out |= {abs(a - b), a + b}
        if b:
            out |= {Fraction(round(a / b, k)).limit_denominator(1000) for k in (0, 1, 2)}
            out |= {Fraction(round(100 * (a - b) / b, k)).limit_denominator(1000) for k in (0, 1)}
    return out


def check_study_fields(item: RWSeedItem) -> list[str]:
    errs = []
    wrong = [L for L in "ABCD" if item.answer != L]
    triage = (item.id or "").startswith(TRIAGE)
    if item.vocab is not None or (triage and item.skill.startswith("RW.CAS.WIC")):
        by_word = {v.word.lower(): v.pos for v in item.vocab or []}
        missing = [c for c in item.choices if c.strip().lower() not in by_word]
        if missing:
            errs.append(f"choices without a vocab entry: {missing}")
        elif len({by_word[c.strip().lower()] for c in item.choices}) > 1:
            errs.append("choices are not all the same part of speech")
    if item.quant is not None:
        if sorted(item.quant) != list("ABCD"):
            errs.append("quant needs a role for every choice")
        if [L for L, role in item.quant.items() if role == "supports"] != [item.answer]:
            errs.append("exactly one choice, the key, may be marked 'supports'")
        if item.figure is not None:
            known = derivable(item.figure.model_dump())
            for L, choice in zip("ABCD", item.choices, strict=True):
                bad = sorted(str(n) for n in numbers(choice) - known)
                if bad and item.quant.get(L) in ("supports", "true_but_irrelevant"):
                    errs.append(f"{L} cites {bad}, not in or computable from the figure")
    if not triage:
        return errs
    for field in ("topic", "steps", "strategy_tip", "traps", "fictional"):
        if getattr(item, field) is None:
            errs.append(f"missing {field}")
    if item.traps is not None and sorted(item.traps) != wrong:
        errs.append(f"traps must name the trap of each wrong choice ({''.join(wrong)})")
    if item.skill.startswith("RW.INI.COEQ") and item.quant is None:
        errs.append("quantitative items need quant roles")
    if (
        item.skill.startswith("RW.SEC.BND")
        and len({re.sub(r"[^a-z]", "", c.lower()) for c in item.choices}) > 1
    ):
        errs.append("boundaries choices differ in more than punctuation")
    if item.skill.startswith("RW.SEC.FSS") and not item.skill.endswith(".MOD"):
        toks = [c.split() for c in item.choices]
        pre = len(os.path.commonprefix(toks))
        suf = len(os.path.commonprefix([t[pre:][::-1] for t in toks]))
        if max(len(t) - pre - suf for t in toks) > 4:
            errs.append("form/structure choices differ in more than the tested words")
    return errs


def check_bank(items: list[RWSeedItem]) -> list[Failure]:
    """Checks across items: near-duplicate passages, topic repeats, and (Triage bank) answer-key
    balance, the key-is-longest bias, and the recorded blind re-solve."""
    out: list[Failure] = []
    texts = {
        i.id or "": norm(" ".join([i.passage, i.passage2 or "", *(i.notes or [])])).split() for i in items
    }
    new = [i for i in texts if i.startswith(TRIAGE)]
    for a in new:
        sm = difflib.SequenceMatcher(None, b=texts[a], autojunk=False)
        for b in texts:
            if b == a or (b.startswith(TRIAGE) and b < a):
                continue
            sm.set_seq1(texts[b])
            if sm.real_quick_ratio() > MAX_SIMILARITY and sm.quick_ratio() > MAX_SIMILARITY:
                r = sm.ratio()
                if r > MAX_SIMILARITY:
                    out.append(("rw", a, f"passage {r:.2f} similar to {b}"))
    topics = Counter((skill_of(i.skill), i.topic.lower()) for i in items if i.topic)
    out += [
        ("rw", f"{s} / {t}", f"topic used {n} times") for (s, t), n in topics.items() if n > MAX_TOPIC_REPEATS
    ]

    blind = json.loads(BLIND.read_text()) if BLIND.exists() else {}
    by_skill: dict[str, list[RWSeedItem]] = defaultdict(list)
    for i in items:
        if (i.id or "").startswith(TRIAGE):
            by_skill[skill_of(i.skill)].append(i)
            key = i.choices["ABCD".index(i.answer)]
            if i.id not in blind:
                out.append(("rw", i.id or "", "no blind re-solve recorded"))
            elif blind[i.id] != key:
                out.append(("rw", i.id or "", f"blind re-solve picked {blind[i.id]!r}, key is {key!r}"))
    for skill, group in by_skill.items():
        n, letters = len(group), Counter(i.answer for i in group)
        if any(not n // 4 <= letters[L] <= -(-n // 4) for L in "ABCD"):
            out.append(("rw", skill, f"unbalanced key {dict(sorted(letters.items()))} over {n} items"))
        longest = sum(
            len(i.choices["ABCD".index(i.answer)])
            > max(len(c) for j, c in enumerate(i.choices) if "ABCD"[j] != i.answer)
            for i in group
        )
        if longest > MAX_KEY_LONGEST * n:
            out.append(("rw", skill, f"key is the longest choice in {longest}/{n} items"))
    return out


def skill_of(leaf: str) -> str:
    return ".".join(leaf.split(".")[:3])


def _val(s: str) -> Any:
    v = sympy.sympify(s)
    return sympy.Tuple(*v) if isinstance(v, tuple) else v  # "(1, 2)" parses to a plain tuple


def same(a: Any, b: Any) -> bool:
    """Mathematically equal: expressions, points, and equations/inequalities up to a constant factor."""
    a, b = (sympy.Tuple(*t) if isinstance(t, tuple) else t for t in (a, b))
    if isinstance(a, sympy.Tuple) or isinstance(b, sympy.Tuple):
        return (
            isinstance(a, sympy.Tuple)
            and isinstance(b, sympy.Tuple)
            and len(a) == len(b)
            and all(same(p, q) for p, q in zip(a, b, strict=True))
        )
    if isinstance(a, sympy.And) or isinstance(b, sympy.And):  # a system: same parts in any order
        if not (isinstance(a, sympy.And) and isinstance(b, sympy.And)) or len(a.args) != len(b.args):
            return False
        return all(any(same(p, q) for q in b.args) for p in a.args)
    if isinstance(a, Relational) or isinstance(b, Relational):
        if not (isinstance(a, Relational) and isinstance(b, Relational)):
            return False
        ratio = sympy.simplify((a.lhs - a.rhs) / (b.lhs - b.rhs))
        if not ratio.is_number or ratio == 0:
            return False
        if isinstance(a, sympy.Eq | sympy.Ne):
            return type(a) is type(b)
        flip = {sympy.Ge: sympy.Le, sympy.Le: sympy.Ge, sympy.Gt: sympy.Lt, sympy.Lt: sympy.Gt}
        return type(a) is (type(b) if ratio > 0 else flip.get(type(b)))
    return bool(sympy.simplify(sympy.sympify(a) - sympy.sympify(b)) == 0)


def accepted(pred: Any, value: Any) -> bool:
    subs = {X: value[0], Y: value[1]} if isinstance(value, sympy.Tuple) else {V: value}
    out = pred.subs(subs)
    if out in (sympy.true, sympy.false):
        return bool(out)
    return bool(sympy.simplify(out) == 0)


def check_math(item: MathItem, leaves: set[str]) -> list[str]:
    errs = []
    if item.skill not in leaves:
        errs.append(f"unknown skill {item.skill}")
    try:
        key = _val(item.check)
    except Exception as e:  # noqa: BLE001 (any parse error is a validation failure)
        return [*errs, f"check doesn't evaluate: {e}"]
    if item.format == "spr":
        assert item.spr_answers is not None
        if not (key.is_Rational and key.is_finite):
            return [*errs, f"SPR key {key} isn't a rational number"]
        keys = [Fraction(a) for a in item.spr_answers]
        if keys[0] != Fraction(int(key.p), int(key.q)):
            errs.append(f"spr_answers[0] = {keys[0]}, but check computes {key}")
        if any(k_ != keys[0] for k_ in keys):
            errs.append("spr_answers disagree with each other")
        entry = canonical_entry(keys[0])
        if not (is_valid_entry(entry) and is_correct(entry, keys)):
            errs.append(f"no valid 5/6-character entry for {keys[0]}")
        for e in item.spr_entries or []:
            if not is_valid_entry(e):
                errs.append(f"sample entry '{e}' breaks the entry rules")
            elif not is_correct(e, keys):
                errs.append(f"sample entry '{e}' is graded wrong")
        if MULTI_ANSWER.search(item.stem):
            errs.append("SPR stem asks 'which ... is a': rewrite it as a single-answer question")
        return errs
    assert item.choices and item.values and item.answer and item.rationales
    ki = "ABCD".index(item.answer)
    try:
        vals = [_val(v) for v in item.values]
        pred = _val(item.accepts) if item.accepts else None
    except Exception as e:  # noqa: BLE001
        return [*errs, f"values/accepts don't evaluate: {e}"]
    if MULTI_ANSWER.search(item.stem) and pred is None:
        errs.append("stem admits several answers but has no `accepts` predicate")
    for i, (letter, v) in enumerate(zip("ABCD", vals, strict=True)):
        right = accepted(pred, v) if pred is not None else same(v, key)
        if i == ki and not right:
            errs.append(f"key {letter} = {v} is not correct (check gives {key})")
        if i != ki and right:
            errs.append(f"distractor {letter} = {v} is ALSO correct")
    if pred is not None and not same(vals[ki], key):
        errs.append(f"key {item.answer} = {vals[ki]} differs from check {key}")
    if len({" ".join(c.lower().split()) for c in item.choices}) != 4:
        errs.append("duplicate choice texts")
    r = item.rationales.model_dump()
    if not r[item.answer].startswith("Correct."):
        errs.append("key's rationale doesn't start with 'Correct.'")
    if any(v.startswith("Correct.") or len(v) < 12 for k, v in r.items() if k != item.answer):
        errs.append("every distractor needs feedback naming its mistake")
    return errs


def check_generators(seeds: int) -> tuple[list[Failure], int]:
    out: list[Failure] = []
    n = 0
    for skill in sorted(REGISTRY):
        for d in DIFFICULTIES:
            for seed in range(seeds):
                ctx = f"{skill}/{d}/seed={seed}"
                n += 1
                try:
                    g = generate(skill, d, random.Random(seed))
                except Exception as e:  # noqa: BLE001
                    out.append(("generator", ctx, f"raised {type(e).__name__}: {e}"))
                    continue
                problems = []
                if not g.verify():
                    problems.append("verify() failed")
                if not g.explanation:
                    problems.append("no explanation")
                if g.format == "mc":
                    if not g.choices or len(set(g.choices)) != 4:
                        problems.append("needs 4 distinct choices")
                    if any(not g.rationales.get(L) for L in "ABCD"):
                        problems.append("a choice has no feedback")
                    if g.accepts is not None:
                        problems += [
                            f"distractor {dv} is also correct" for dv in g.distractor_values if g.accepts(dv)
                        ]
                else:
                    assert g.spr_answers
                    entry = canonical_entry(g.spr_answers[0])
                    if not (is_valid_entry(entry) and is_correct(entry, g.spr_answers)):
                        problems.append(f"SPR key {g.spr_answers[0]} has no valid entry")
                out += [("generator", ctx, p) for p in problems]
    return out, n


def check_imports(known: set[str], leaves: set[str]) -> tuple[list[Failure], int]:
    if not IMPORTS.exists():
        return [], 0
    out: list[Failure] = []
    rows = json.loads(IMPORTS.read_text())["mistakes"]
    for row in rows:
        eid = row["external_id"]
        if row["skill"] not in leaves:
            out.append(("import", eid, f"unknown skill {row['skill']}"))
        missing = [t for t in row.get("linked_practice_ids", []) if t not in known]
        if missing:
            out.append(("import", eid, f"linked twins not in the seed: {missing}"))
    dup = [e for e, c in Counter(r["external_id"] for r in rows).items() if c > 1]
    out += [("import", e, "duplicate external_id") for e in dup]
    refs = json.loads(REFERENCES.read_text())["examples"] if REFERENCES.exists() else []
    out += [("import", r["ref_id"], f"unknown skill {r['skill']}") for r in refs if r["skill"] not in leaves]
    return out, len(rows) + len(refs)


def check_seed_files(leaves: set[str]) -> tuple[list[Failure], set[str], Counter[str]]:
    out: list[Failure] = []
    ids: Counter[str] = Counter()
    texts: dict[str, str] = {}
    per_skill: Counter[str] = Counter()
    rw: list[RWSeedItem] = []
    for folder, model, check in (("rw", RWSeedItem, check_rw), ("math", MathItem, check_math)):
        for path in sorted((SEED_DIR / folder).glob("*.json")):
            for i, raw in enumerate(json.loads(path.read_text())):
                where = f"{path.name}[{i}]"
                try:
                    item = model.model_validate(raw)
                except Exception as e:  # noqa: BLE001
                    out.append((folder, raw.get("id") or where, f"schema: {e}".splitlines()[0]))
                    continue
                eid = item.id or where
                ids[eid] += 1
                if isinstance(item, RWSeedItem):
                    rw.append(item)
                per_skill[f"{item.skill}|{item.difficulty}"] += 1
                out += [(folder, eid, e) for e in check(item, leaves)]  # type: ignore[arg-type]
                body = norm(" ".join([getattr(item, "passage", "") or "", item.stem]))
                if body in texts:
                    out.append((folder, eid, f"same passage and stem as {texts[body]}"))
                texts.setdefault(body, eid)
    out += [("seed", e, "duplicate id") for e, c in ids.items() if c > 1]
    out += check_bank(rw)
    return out, set(ids), per_skill


async def check_db(fix: bool, leaves: set[str]) -> tuple[list[Failure], int]:
    """Stored questions (including generator items saved by past drills and exams)."""
    from sqlalchemy import select, update

    from app.core.db import SessionLocal, engine
    from app.models import Question, Response

    out: list[Failure] = []
    bad: set[int] = set()
    async with SessionLocal() as db:
        rows = (await db.scalars(select(Question).where(Question.status == "active"))).all()
        for q in rows:
            c, problems = q.content, []
            if q.skill_id not in leaves:
                problems.append(f"unknown skill {q.skill_id}")
            if not c.get("explanation"):
                problems.append("no explanation")
            if q.format == "mc":
                ch = c.get("choices") or []
                if (
                    len(ch) != 4
                    or len({" ".join(x.lower().split()) for x in ch}) != 4
                    or c.get("answer") not in list("ABCD")
                ):
                    problems.append("needs 4 distinct choices and a key")
                if q.skill_id.startswith("RW.") and not all(
                    (c.get("rationales") or {}).get(L) for L in "ABCD"
                ):
                    problems.append("a choice has no feedback")
                if q.skill_id == "MATH.ADV.NLF.POLYZ" and "is a zero" in c["stem"]:
                    zeros = {-int(s + d) for s, d in re.findall(r"\(x ([+-]) (\d+)\)", c["stem"])}
                    if sum(int(x.strip("$")) in zeros for x in ch) > 1:
                        problems.append("more than one choice is a zero")
            else:
                keys = [Fraction(a) for a in c.get("spr_answers") or []]
                if not keys or not is_valid_entry(canonical_entry(keys[0])):
                    problems.append("SPR key has no valid entry")
            if problems:
                bad.add(q.id)
            out += [("db", f"q{q.id} {q.skill_id}", p) for p in problems]
        if fix and bad:
            await db.execute(update(Question).where(Question.id.in_(bad)).values(status="quarantined"))
            # A wrong grade on a broken item shouldn't count against anyone.
            await db.execute(
                update(Response)
                .where(Response.question_id.in_(bad), Response.correct.is_(False))
                .values(correct=None)
            )
            await db.commit()
    await engine.dispose()
    return out, len(rows)


def report(failures: list[Failure], counts: dict[str, int], per_skill: Counter[str], fixed: bool) -> str:
    by_area = Counter(a for a, _, _ in failures)
    by_problem = Counter(re.sub(r"\d+ words", "N words", p.split(":")[0]) for _, _, p in failures)
    lines = [
        "# Question bank audit",
        "",
        "Generated by `uv run python -m app.validate --report docs/AUDIT.md`.",
        "",
    ]
    lines += ["| Checked | Items | Failures |", "|---|---|---|"]
    lines += [f"| {k} | {v} | {by_area.get(k, 0)} |" for k, v in counts.items()]
    if fixed:
        lines += ["", "Failing stored questions were quarantined (`status='quarantined'`), not deleted."]
    if failures:
        lines += ["", "## Failures by kind", "", "| Problem | Count |", "|---|---|"]
        lines += [f"| {p} | {n} |" for p, n in by_problem.most_common()]
        lines += ["", "## All failures", "", "| Area | Item | Problem |", "|---|---|---|"]
        lines += [f"| {a} | `{i}` | {p.replace('|', '/')} |" for a, i, p in failures]
    lines += [
        "",
        HISTORY.rstrip(),
        "",
        "## Seed items per sub-skill",
        "",
        "| Sub-skill | Easy | Medium | Hard |",
        "|---|---|---|---|",
    ]
    grid: dict[str, dict[str, int]] = defaultdict(dict)
    for key, n in per_skill.items():
        skill, d = key.split("|")
        grid[skill][d] = n
    lines += [
        f"| {s} | " + " | ".join(str(grid[s].get(d, 0)) for d in DIFFICULTIES) + " |" for s in sorted(grid)
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, default=50, help="random seeds per generator and difficulty")
    ap.add_argument("--db", action="store_true", help="also audit stored questions")
    ap.add_argument("--fix", action="store_true", help="with --db: quarantine stored failures")
    ap.add_argument("--report", type=Path, help="write a Markdown report here")
    args = ap.parse_args()

    leaves = {n["id"] for n in load_taxonomy() if n["level"] == "subskill"}
    failures, ids, per_skill = check_seed_files(leaves)
    counts = {
        "rw": sum(1 for i in ids if i.startswith("rw-")),
        "math": sum(1 for i in ids if i.startswith("m-")),
    }
    f, counts["import"] = check_imports(ids, leaves)
    failures += f
    f, counts["generator"] = check_generators(args.seeds)
    failures += f
    if args.db:
        f, counts["db"] = asyncio.run(check_db(args.fix, leaves))
        failures += f

    for area, item, problem in failures:
        print(f"{area:<9} {item:<40} {problem}")
    print("checked:", ", ".join(f"{k} {v}" for k, v in counts.items()), f"| failures: {len(failures)}")
    if args.report:
        args.report.write_text(report(failures, counts, per_skill, args.fix))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
