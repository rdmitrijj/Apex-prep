"""Generator framework: build a question from a SymPy-computed key and error-model distractors."""

import random
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Literal

import sympy

from app.generators.spr import canonical_entry, is_correct

Difficulty = Literal["easy", "medium", "hard"]
DIFFICULTIES: tuple[Difficulty, ...] = ("easy", "medium", "hard")
DIFFICULTY_RATING: dict[str, float] = {"easy": -1.0, "medium": 0.0, "hard": 1.0}

# Named error models. Every distractor must come from one of these.
ERROR_MODELS = {
    "sign_flip": "Sign error: a term changed sides (or was distributed) without changing sign.",
    "wrong_formula": "Used the wrong formula or relationship.",
    "partial_solution": "Stopped one step early: this is an intermediate value, not what was asked.",
    "unit_slip": "Unit or scale error (wrong conversion, or answered in the wrong units).",
    "operation_swap": "Used the inverse operation (e.g. multiplied instead of divided).",
    "reciprocal": "Inverted the ratio (took the reciprocal).",
    "distribution": "Distributed or expanded incorrectly.",
    "exponent_rule": "Misapplied an exponent rule (e.g. multiplied exponents instead of adding).",
    "extraneous": "An extraneous root: it satisfies a squared/cleared equation but not the original.",
    "misread": "Misread which quantity the question asks for.",
    "off_by_one": "Off by one (boundary or counting error).",
    "concept": "Conceptual confusion between two related ideas.",
    "order_of_ops": "Undid the operations in the wrong order.",
}

Value = Any  # a SymPy expression, int, or display string (SymPy ships no type hints)


@dataclass(frozen=True)
class D:
    """A distractor: value, the error model that produces it, and why it's wrong."""

    value: Value
    model: str
    why: str


@dataclass
class Generated:
    skill_id: str
    difficulty: Difficulty
    format: Literal["mc", "spr"]
    stem: str
    choices: list[str] | None
    answer: str | None  # MC letter
    spr_answers: list[Fraction] | None
    explanation: list[str]
    rationales: dict[str, str]
    error_models: dict[str, str]
    figure: dict[str, Any] | None
    verify: Callable[[], bool] = field(repr=False, compare=False)
    key_value: Value = field(repr=False, compare=False, default="")
    distractor_values: list[Value] = field(repr=False, compare=False, default_factory=list)

    def content(self) -> dict[str, Any]:
        return {
            "stem": self.stem,
            "choices": self.choices,
            "answer": self.answer,
            "spr_answers": [str(a) for a in self.spr_answers] if self.spr_answers else None,
            "explanation": self.explanation,
            "rationales": self.rationales,
            "error_models": self.error_models,
            "figure": self.figure,
        }


# ---------- helpers ----------

R = sympy.Rational
x, y, k = sympy.symbols("x y k")


def ri(rng: random.Random, lo: int, hi: int, exclude: tuple[int, ...] = (0,)) -> int:
    while True:
        v = rng.randint(lo, hi)
        if v not in exclude:
            return v


def tex(v: Value) -> str:
    if isinstance(v, str):
        return v
    return str(sympy.latex(sympy.sympify(v)))


def m(v: Value) -> str:
    """Inline math."""
    return f"${tex(v)}$"


def signed(n: Value) -> str:
    """'+ 3' / '- 3' for writing terms after a leading term."""
    v = sympy.sympify(n)
    return f"- {tex(-v)}" if v < 0 else f"+ {tex(v)}"


def lin(a: Value, b: Value, var: str = "x") -> str:
    """LaTeX for a*var + b, dropping 1s and zeros."""
    av, bv = sympy.sympify(a), sympy.sympify(b)
    head = "" if av == 0 else (var if av == 1 else f"-{var}" if av == -1 else f"{tex(av)}{var}")
    if bv == 0:
        return head or "0"
    return f"{head} {signed(bv)}" if head else tex(bv)


def holds(lhs: Value, rhs: Value, subs: dict[sympy.Symbol, Value]) -> bool:
    """Independent check: substitute and simplify lhs - rhs."""
    diff = (sympy.sympify(lhs) - sympy.sympify(rhs)).subs(subs)
    return bool(sympy.simplify(diff) == 0)


def safe(fn: Callable[[], Value]) -> Value | None:
    """Distractor formulas can divide by zero for some parameters; those are just skipped."""
    try:
        v = fn()
    except ZeroDivisionError:
        return None
    if v is None:
        return None
    if not isinstance(v, str) and sympy.sympify(v).has(sympy.zoo, sympy.nan, sympy.oo):
        return None
    return v


def ds(*items: tuple[Callable[[], Value], str, str]) -> list[D]:
    """Distractors from (lazy value, model, why); ones that fail to compute are dropped."""
    out: list[D] = []
    for fn, model, why in items:
        v = safe(fn)
        if v is not None:
            out.append(D(v, model, why))
    return out


def pt(a: Value, b: Value) -> str:
    return f"$({tex(a)}, {tex(b)})$"


def to_fraction(v: sympy.Basic) -> Fraction:
    r = sympy.Rational(v)
    return Fraction(int(r.p), int(r.q))


def _is_num(v: Value) -> bool:
    return not isinstance(v, str) and bool(sympy.sympify(v).is_number)


def _same(a: Value, b: Value) -> bool:
    if isinstance(a, str) or isinstance(b, str):
        return tex(a) == tex(b)
    da = sympy.sympify(a) - sympy.sympify(b)
    if da.is_number:
        return bool(abs(sympy.N(da, 30)) < 1e-12)
    # Cheap numeric probe first: a nonzero value at any point proves the expressions differ.
    for probe in (R(37, 100), R(191, 100), R(253, 100)):
        val = sympy.N(da.subs({s_: probe for s_ in da.free_symbols}), 30)
        if val.is_number and val.is_finite and abs(val) > 1e-9:
            return False
    return bool(sympy.simplify(da) == 0)


def num(v: Value) -> str:
    """Terminating rationals as decimals (money, percents, data); everything else as LaTeX."""
    if not isinstance(v, str):
        e = sympy.sympify(v)
        if e.is_Rational and not e.is_integer:
            q = int(e.q)
            while q % 2 == 0:
                q //= 2
            while q % 5 == 0:
                q //= 5
            if q == 1:
                f = to_fraction(e)
                for places in range(1, 5):
                    if f * 10**places == int(f * 10**places):
                        return f"{float(f):.{places}f}"
    return tex(v)


def dec_fmt(v: Value) -> str:
    return v if isinstance(v, str) else f"${num(v)}$"


def _render(v: Value) -> str:
    return v if isinstance(v, str) else m(v)


LETTERS = "ABCD"
CHOICE_WORDING = re.compile(r"\bwhich (of the following|choice|option)\b", re.IGNORECASE)


def build(
    rng: random.Random,
    *,
    skill: str,
    d: Difficulty,
    stem: str,
    key: Value,
    distractors: list[D],
    steps: list[str],
    verify: Callable[[], bool],
    figure: dict[str, Any] | None = None,
    spr: bool = True,
    spr_stem: str | None = None,
    fmt: Callable[[Value], str] = _render,
) -> Generated:
    """Assemble MC or SPR. SPR (~30%) only for rational keys when the stem allows it."""
    key_s = sympy.sympify(key) if not isinstance(key, str) else key
    # A stem that refers to answer choices can't become a free-response item without its own wording.
    spr = spr and (spr_stem is not None or not CHOICE_WORDING.search(stem))
    if fr_ok := (spr and not isinstance(key_s, str) and key_s.is_Rational and rng.random() < 0.3):
        fr = [to_fraction(key_s)]
        fr_ok = is_correct(canonical_entry(fr[0]), fr)
    if fr_ok:
        return Generated(
            skill, d, "spr", spr_stem or stem, None, None, fr, steps, {}, {}, figure, verify, key
        )
    chosen: list[D] = []
    if _is_num(key):
        kv = sympy.sympify(key)
        distractors = distractors + [
            D(-kv, "sign_flip", "Sign error somewhere in the work."),
            D(kv + 1, "off_by_one", "Arithmetic slip: off by one."),
            D(kv - 1, "off_by_one", "Arithmetic slip: off by one."),
            D(2 * kv, "operation_swap", "Multiplied where a division (or halving) was needed."),
        ]
    for dist in distractors:
        assert dist.model in ERROR_MODELS, dist.model
        if _same(dist.value, key) or fmt(dist.value) == fmt(key):
            continue
        if any(_same(dist.value, c.value) or fmt(dist.value) == fmt(c.value) for c in chosen):
            continue
        chosen.append(dist)
        if len(chosen) == 3:
            break
    if len(chosen) < 3:
        raise ValueError(f"{skill}/{d}: only {len(chosen)} usable distractors")
    order = [None, *chosen]
    rng.shuffle(order)
    choices, rationales, models = [], {}, {}
    answer = "A"
    for letter, opt in zip(LETTERS, order, strict=True):
        if opt is None:
            answer = letter
            choices.append(fmt(key))
            rationales[letter] = "Correct."
        else:
            choices.append(fmt(opt.value))
            rationales[letter] = opt.why
            models[letter] = opt.model
    return Generated(
        skill,
        d,
        "mc",
        stem,
        choices,
        answer,
        None,
        steps,
        rationales,
        models,
        figure,
        verify,
        key,
        [c.value for c in chosen],
    )


GeneratorFn = Callable[[random.Random, Difficulty], Generated]
REGISTRY: dict[str, GeneratorFn] = {}


def register(skill_id: str) -> Callable[[GeneratorFn], GeneratorFn]:
    def deco(fn: GeneratorFn) -> GeneratorFn:
        REGISTRY[skill_id] = fn
        return fn

    return deco


def plot_fn(f: Callable[[float], float], lo: float, hi: float, n: int = 60) -> list[list[float]]:
    """Sample a function into a polyline for a 'plot' figure."""
    pts = []
    for i in range(n + 1):
        xv = lo + (hi - lo) * i / n
        pts.append([round(xv, 4), round(f(xv), 4)])
    return pts
