"""Weakness score per sub-skill: how much practising it is likely to move the score.

score = (0.45·need + 0.30·errors + 0.15·pace + 0.10·decay) · sqrt(weight / mean leaf weight) · 1.3 for Math

- need: chance of missing a medium-hard item (b = 0.5) at the skill's recency-weighted ability
- errors: recency-weighted error rate, smoothed toward 50%
- pace: how far the median answer time is over the test's per-question budget (capped at 2x)
- decay: days since last practice, saturating at 21
Responses decay with a 14-day half-life; exam responses (timed, realistic) count 1.5x.
"""

import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.engine.irt import ability, p_correct

HALF_LIFE_DAYS = 14.0
EXAM_WEIGHT = 1.5
MATH_BOOST = 1.3  # Aalto: Math >= 700 and ties broken by Math
# Per-question time budget on the real test: 32 min / 27 (R&W), 35 min / 22 (Math).
TARGET_SECONDS = {"RW": 32 * 60 / 27, "MATH": 35 * 60 / 22}


@dataclass(frozen=True)
class Attempt:
    correct: bool
    b: float
    time_ms: int
    age_days: float
    exam: bool


@dataclass(frozen=True)
class Weakness:
    skill_id: str
    score: float
    theta: float
    attempts: int
    correct: int
    avg_seconds: float | None
    target_seconds: float
    reasons: list[str] = field(default_factory=list)


def weakness(
    skill_id: str, section: str, weight: float, mean_weight: float, attempts: Sequence[Attempt]
) -> Weakness:
    target = TARGET_SECONDS[section]
    ws = [0.5 ** (a.age_days / HALF_LIFE_DAYS) * (EXAM_WEIGHT if a.exam else 1.0) for a in attempts]
    theta = ability([(a.b, a.correct, w) for a, w in zip(attempts, ws, strict=True)])
    need = 1.0 - p_correct(theta, 0.5)
    missed_w = sum(w for a, w in zip(attempts, ws, strict=True) if not a.correct)
    errors = (missed_w + 0.5) / (sum(ws) + 1.0)
    times = [a.time_ms / 1000 for a in attempts if a.time_ms > 0]
    median = statistics.median(times) if times else None
    pace = 0.0 if median is None else max(0.0, min(1.0, median / target - 1.0))
    last = min((a.age_days for a in attempts), default=None)
    decay = 0.0 if last is None else min(1.0, last / 21.0)

    base = 0.45 * need + 0.30 * errors + 0.15 * pace + 0.10 * decay
    score = base * (weight / mean_weight) ** 0.5 * (MATH_BOOST if section == "MATH" else 1.0)

    n_correct = sum(a.correct for a in attempts)
    reasons: list[str] = []
    if not attempts:
        reasons.append("Not tried yet")
    else:
        recent = sorted(attempts, key=lambda a: a.age_days)[:6]
        missed = sum(not a.correct for a in recent)
        if missed:
            reasons.append(f"Missed {missed} of the last {len(recent)}")
        if median is not None and median > target * 1.2:
            reasons.append(f"{median / target:.1f}× slower than test pace")
        if last is not None and last >= 14:
            reasons.append(f"Not practised in {int(last)} days")
    return Weakness(
        skill_id=skill_id,
        score=score,
        theta=theta,
        attempts=len(attempts),
        correct=n_correct,
        avg_seconds=sum(times) / len(times) if times else None,
        target_seconds=target,
        reasons=reasons,
    )
