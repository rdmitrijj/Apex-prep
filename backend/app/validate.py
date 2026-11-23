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

from app.engine.weakset import set_of
from app.generators import DIFFICULTIES, REGISTRY, generate
from app.generators.core import MULTI_ANSWER
from app.generators.spr import canonical_entry, is_correct, is_valid_entry
from app.schemas.question import MathItem, RWItem, RWSeedItem
from app.services.questions import SEED_DIR, load_taxonomy

IMPORTS = sorted((SEED_DIR / "imports").glob("bluebook_*.json"))
PT5 = SEED_DIR / "pt5"
REFERENCES = SEED_DIR / "imports" / "reference_examples.json"
# Blind re-solves of the Triage bank: item id -> the choice TEXT a solver picked without the key.
BLIND = SEED_DIR / "blind_solve.json"
# Triage-bank and PT5 weakness-drill ids; the stricter study-field checks apply to these.
TRIAGE = ("rw-tri-", "pt5-", "pt6-")
PT6_SOURCE = SEED_DIR / "pt6" / "source" / "pt6_mistakes.json"
PT6_IMPORT = SEED_DIR / "imports" / "bluebook_pt6.json"
ORIGINAL_RUN = 8  # a PT6 item may not share this many consecutive words with a paraphrase
FORM_SIZES = {"rw": 27, "math": 22}
FORM_FRESH = {"rw": 6, "math": 4}  # mock-only items per form and module
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
    vals = numbers(json.dumps(fig, ensure_ascii=False))
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
    # Boundaries choices differ in punctuation (plus at most a conjunction); form choices in a short span.
    if item.skill.startswith("RW.SEC.BND") and changed_words(item.choices, punctuation=False) > 1:
        errs.append("boundaries choices differ in more than punctuation")
    fss = item.skill.startswith("RW.SEC.FSS") and not item.skill.endswith(".MOD")
    if fss and changed_words(item.choices, punctuation=True) > 4:
        errs.append("form/structure choices differ in more than the tested words")
    return errs


def changed_words(choices: list[str], punctuation: bool) -> int:
    """Most words any choice has outside the prefix and suffix that all choices share."""
    toks = [c.split() if punctuation else re.sub(r"[^a-z0-9']+", " ", c.lower()).split() for c in choices]
    pre = len(os.path.commonprefix(toks))
    suf = len(os.path.commonprefix([t[pre:][::-1] for t in toks]))
    return max(len(t) - pre - suf for t in toks)


def bank_group(eid: str, skill: str) -> str:
    """Key-balance group: a PT5 set ("pt5 rw-trans", "pt5 mock rw"), else the skill."""
    if eid.startswith("pt5-mock-"):
        return f"pt5 mock {eid.split('-')[3]}"
    if eid.startswith("pt5-"):
        return "pt5 " + "-".join(eid.split("-")[1:3])
    if eid.startswith("pt6-replay-"):
        return "pt6 replay"  # keys fixed by the original test: no balance check
    if eid.startswith("pt6-"):
        return "pt6 twins math" if "-math-" in eid else "pt6 twins rw"
    return skill_of(skill)


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
            by_skill[bank_group(i.id or "", i.skill)].append(i)
            key = i.choices["ABCD".index(i.answer)]
            if i.id not in blind:
                out.append(("rw", i.id or "", "no blind re-solve recorded"))
            elif blind[i.id] != key:
                out.append(("rw", i.id or "", f"blind re-solve picked {blind[i.id]!r}, key is {key!r}"))
    for skill, group in by_skill.items():
        n, letters = len(group), Counter(i.answer for i in group)
        if skill != "pt6 replay" and any(not n // 4 <= letters[L] <= -(-n // 4) for L in "ABCD"):
            out.append(("rw", skill, f"unbalanced key {dict(sorted(letters.items()))} over {n} items"))
        # Conventions choices differ by a mark or a word; length is no cue there.
        group = [i for i in group if not i.skill.startswith("RW.SEC.")]
        n = len(group)
        # A key that is usually the longest (or, after padding distractors, the shortest) gives itself away.
        for name, pick in (("longest", max), ("shortest", min)):
            if n < 4:
                break
            k = sum(len(i.choices["ABCD".index(i.answer)]) == pick(map(len, i.choices)) for i in group)
            if k > MAX_KEY_LONGEST * n:
                out.append(("rw", skill, f"key is the {name} choice in {k}/{n} items"))
    return out


def skill_of(leaf: str) -> str:
    return ".".join(leaf.split(".")[:3])


def _val(s: str) -> Any:
    v = sympy.sympify(s)
    return sympy.Tuple(*v) if isinstance(v, tuple) else v  # "(1, 2)" parses to a plain tuple


def same(a: Any, b: Any) -> bool:
    """Mathematically equal: expressions, points, and equations/inequalities up to a constant factor."""
    a, b = (sympy.Tuple(*t) if isinstance(t, tuple) else t for t in (a, b))
    if a == b:  # also covers oo, where simplify(oo - oo) is nan
        return True
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
    out: list[Failure] = []
    rows = [r for f in IMPORTS for r in json.loads(f.read_text())["mistakes"]]
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
    math: list[MathItem] = []
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
                else:
                    math.append(item)  # type: ignore[arg-type]
                per_skill[f"{item.skill}|{item.difficulty}"] += 1
                out += [(folder, eid, e) for e in check(item, leaves)]  # type: ignore[arg-type]
                body = norm(
                    " ".join(
                        [getattr(item, "passage", "") or "", *(getattr(item, "notes", None) or []), item.stem]
                    )
                )
                if body in texts:
                    out.append((folder, eid, f"same passage and stem as {texts[body]}"))
                texts.setdefault(body, eid)
    out += [("seed", e, "duplicate id") for e, c in ids.items() if c > 1]
    out += check_bank(rw)
    groups: dict[str, list[str]] = defaultdict(list)  # PT5 math sets: multiple-choice key balance
    for m in math:
        if m.id.startswith(("pt5-", "pt6-")) and m.answer and not m.id.startswith("pt6-replay-"):
            groups[bank_group(m.id, m.skill)].append(m.answer)
    for g, keys in groups.items():
        n, letters = len(keys), Counter(keys)
        if any(not n // 4 <= letters[L] <= -(-n // 4) for L in "ABCD"):
            out.append(("math", g, f"unbalanced key {dict(sorted(letters.items()))} over {n} items"))
    everything = {i.id or "": i for i in rw} | {m.id: m for m in math}
    out += check_pt5(everything)
    out += check_pt6(everything)
    return out, set(ids), per_skill


def check_pt5(items: dict[str, RWSeedItem | MathItem]) -> list[Failure]:
    """PT5 drill sets (count, rule card) and Mini Mock forms (size, no repeats, mix)."""
    if not (PT5 / "sets.json").exists():
        return []
    out: list[Failure] = []
    sets = json.loads((PT5 / "sets.json").read_text())["sets"]
    have = Counter(set_of(e) for e in items)
    for s in sets:
        if have[s["id"]] != s["count"]:
            out.append(("pt5", s["id"], f"{have[s['id']]} items, set needs {s['count']}"))
        if not (PT5 / "rules" / f"{s['id']}.md").exists():
            out.append(("pt5", s["id"], "no rule card"))
    known = {s["id"] for s in sets}
    out += [("pt5", e, "id names an unknown set") for e in items if set_of(e) not in (None, *known)]
    if not (PT5 / "forms.json").exists():
        return out
    forms: dict[str, dict[str, list[str]]] = json.loads((PT5 / "forms.json").read_text())
    used: Counter[str] = Counter()
    for name, form in forms.items():
        for sec, size in FORM_SIZES.items():
            ids = form[sec]
            used.update(ids)
            where = f"form {name} {sec}"
            if len(ids) != size or len(set(ids)) != size:
                out.append(("pt5", where, f"{len(set(ids))} distinct items, needs {size}"))
            missing = [e for e in ids if e not in items]
            if missing:
                out.append(("pt5", where, f"unknown items {missing}"))
                continue
            fresh = [e for e in ids if e.startswith(f"pt5-mock-{name.lower()}-")]
            if len(fresh) != FORM_FRESH[sec]:
                out.append(("pt5", where, f"{len(fresh)} mock-only items, needs {FORM_FRESH[sec]}"))
            if any(set_of(e) is None and e not in fresh for e in ids):
                out.append(("pt5", where, "uses an item that is neither in a set nor this form's own"))
            want = "RW." if sec == "rw" else "MATH."
            if any(not items[e].skill.startswith(want) for e in ids):
                out.append(("pt5", where, "item from the wrong section"))
            hard = sum(items[e].difficulty == "hard" for e in ids) / size
            if not 0.6 <= hard <= 0.8:
                out.append(("pt5", where, f"{hard:.0%} hard (needs about 70%)"))
            if sec == "math":
                spr = sum(getattr(items[e], "format", "mc") == "spr" for e in ids) / size
                if not 0.2 <= spr <= 0.35:
                    out.append(("pt5", where, f"{spr:.0%} SPR (needs about 25%)"))
    out += [("pt5", e, f"used in {n} forms") for e, n in used.items() if n > 1]
    mock = [e for e in items if e.startswith("pt5-mock-")]
    out += [("pt5", e, "mock-only item in no form") for e in mock if e not in used]
    return out


def shingles(text: str, n: int = ORIGINAL_RUN) -> set[tuple[str, ...]]:
    w = norm(text).split()
    return {tuple(w[i : i + n]) for i in range(len(w) - n + 1)}


def item_text(item: RWSeedItem | MathItem) -> str:
    parts = [getattr(item, "passage", "") or "", getattr(item, "passage2", "") or ""]
    return " ".join([*parts, *(getattr(item, "notes", None) or []), item.stem, *(item.choices or [])])


def check_boxplot(item: MathItem, key: Any) -> list[str]:
    """Five-number summaries in order; a 'ranges' question's key recomputed from the plotted data."""
    fig = item.figure or {}
    if fig.get("kind") != "boxplot":
        return []
    plots = fig.get("plots") or []
    order = ("min", "q1", "median", "q3", "max")
    errs = [
        f"box plot {p.get('name')} is not min <= q1 <= median <= q3 <= max"
        for p in plots
        if [p[k] for k in order] != sorted(p[k] for k in order)
    ]
    if "ranges" in item.stem and len(plots) == 2 and not errs:
        a, b = (p["max"] - p["min"] for p in plots)
        if not same(key, abs(a - b)):
            errs.append(f"key {key} isn't the difference of the plotted ranges ({abs(a - b)})")
    return errs


def mirror_letter(row: dict[str, Any], field: str) -> str | None:
    """'D' or 'B (320)' -> the letter; SPR answers and blanks -> None."""
    v = row.get(field)
    m = re.match(r"^([ABCD])(?: \(|$)", v or "")
    return m[1] if m else None


def mirror_common(t: RWSeedItem | MathItem, r: dict[str, Any], skill: str | None, label: str) -> list[str]:
    """What every PT6 twin shares with its record: source, skill, label, trap and lesson, trap answer."""
    errs = []
    rid = r["external_id"]
    if t.modeled_on != "bb-" + rid:
        errs.append(f"modeled_on is {t.modeled_on}, needs bb-{rid}")
    if t.skill != skill:
        errs.append(f"skill {t.skill}, the record's is {skill}")
    rp = t.replay
    if rp is None:
        return [*errs, "no replay block"]
    if rp.label != label:
        errs.append(f"label {rp.label!r}, needs {label!r}")
    if (rp.trap, rp.lesson) != (r["trap"], r["lesson"]):
        errs.append("trap/lesson differ from the record")
    if r["status"] != "wrong":
        if rp.trap_answer is not None:
            errs.append("blank/guessed records have no trap answer")
    elif rp.trap_answer is None:
        errs.append("needs a trap answer (the choice that repeats the PT6 mistake)")
    elif isinstance(t, MathItem) and t.format == "spr":
        if rp.trap_answer not in (t.spr_traps or {}):
            errs.append("SPR trap answer must be one of spr_traps")
    elif rp.trap_answer == getattr(t, "answer", None):
        errs.append("the trap answer is the key")
    return errs


def check_pt6(items: dict[str, RWSeedItem | MathItem]) -> list[Failure]:
    """PT6 Replay mirrors its record (skill, key letter, trap letter, label, trap, lesson). Twins+: twin 2
    keeps the difficulty but moves the key letter, twin 3 is hard and (R&W) longer, the four math blanks
    have a 60-second version. No PT6 item echoes a paraphrase; box plots are consistent."""
    if not PT6_SOURCE.exists():
        return []
    out: list[Failure] = []
    src = json.loads(PT6_SOURCE.read_text())["mistakes"]
    skills = {
        r["external_id"].removeprefix("bb-"): r["skill"]
        for r in json.loads(PT6_IMPORT.read_text())["mistakes"]
    }
    for r in src:
        rid = r["external_id"]
        base = rid.removeprefix("pt6-")
        label = f"PT6 · {'R&W' if r['section'] == 'rw' else 'Math'} M{r['module']} · Q{r['number']}"
        mirror = r.get("mirror_twin") or {}
        letter = mirror.get("correct") or mirror_letter(r, "correct_answer")
        t = items.get(f"pt6-replay-{base}")
        if t is None:
            out.append(("pt6", f"pt6-replay-{base}", "missing replay twin"))
            continue
        errs = mirror_common(t, r, skills.get(rid), label)
        answer = getattr(t, "answer", None)
        if letter and answer != letter:
            errs.append(f"key {answer}, the record's letter is {letter}")
        if not letter and getattr(t, "format", "mc") != "spr":
            errs.append("the record is grid-in, the twin isn't")
        spr = getattr(t, "spr_answers", None)
        if mirror.get("answer") and spr and Fraction(spr[0]) != Fraction(mirror["answer"]):
            errs.append(f"SPR key {spr[0]} differs from the mirror twin's {mirror['answer']}")
        if (
            letter
            and r["status"] == "wrong"
            and t.replay
            and t.replay.trap_answer != mirror_letter(r, "my_answer")
        ):
            errs.append(
                f"trap answer {t.replay.trap_answer}, but the PT6 pick was {mirror_letter(r, 'my_answer')}"
            )
        out += [("pt6", t.id or "", e) for e in errs]
        speed = r["section"] == "math" and r["status"] == "omitted"
        for kind, suffix in [
            ("twin2", "Twin 2"),
            ("twin3", "Twin 3"),
            *([("speed", "60-second")] if speed else []),
        ]:
            tid = f"pt6-{kind}-{base}"
            tw = items.get(tid)
            if tw is None:
                out.append(("pt6", tid, f"missing {suffix.lower()}"))
                continue
            errs = mirror_common(tw, r, skills.get(rid), f"{label} · {suffix}")
            if getattr(tw, "format", "mc") != getattr(t, "format", "mc"):
                errs.append("format differs from the record's")
            if kind == "twin2":
                if tw.difficulty != t.difficulty:
                    errs.append(f"difficulty {tw.difficulty}, the record's is {t.difficulty}")
                if letter and getattr(tw, "answer", None) == letter:
                    errs.append(f"twin 2 must move the key off {letter}")
            if kind == "twin3":
                if tw.difficulty != "hard":
                    errs.append("twin 3 must be hard")
                if isinstance(tw, RWSeedItem) and isinstance(t, RWSeedItem) and words(tw) <= words(t):
                    errs.append(f"twin 3 is {words(tw)} words, not longer than the replay twin ({words(t)})")
            out += [("pt6", tid, e) for e in errs]
    known = {
        f"pt6-{k}-{r['external_id'].removeprefix('pt6-')}"
        for r in src
        for k in ("replay", "twin2", "twin3", "speed")
    }
    out += [("pt6", e, "id matches no PT6 record") for e in items if e.startswith("pt6-") and e not in known]
    para = {s for r in src for s in shingles(r["paraphrase"])}
    for eid, item in items.items():
        if not eid.startswith("pt6-"):
            continue
        echo = shingles(item_text(item)) & para
        if echo:
            out.append(
                ("pt6", eid, f"repeats {ORIGINAL_RUN}+ words of a paraphrase: {' '.join(sorted(echo)[0])!r}")
            )
        if isinstance(item, MathItem):
            try:
                out += [("pt6", eid, e) for e in check_boxplot(item, _val(item.check))]
            except Exception as e:  # noqa: BLE001
                out.append(("pt6", eid, f"check doesn't evaluate: {e}"))
    return out


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
        "rw": sum(
            1
            for i in ids
            if i.startswith(("rw-", "pt5-rw-")) or i.startswith(("pt5-mock-", "pt6-")) and "-rw-" in i
        ),
        "math": sum(
            1
            for i in ids
            if i.startswith(("m-", "pt5-m-"))
            or i.startswith("pt5-mock-")
            and "-m-" in i
            or i.startswith("pt6-")
            and "-math-" in i
        ),
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
