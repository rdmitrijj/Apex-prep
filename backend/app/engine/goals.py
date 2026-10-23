"""Per-user score goals: section targets and how much each section's weaknesses count."""

MAX_BOOST = 1.3


def section_targets(total: int, math: int | None, rw: int | None) -> dict[str, int]:
    """Section targets from the goals; a section without its own minimum gets what the total leaves it."""
    if math is None:
        math = total - rw if rw is not None else -(-total // 20) * 10  # half, rounded up to a multiple of 10
    if rw is None:
        rw = total - math
    return {"MATH": max(200, min(800, math)), "RW": max(200, min(800, rw))}


def section_boost(targets: dict[str, int] | None) -> dict[str, float]:
    """Weakness multiplier per section: the section with the higher target counts up to 1.3x.

    A 50-point lead earns the full boost (700 Math within a 1350 total, the original setup).
    """
    gap = targets["MATH"] - targets["RW"] if targets else 0
    return {
        "MATH": 1 + min(MAX_BOOST - 1, 0.006 * max(0, gap)),
        "RW": 1 + min(MAX_BOOST - 1, 0.006 * max(0, -gap)),
    }


def priority(targets: dict[str, int] | None) -> str:
    """The section the goals lean on (Math on a tie)."""
    b = section_boost(targets)
    return "RW" if b["RW"] > b["MATH"] else "MATH"
