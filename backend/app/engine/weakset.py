"""PT5 Weakness Drill: when a mini-set counts as mastered, and the overall readiness figure.

A set is mastered when at least 80% of its last 8 answers are right (7 of 8) and those 8 answers
were given on at least 2 separate days. Mastered sets are then reviewed on the SRS schedule.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

WINDOW = 8
NEED = 7  # 80% of 8, rounded up
DAYS = 2


@dataclass(frozen=True)
class Status:
    answered: int  # all graded answers on the set's questions
    recent_correct: int  # within the last WINDOW
    recent_total: int
    days: int  # distinct days within the last WINDOW
    mastered: bool
    progress: float  # 0..1; 1 only when mastered


def status(answers: Sequence[tuple[date, bool]]) -> Status:
    """`answers`: (day, correct) in chronological order."""
    last = answers[-WINDOW:]
    right = sum(c for _, c in last)
    days = len({d for d, _ in last})
    mastered = len(last) == WINDOW and right >= NEED and days >= DAYS
    progress = 1.0 if mastered else min(right, NEED - 1) / NEED
    return Status(len(answers), right, len(last), days, mastered, progress)


def readiness(progress: Sequence[float]) -> float:
    return sum(progress) / len(progress) if progress else 0.0


def set_of(external_id: str | None) -> str | None:
    """Drill set of a seed item id ("pt5-rw-trans-001" -> "rw-trans"); None for mock-only items
    ("pt5-mock-a-rw-01") and everything else."""
    if not external_id or not external_id.startswith("pt5-") or external_id.startswith("pt5-mock-"):
        return None
    return "-".join(external_id.split("-")[1:3])
