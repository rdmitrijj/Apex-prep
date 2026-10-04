"""Practice-exam blueprint: module layout, difficulty profiles, slot sampling, official ordering."""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

Setting = Literal["official", "hard", "brutal"]
SECTION_ORDER = ("RW", "MATH")
BREAK_SECONDS = 10 * 60
PRETEST_PER_MODULE = 2

# (operational questions per module, seconds per module)
MODULE_SPEC = {"RW": (25, 32 * 60), "MATH": (20, 35 * 60)}

# Operational questions per domain in each module (SAT_SPEC §3/§4 shares, split evenly over 2 modules).
BLUEPRINT = {
    "RW": {"RW.CAS": 7, "RW.INI": 6, "RW.SEC": 7, "RW.EOI": 5},
    "MATH": {"MATH.ALG": 7, "MATH.ADV": 7, "MATH.PSD": 3, "MATH.GEO": 3},
}
RW_DOMAIN_ORDER = ("RW.CAS", "RW.INI", "RW.SEC", "RW.EOI")

# Share of (easy, medium, hard) per setting and module. Module 1 is broad; Module 2 depends on routing.
PROFILES: dict[str, dict[str, tuple[float, float, float]]] = {
    "official": {"1": (0.34, 0.33, 0.33), "harder": (0.15, 0.35, 0.50), "easier": (0.50, 0.40, 0.10)},
    "hard": {"1": (0.20, 0.40, 0.40), "harder": (0.05, 0.35, 0.60), "easier": (0.35, 0.40, 0.25)},
    "brutal": {"1": (0.10, 0.30, 0.60), "harder": (0.00, 0.20, 0.80), "easier": (0.25, 0.40, 0.35)},
}
DIFFICULTIES = ("easy", "medium", "hard")


@dataclass(frozen=True)
class Slot:
    domain: str
    leaf: str
    difficulty: str
    pretest: bool


def domain_of(skill_id: str) -> str:
    return ".".join(skill_id.split(".")[:2])


def quotas(shares: Sequence[float], n: int) -> list[int]:
    """Largest-remainder split of n into integer counts proportional to shares."""
    raw = [s * n for s in shares]
    counts = [int(r) for r in raw]
    by_remainder = sorted(range(len(raw)), key=lambda i: raw[i] - counts[i], reverse=True)
    for i in by_remainder[: n - sum(counts)]:
        counts[i] += 1
    return counts


def slots(
    section: str, setting: Setting, stage_key: str, leaves: Sequence[tuple[str, float]], rng: random.Random
) -> list[Slot]:
    """Sample a module's slots. `leaves` are (sub-skill id, weight) for the section; `stage_key` is
    '1', 'harder', or 'easier'."""
    blueprint = BLUEPRINT[section]
    domains = [d for d, n in blueprint.items() for _ in range(n)]
    domains += rng.choices(list(blueprint), weights=list(blueprint.values()), k=PRETEST_PER_MODULE)
    pretest = [False] * (len(domains) - PRETEST_PER_MODULE) + [True] * PRETEST_PER_MODULE
    counts = quotas(PROFILES[setting][stage_key], len(domains))
    diffs = [d for d, c in zip(DIFFICULTIES, counts, strict=True) for _ in range(c)]
    rng.shuffle(diffs)
    out = []
    for domain, diff, pre in zip(domains, diffs, pretest, strict=True):
        pool = [(leaf, w) for leaf, w in leaves if domain_of(leaf) == domain]
        leaf = rng.choices([p[0] for p in pool], weights=[p[1] for p in pool])[0]
        out.append(Slot(domain, leaf, diff, pre))
    return out


def order(section: str, items: Sequence[tuple[str, float]], rng: random.Random) -> list[int]:
    """Indices of (sub-skill id, difficulty b) items in official order (SAT_SPEC §2):
    R&W by domain CAS→INI→SEC→EOI, grouped by skill except SEC, easy→hard; Math easy→hard."""
    ties = [rng.random() for _ in items]

    def key(i: int) -> tuple[int, str, float, float]:
        skill_id, b = items[i]
        if section == "MATH":
            return (0, "", b, ties[i])
        dom = domain_of(skill_id)
        group = "" if dom == "RW.SEC" else ".".join(skill_id.split(".")[:3])
        return (RW_DOMAIN_ORDER.index(dom), group, b, ties[i])

    return sorted(range(len(items)), key=key)
