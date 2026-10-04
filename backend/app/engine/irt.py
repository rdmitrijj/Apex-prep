"""Rasch (1PL) model: ability estimates, section-score mapping, adaptive routing, difficulty targeting.

Item difficulty b comes from `questions.difficulty_rating` (easy -1, medium 0, hard 1).
"""

import math
from collections.abc import Sequence

# (b, correct, weight)
Obs = tuple[float, bool, float]

# Route to the harder Module 2 at >= ~60% expected correct on a medium item: ln(0.6/0.4).
ROUTE_THRESHOLD = math.log(0.6 / 0.4)
# Students report the easier Module 2 caps a section around 600-650 (SAT_SPEC §2).
EASIER_ROUTE_CAP = 640
# Provisional linear map: theta 0 (50% on medium items) -> 500; theta ~2.7 -> 800.
SCALE_MID, SCALE_SLOPE = 500.0, 110.0
TARGET_SUCCESS = 0.65  # training aims for 60-70% expected success
DIFFICULTY_B = {"easy": -1.0, "medium": 0.0, "hard": 1.0}


def p_correct(theta: float, b: float) -> float:
    return 1.0 / (1.0 + math.exp(b - theta))


def ability(obs: Sequence[Obs], prior_sd: float = 1.0) -> float:
    """MAP ability with a N(0, prior_sd²) prior (Newton's method; the log posterior is concave)."""
    theta = 0.0
    inv_var = 1.0 / prior_sd**2
    for _ in range(50):
        grad = -theta * inv_var
        hess = -inv_var
        for b, correct, w in obs:
            p = p_correct(theta, b)
            grad += w * ((1.0 if correct else 0.0) - p)
            hess -= w * p * (1.0 - p)
        step = grad / hess
        theta = max(-4.0, min(4.0, theta - step))
        if abs(step) < 1e-7:
            break
    return theta


def route(module1: Sequence[tuple[float, bool]]) -> str:
    """'harder' or 'easier' Module 2, from the scored Module 1 items."""
    theta = ability([(b, c, 1.0) for b, c in module1])
    return "harder" if theta >= ROUTE_THRESHOLD else "easier"


def section_score(items: Sequence[tuple[float, bool]], module2_route: str | None) -> int:
    """Estimated 200-800 section score (10-point steps) from all scored items of the section."""
    theta = ability([(b, c, 1.0) for b, c in items])
    score = SCALE_MID + SCALE_SLOPE * theta
    if module2_route == "easier":
        score = min(score, EASIER_ROUTE_CAP)
    return int(round(max(200.0, min(800.0, score)) / 10.0) * 10)


def target_difficulty(theta: float) -> str:
    """The difficulty whose expected success is closest to TARGET_SUCCESS."""
    return min(DIFFICULTY_B, key=lambda d: abs(p_correct(theta, DIFFICULTY_B[d]) - TARGET_SUCCESS))
