"""Rasch (1PL) model: ability estimates, section-score mapping, adaptive routing, difficulty targeting.

Item difficulty b comes from `questions.difficulty_rating` (easy -1, medium 0, hard 1).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

# (b, credit in [0, 1] (a bool works: True = full credit), weight)
Obs = tuple[float, float, float]

# Route to the harder Module 2 at >= ~60% expected correct on a medium item: ln(0.6/0.4).
ROUTE_THRESHOLD = math.log(0.6 / 0.4)
# Students report the easier Module 2 caps a section around 600-650 (SAT_SPEC §2).
EASIER_ROUTE_CAP = 640
# Default linear map (before calibration): theta 0 (50% on medium items) -> 500; theta ~2.7 -> 800.
SCALE_MID, SCALE_SLOPE = 500.0, 110.0
# Prior uncertainty of that map (SD of intercept and slope), and how much an official score itself
# wobbles between sittings of equal ability (College Board reports roughly ±30-40 per section).
PRIOR_SD = (60.0, 25.0)
OFFICIAL_SD = 30.0
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
        for b, credit, w in obs:
            p = p_correct(theta, b)
            grad += w * (float(credit) - p)
            hess -= w * p * (1.0 - p)
        step = grad / hess
        theta = max(-4.0, min(4.0, theta - step))
        if abs(step) < 1e-7:
            break
    return theta


def ability_se(theta: float, bs: Sequence[float], prior_sd: float = 1.0) -> float:
    """Standard error of an ability estimate: 1/sqrt(prior precision + test information)."""
    info = 1.0 / prior_sd**2 + sum(p_correct(theta, b) * (1.0 - p_correct(theta, b)) for b in bs)
    return 1.0 / math.sqrt(info)


Mat2 = tuple[tuple[float, float], tuple[float, float]]


@dataclass(frozen=True)
class Scale:
    """score = intercept + slope · theta, with the posterior covariance of (intercept, slope)."""

    intercept: float
    slope: float
    cov: Mat2
    n: int = 0  # official scores it was fitted to


DEFAULT_SCALE = Scale(SCALE_MID, SCALE_SLOPE, ((PRIOR_SD[0] ** 2, 0.0), (0.0, PRIOR_SD[1] ** 2)))


def _inv(m: Mat2) -> Mat2:
    (a, b), (c, d) = m
    det = a * d - b * c
    return ((d / det, -b / det), (-c / det, a / det))


def calibrate(pairs: Sequence[tuple[float, float, float]], prior: Scale = DEFAULT_SCALE) -> Scale:
    """Bayesian linear fit of official scores on in-app ability. `pairs` are (theta, theta_se, score).

    Each observation's noise is the official score's own wobble plus the in-app estimate's error
    carried through the prior slope (errors-in-variables, approximately).
    With no pairs the prior comes back unchanged; one pair mostly moves the intercept; several
    pairs spread over different abilities pin down the slope too.
    """
    if not pairs:
        return prior
    p = _inv(prior.cov)
    p00, p01, p11 = p[0][0], p[0][1], p[1][1]
    r0 = p00 * prior.intercept + p01 * prior.slope
    r1 = p01 * prior.intercept + p11 * prior.slope
    for theta, se, score in pairs:
        w = 1.0 / (OFFICIAL_SD**2 + (prior.slope * se) ** 2)
        p00 += w
        p01 += w * theta
        p11 += w * theta * theta
        r0 += w * score
        r1 += w * theta * score
    cov = _inv(((p00, p01), (p01, p11)))
    return Scale(
        intercept=cov[0][0] * r0 + cov[0][1] * r1,
        slope=cov[1][0] * r0 + cov[1][1] * r1,
        cov=cov,
        n=len(pairs),
    )


def margin(theta: float, se: float, scale: Scale) -> int:
    """One-SD uncertainty of a section score: the map's own uncertainty plus the ability estimate's."""
    (a, b), (_, d) = scale.cov
    var = a + 2 * b * theta + d * theta * theta + (scale.slope * se) ** 2
    return int(round(math.sqrt(var) / 10.0) * 10)


def route(module1: Sequence[tuple[float, bool]]) -> str:
    """'harder' or 'easier' Module 2, from the scored Module 1 items."""
    theta = ability([(b, c, 1.0) for b, c in module1])
    return "harder" if theta >= ROUTE_THRESHOLD else "easier"


def to_score(theta: float, module2_route: str | None, scale: Scale = DEFAULT_SCALE) -> int:
    """200-800 section score in 10-point steps."""
    score = scale.intercept + scale.slope * theta
    if module2_route == "easier":
        score = min(score, EASIER_ROUTE_CAP)
    return int(round(max(200.0, min(800.0, score)) / 10.0) * 10)


def section_score(
    items: Sequence[tuple[float, bool]], module2_route: str | None, scale: Scale = DEFAULT_SCALE
) -> int:
    """Estimated section score from all scored items (b, correct) of the section."""
    return to_score(ability([(b, c, 1.0) for b, c in items]), module2_route, scale)


def target_difficulty(theta: float) -> str:
    """The difficulty whose expected success is closest to TARGET_SUCCESS."""
    return min(DIFFICULTY_B, key=lambda d: abs(p_correct(theta, DIFFICULTY_B[d]) - TARGET_SUCCESS))
