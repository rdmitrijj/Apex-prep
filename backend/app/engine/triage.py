"""Triage drills: timed sets that train pace, guessing, and skipping (no exam scoring).

Modes, per-question target times, slot planning, and the results analysis (accuracy by domain and
skill, time against target, time sinks, first- vs second-pass accuracy, recommendations).
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.engine.exam import quotas

Mode = Literal["sprint", "module", "weakness", "math"]

# (questions, seconds). Module Simulation matches a real R&W module (27 in 32 minutes).
MODES: dict[str, tuple[int, int]] = {
    "sprint": (12, 14 * 60),
    "module": (27, 32 * 60),
    "weakness": (10, 12 * 60),
    "math": (10, 12 * 60),
}
# Share of R&W domains in Sprint and Module Simulation, weighted toward the owner's weak areas.
DOMAIN_SHARES = {"RW.INI": 0.36, "RW.CAS": 0.31, "RW.SEC": 0.19, "RW.EOI": 0.14}
MODULE_HARD = 0.8  # Module Simulation: mostly hard, the rest medium
WEAKNESS_SKILLS = 2
# Seconds a well-paced student spends per question, by skill (the real average is 71 s for R&W).
TARGET_SECONDS = {
    "RW.SEC.BND": 40,
    "RW.SEC.FSS": 40,
    "RW.EOI.TRN": 45,
    "RW.CAS.WIC": 50,
    "RW.EOI.RS": 55,
    "RW.CAS.TSP": 65,
    "RW.INI.CID": 75,
    "RW.INI.INF": 75,
    "RW.INI.COET": 80,
    "RW.INI.COEQ": 80,
    "RW.CAS.CTC": 90,
}
MATH_TARGET = 95  # 35 min / 22 questions
OVER_RED = 30  # the soft timer turns red this many seconds past the target
# One-line fixes for skills answered poorly, by skill prefix.
TIPS = {
    "RW.CAS.WIC": "predict your own word before reading the options",
    "RW.INI.COET": "turn the claim into a checklist and make sure the choice covers every part",
    "RW.INI.COEQ": "decide which comparison the claim needs before you read the choices",
    "RW.INI.INF": "pick the completion that follows from every premise, not one that goes further",
    "RW.EOI.RS": "underline every part of the goal; choices with only the method or aim are traps",
    "RW.EOI.TRN": "name the relationship (contrast, cause, example, stronger support) before choosing",
    "RW.SEC.BND": "check whether each side of the blank could stand alone as a sentence",
    "RW.SEC.FSS": "cross out the words between the subject and the blank, then match the verb",
    "RW.CAS.CTC": "find the assumption in Text 1 that Text 2 tests",
    "RW.CAS.TSP": "say what the text DOES (challenge, explain, compare) before reading the choices",
    "RW.INI.CID": "find the sentence that the rest of the text supports",
}


def skill_of(leaf: str) -> str:
    return ".".join(leaf.split(".")[:3])


def domain_of(leaf: str) -> str:
    return ".".join(leaf.split(".")[:2])


def target_seconds(leaf: str) -> int:
    return TARGET_SECONDS.get(skill_of(leaf), MATH_TARGET)


def timer_color(spent_s: float, target_s: float) -> Literal["normal", "amber", "red"]:
    """Soft per-question timer: amber at the target, red 30 s past it."""
    if spent_s >= target_s + OVER_RED:
        return "red"
    return "amber" if spent_s >= target_s else "normal"


@dataclass(frozen=True)
class Slot:
    prefix: str  # taxonomy id the question must fall under (domain or skill)
    difficulty: str


def plan(mode: str, weak_skills: Sequence[str], rng: random.Random) -> list[Slot]:
    """Slots for a session. `weak_skills` (skill ids, weakest first) drive the Weakness Sprint."""
    n, _ = MODES[mode]
    if mode == "math":
        return [Slot("MATH", rng.choice(["medium", "hard"])) for _ in range(n)]
    if mode == "weakness":
        skills = list(weak_skills[:WEAKNESS_SKILLS]) or list(DOMAIN_SHARES)
        return [
            Slot(s, "hard")
            for s, k in zip(skills, quotas([1 / len(skills)] * len(skills), n), strict=True)
            for _ in range(k)
        ]
    counts = quotas(list(DOMAIN_SHARES.values()), n)
    slots = [Slot(d, "hard") for d, k in zip(DOMAIN_SHARES, counts, strict=True) for _ in range(k)]
    if mode == "module":
        for i in rng.sample(range(n), n - round(n * MODULE_HARD)):
            slots[i] = Slot(slots[i].prefix, "medium")
    return slots


@dataclass(frozen=True)
class Item:
    skill_id: str  # leaf
    correct: bool  # blanks are wrong
    blank: bool
    seconds: float
    first_pass: bool  # the final answer was given on the first visit


@dataclass(frozen=True)
class Group:
    id: str
    total: int
    correct: int
    avg_seconds: float
    target_seconds: float


@dataclass(frozen=True)
class Analysis:
    total: int
    correct: int
    blanks: int
    avg_seconds: float
    by_domain: list[Group]
    by_skill: list[Group]
    time_sinks: dict[str, int]  # skill -> questions over target AND wrong
    first_pass: tuple[int, int]  # (correct, total)
    second_pass: tuple[int, int]
    recommendations: list[str]


def is_time_sink(i: Item) -> bool:
    return not i.correct and i.seconds > target_seconds(i.skill_id)


def _groups(items: Sequence[Item], key: str) -> list[Group]:
    out: dict[str, list[Item]] = {}
    for i in items:
        out.setdefault(domain_of(i.skill_id) if key == "domain" else skill_of(i.skill_id), []).append(i)
    return [
        Group(
            g,
            len(xs),
            sum(x.correct for x in xs),
            sum(x.seconds for x in xs) / len(xs),
            sum(target_seconds(x.skill_id) for x in xs) / len(xs),
        )
        for g, xs in sorted(out.items())
    ]


def analyze(items: Sequence[Item], names: dict[str, str]) -> Analysis:
    by_skill = _groups(items, "skill")
    sinks: dict[str, int] = {}
    for i in items:
        if is_time_sink(i):
            sinks[skill_of(i.skill_id)] = sinks.get(skill_of(i.skill_id), 0) + 1
    answered = [i for i in items if not i.blank]
    first = [i for i in answered if i.first_pass]
    second = [i for i in answered if not i.first_pass]
    return Analysis(
        total=len(items),
        correct=sum(i.correct for i in items),
        blanks=sum(i.blank for i in items),
        avg_seconds=sum(i.seconds for i in items) / len(items) if items else 0.0,
        by_domain=_groups(items, "domain"),
        by_skill=by_skill,
        time_sinks=sinks,
        first_pass=(sum(i.correct for i in first), len(first)),
        second_pass=(sum(i.correct for i in second), len(second)),
        recommendations=recommend(by_skill, sum(i.blank for i in items), names),
    )


def recommend(by_skill: Sequence[Group], blanks: int, names: dict[str, str]) -> list[str]:
    """Up to three concrete, data-backed suggestions, most costly problem first."""
    found: list[tuple[float, str]] = []
    if blanks:
        found.append(
            (
                blanks + 0.5,
                f"You left {blanks} blank. A guess has a 25% chance; a blank has none. Guess on every one.",
            )
        )
    for g in by_skill:
        name, acc, wrong = names.get(g.id, g.id), g.correct / g.total, g.total - g.correct
        slow = g.avg_seconds > 1.3 * g.target_seconds
        if slow and acc < 0.5:
            found.append(
                (
                    wrong + 0.25,
                    f"{name} took {g.avg_seconds:.0f} s on average (target {g.target_seconds:.0f} s) with "
                    f"{acc:.0%} accuracy: on the first pass, answer quickly and mark it.",
                )
            )
        elif acc < 0.6 and wrong >= 2 and g.id in TIPS:
            found.append((wrong, f"{name} accuracy {acc:.0%}: {TIPS[g.id]}."))
        elif slow and g.total >= 2:
            found.append(
                (0.5, f"{name} averaged {g.avg_seconds:.0f} s against a {g.target_seconds:.0f} s target.")
            )
    return [text for _, text in sorted(found, key=lambda f: -f[0])[:3]]
